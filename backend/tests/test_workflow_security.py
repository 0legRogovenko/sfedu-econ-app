import re
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
WORKFLOWS = sorted(set(WORKFLOWS_DIR.glob("*.yml")) | set(WORKFLOWS_DIR.glob("*.yaml")))
CI_WORKFLOW = WORKFLOWS_DIR / "ci.yml"

TRUSTED_ACTIONS = {
    "actions/checkout": {
        "11d5960a326750d5838078e36cf38b85af677262": "v4.4.0",
    },
    "actions/setup-python": {
        "a26af69be951a213d495a4c3e4e4022e16d87065": "v5.6.0",
    },
    "actions/setup-java": {
        "cf277c60eb25467037889841efdb72551f06f6c3": "v4.9.1",
    },
    "actions/upload-artifact": {
        "ea165f8d65b6e75b540449e92b4886f43607fa02": "v4.6.2",
    },
    "subosito/flutter-action": {
        "1a449444c387b1966244ae4d4f8c696479add0b2": "v2.23.0",
    },
}

ACTION_STEP = re.compile(r"^\s*(?:-\s+)?uses:")
SHA_PIN = re.compile(
    r"^\s*(?:-\s+)?uses:\s+(?P<action>[^\s@]+)@"
    r"(?P<sha>[0-9a-f]{40})\s+# "
    r"(?P<version>v[0-9]+(?:\.[0-9]+)*)\s*$"
)
RUN_STEP = re.compile(r"(?m)^\s*-\s+run:\s*(?P<command>[^\n]+?)\s*$")
PERMISSIONS_KEY = re.compile(r"^(?P<indent>[ \t]*)permissions\s*:(?P<value>.*)$")
WORKING_DIRECTORY = re.compile(
    r"(?m)^\s+working-directory:\s*(?P<directory>[^\s#]+)\s*$"
)


def _action_pin_issue(line: str) -> str | None:
    match = SHA_PIN.fullmatch(line)
    if match is None:
        return "malformed or mutable action ref"

    action = match.group("action")
    approved_shas = TRUSTED_ACTIONS.get(action)
    if approved_shas is None:
        return f"unknown action {action}"

    sha = match.group("sha")
    expected_version = approved_shas.get(sha)
    if expected_version is None:
        return f"unapproved SHA for {action}"

    version = match.group("version")
    if version != expected_version:
        return (
            f"wrong version comment for {action}: "
            f"expected {expected_version}, got {version}"
        )
    return None


def _workflow_job(text: str, name: str) -> str:
    jobs = re.search(r"(?m)^jobs:\s*$", text)
    assert jobs is not None, "workflow is missing a top-level jobs mapping"

    jobs_text = text[jobs.end() :]
    job = re.search(rf"(?m)^  {re.escape(name)}:\s*$", jobs_text)
    assert job is not None, f"workflow is missing the {name!r} job"

    following = jobs_text[job.end() :]
    next_job = re.search(r"(?m)^  [A-Za-z0-9_-]+:\s*$", following)
    end = job.end() + next_job.start() if next_job else len(jobs_text)
    return jobs_text[job.start() : end]


def _permission_issues(lines: list[str]) -> list[str]:
    keys: list[tuple[int, str, str]] = []
    for line_number, line in enumerate(lines, start=1):
        match = PERMISSIONS_KEY.fullmatch(line)
        if match is not None:
            keys.append(
                (line_number, match.group("indent"), match.group("value").strip())
            )

    issues = [
        f"line {line_number}: nested permissions key is forbidden"
        for line_number, indent, _value in keys
        if indent
    ]
    top_level = [key for key in keys if not key[1]]
    if len(top_level) != 1:
        issues.append("workflow must define exactly one top-level permissions block")
        return issues

    start_line, _indent, inline_value = top_level[0]
    block: list[str] = []
    if inline_value:
        block.append(inline_value)
    else:
        for line in lines[start_line:]:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not line[0].isspace():
                break
            block.append(stripped)

    if block != ["contents: read"]:
        issues.append("top-level permissions must contain only contents: read")
    return issues


def _load_guard(
    tmp_path: Path,
    workflows: dict[str, str],
) -> dict[str, object]:
    test_path = tmp_path / "backend" / "tests" / Path(__file__).name
    test_path.parent.mkdir(parents=True)
    test_path.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")

    workflows_path = tmp_path / ".github" / "workflows"
    workflows_path.mkdir(parents=True)
    for name, text in workflows.items():
        (workflows_path / name).write_text(text, encoding="utf-8")

    return runpy.run_path(str(test_path))


def _action_workflow(uses: str) -> str:
    if uses.startswith("- uses:"):
        return f"jobs:\n  release:\n    steps:\n      {uses}\n"
    return f"jobs:\n  release:\n    {uses}\n"


VALID_BACKEND_WORKFLOW = """\
jobs:
  backend:
    defaults:
      run:
        working-directory: backend
    steps:
      - run: pip install -r requirements-dev.txt
      - run: ruff check .
      - run: ruff format --check .
      - run: pytest -q
"""


def test_workflow_actions_are_pinned_to_versioned_commit_shas() -> None:
    assert WORKFLOWS, "repository has no workflow files"
    invalid_refs: list[str] = []

    for workflow in WORKFLOWS:
        for line_number, line in enumerate(
            workflow.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not ACTION_STEP.match(line):
                continue
            issue = _action_pin_issue(line)
            if issue is not None:
                path = workflow.relative_to(ROOT)
                invalid_refs.append(f"{path}:{line_number}: {issue}: {line.strip()}")

    assert not invalid_refs, "invalid action refs:\n" + "\n".join(invalid_refs)


def test_workflows_use_read_only_permissions_and_safe_triggers() -> None:
    issues: list[str] = []

    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        path = workflow.relative_to(ROOT)

        for issue in _permission_issues(text.splitlines()):
            issues.append(f"{path}: {issue}")
        if "pull_request_target" in text:
            issues.append(f"{path}: pull_request_target is forbidden")

    assert not issues, "workflow security issues:\n" + "\n".join(issues)


def test_backend_ci_runs_ruff_after_install_and_before_pytest() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    backend_job = _workflow_job(workflow, "backend")
    working_directories = WORKING_DIRECTORY.findall(backend_job)
    assert working_directories == ["backend"], (
        "backend job must declare exactly one working-directory: backend"
    )

    # Conservatively forbid escape hatches anywhere in this job so required
    # install, Ruff, and pytest steps cannot be conditionally bypassed.
    assert re.search(r"(?m)^\s+continue-on-error\s*:", backend_job) is None, (
        "backend job must not use continue-on-error"
    )
    assert re.search(r"(?m)^\s+if\s*:", backend_job) is None, (
        "backend job must not use conditional if"
    )

    commands = [match.group("command") for match in RUN_STEP.finditer(backend_job)]

    required_commands = (
        "pip install -r requirements-dev.txt",
        "ruff check .",
        "ruff format --check .",
        "pytest -q",
    )
    missing = [command for command in required_commands if command not in commands]
    assert not missing, f"backend job is missing run steps: {missing}"

    positions = [commands.index(command) for command in required_commands]
    assert positions == sorted(positions), (
        "backend job must install requirements-dev, run both Ruff gates, "
        "and then run pytest"
    )


def test_workflow_collection_includes_yaml_and_is_sorted_without_duplicates(
    tmp_path: Path,
) -> None:
    guard = _load_guard(
        tmp_path,
        {
            "z.yml": "name: z\n",
            "a.yaml": "name: a\n",
        },
    )

    names = [path.name for path in guard["WORKFLOWS"]]
    assert names == ["a.yaml", "z.yml"]
    assert len(names) == len(set(names))


def test_yaml_workflow_with_mutable_action_is_rejected(tmp_path: Path) -> None:
    guard = _load_guard(
        tmp_path,
        {"release.yaml": _action_workflow("- uses: actions/checkout@v4")},
    )

    with pytest.raises(AssertionError, match=r"release\.yaml"):
        guard["test_workflow_actions_are_pinned_to_versioned_commit_shas"]()


def test_nested_permissions_override_is_rejected(tmp_path: Path) -> None:
    guard = _load_guard(
        tmp_path,
        {
            "release.yml": """\
permissions:
  contents: read
jobs:
  release:
    permissions:
      contents: write
"""
        },
    )

    with pytest.raises(AssertionError, match="nested permissions"):
        guard["test_workflows_use_read_only_permissions_and_safe_triggers"]()


@pytest.mark.parametrize("uses_prefix", ("- uses:", "uses:"))
def test_unknown_action_is_rejected_in_step_and_job_forms(
    tmp_path: Path,
    uses_prefix: str,
) -> None:
    guard = _load_guard(
        tmp_path,
        {
            "release.yml": _action_workflow(
                f"{uses_prefix} attacker/fork@{'a' * 40} # v1.2.3"
            )
        },
    )

    with pytest.raises(AssertionError, match="unknown action"):
        guard["test_workflow_actions_are_pinned_to_versioned_commit_shas"]()


@pytest.mark.parametrize(
    ("uses", "expected_error"),
    (
        (
            f"- uses: actions/checkout@{'0' * 40} # v4.4.0",
            "unapproved SHA",
        ),
        (
            "- uses: actions/checkout@"
            "11d5960a326750d5838078e36cf38b85af677262 # v4.4.1",
            "version comment",
        ),
    ),
    ids=("wrong-sha", "wrong-version"),
)
def test_trusted_action_with_wrong_pin_is_rejected(
    tmp_path: Path,
    uses: str,
    expected_error: str,
) -> None:
    guard = _load_guard(
        tmp_path,
        {"release.yml": _action_workflow(uses)},
    )

    with pytest.raises(AssertionError, match=expected_error):
        guard["test_workflow_actions_are_pinned_to_versioned_commit_shas"]()


@pytest.mark.parametrize(
    ("target", "replacement", "expected_error"),
    (
        (
            "      - run: ruff check .",
            "      - run: ruff check .\n        continue-on-error: true",
            "continue-on-error",
        ),
        (
            "      - run: ruff format --check .",
            "      - run: ruff format --check .\n        if: false",
            "conditional if",
        ),
        (
            "        working-directory: backend",
            "        working-directory: elsewhere",
            "working-directory",
        ),
    ),
    ids=("continue-on-error", "conditional-skip", "working-directory"),
)
def test_backend_ruff_gate_rejects_weakening(
    tmp_path: Path,
    target: str,
    replacement: str,
    expected_error: str,
) -> None:
    assert target in VALID_BACKEND_WORKFLOW
    mutated_workflow = VALID_BACKEND_WORKFLOW.replace(target, replacement)
    guard = _load_guard(tmp_path, {"ci.yml": mutated_workflow})

    with pytest.raises(AssertionError, match=expected_error):
        guard["test_backend_ci_runs_ruff_after_install_and_before_pytest"]()
