import re
import runpy
import tomllib
from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest
import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
WORKFLOWS = sorted(set(WORKFLOWS_DIR.glob("*.yml")) | set(WORKFLOWS_DIR.glob("*.yaml")))
CI_WORKFLOW = WORKFLOWS_DIR / "ci.yml"
SECURITY_WORKFLOW = WORKFLOWS_DIR / "security.yml"
GITLEAKS_CONFIG = ROOT / ".gitleaks.toml"

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
    "aquasecurity/trivy-action": {
        "b6643a29fecd7f34b3597bc6acb0a98b03d33ff8": "v0.33.1",
    },
    "gitleaks/gitleaks-action": {
        "ff98106e4c7b2bc287b24eaf42907196329070c7": "v2.3.9",
    },
    "subosito/flutter-action": {
        "1a449444c387b1966244ae4d4f8c696479add0b2": "v2.23.0",
    },
}

SHA_PIN = re.compile(
    r"^\s*(?:-\s+)?(?:uses|\"uses\"|'uses'):\s+"
    r"(?P<quote>[\"']?)(?P<action>[^\s@\"']+)@"
    r"(?P<sha>[0-9a-f]{40})(?P=quote)\s+# "
    r"(?P<version>v[0-9]+(?:\.[0-9]+)*)\s*$"
)


class _MarkedMapping(dict[object, object]):
    def __init__(self) -> None:
        super().__init__()
        self.key_lines: dict[object, int] = {}


class _UniqueKeySafeLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> _MarkedMapping:
    loader.flatten_mapping(node)
    mapping = _MarkedMapping()
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key is True and key_node.value == "on":
            key = "on"
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )

        mapping[key] = loader.construct_object(value_node, deep=deep)
        mapping.key_lines[key] = key_node.start_mark.line
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _load_workflow(workflow: Path) -> tuple[str, _MarkedMapping]:
    text = workflow.read_text(encoding="utf-8")
    path = workflow.relative_to(ROOT)
    try:
        document = yaml.load(text, Loader=_UniqueKeySafeLoader)
    except yaml.YAMLError as exc:
        raise AssertionError(f"{path}: invalid workflow YAML: {exc}") from exc

    assert isinstance(document, _MarkedMapping), (
        f"{path}: workflow root must be a mapping"
    )
    return text, document


def _mapping_entries(
    value: object,
) -> Iterator[tuple[_MarkedMapping, object, object, int]]:
    pending = [value]
    visited: set[int] = set()
    while pending:
        current = pending.pop()
        if isinstance(current, _MarkedMapping):
            identity = id(current)
            if identity in visited:
                continue
            visited.add(identity)
            for key, nested in current.items():
                yield current, key, nested, current.key_lines[key]
                pending.append(nested)
        elif isinstance(current, list):
            identity = id(current)
            if identity in visited:
                continue
            visited.add(identity)
            pending.extend(current)


def _entries_for_key(
    document: _MarkedMapping,
    expected_key: str,
) -> list[tuple[_MarkedMapping, object, int]]:
    return [
        (mapping, value, line)
        for mapping, key, value, line in _mapping_entries(document)
        if key == expected_key
    ]


def _action_pin_issue(line: str, parsed_uses: object) -> str | None:
    match = SHA_PIN.fullmatch(line)
    if match is None:
        return "malformed or mutable action ref"

    action = match.group("action")
    source_uses = f"{action}@{match.group('sha')}"
    if parsed_uses != source_uses:
        return "malformed or mutable action ref"

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


def _permission_issues(document: _MarkedMapping) -> list[str]:
    issues: list[str] = []
    missing = object()
    root_permissions = document.get("permissions", missing)
    if root_permissions is missing:
        issues.append("workflow must define exactly one top-level permissions block")
    elif root_permissions != {"contents": "read"}:
        issues.append("top-level permissions must contain only contents: read")

    for mapping, _value, line in _entries_for_key(document, "permissions"):
        if mapping is not document:
            issues.append(f"line {line + 1}: nested permissions key is forbidden")
    return issues


def _trigger_issues(document: _MarkedMapping) -> list[str]:
    missing = object()
    trigger = document.get("on", missing)
    if trigger is missing:
        return []

    line = document.key_lines["on"] + 1
    if isinstance(trigger, str):
        trigger_names = (trigger,)
        supported_shape = True
    elif isinstance(trigger, list):
        trigger_names = tuple(item for item in trigger if isinstance(item, str))
        supported_shape = len(trigger_names) == len(trigger)
    elif isinstance(trigger, Mapping):
        trigger_names = tuple(key for key in trigger if isinstance(key, str))
        supported_shape = len(trigger_names) == len(trigger)
    else:
        trigger_names = ()
        supported_shape = False

    issues: list[str] = []
    if not supported_shape:
        issues.append(f"line {line}: unsupported on trigger shape")
    if "pull_request_target" in trigger_names:
        issues.append(f"line {line}: pull_request_target is forbidden")
    return issues


def _shell_issues(document: _MarkedMapping) -> list[str]:
    issues: list[str] = []
    for _mapping, value, line in _entries_for_key(document, "shell"):
        if value != "bash":
            issues.append(
                f"line {line + 1}: shell override must use the trusted bash runner shell"
            )
    return issues


def _workflow_job(document: _MarkedMapping, name: str) -> _MarkedMapping:
    jobs = document.get("jobs")
    assert isinstance(jobs, _MarkedMapping), (
        "workflow is missing a top-level jobs mapping"
    )
    job = jobs.get(name)
    assert isinstance(job, _MarkedMapping), f"workflow is missing the {name!r} job"
    return job


def _job_steps(job: _MarkedMapping) -> list[_MarkedMapping]:
    steps = job.get("steps")
    assert isinstance(steps, list), "workflow job must define a steps sequence"
    assert all(isinstance(step, _MarkedMapping) for step in steps), (
        "workflow steps must be mappings"
    )
    return steps


def _named_step(job: _MarkedMapping, name: str) -> _MarkedMapping:
    matches = [step for step in _job_steps(job) if step.get("name") == name]
    assert len(matches) == 1, f"expected exactly one {name!r} step"
    return matches[0]


def _action_uses(job: _MarkedMapping) -> list[str]:
    return [
        uses for step in _job_steps(job) if isinstance((uses := step.get("uses")), str)
    ]


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
    if uses.startswith("-"):
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
        text, document = _load_workflow(workflow)
        lines = text.splitlines()
        for _mapping, parsed_uses, line_index in _entries_for_key(document, "uses"):
            line = lines[line_index]
            issue = _action_pin_issue(line, parsed_uses)
            if issue is not None:
                path = workflow.relative_to(ROOT)
                invalid_refs.append(f"{path}:{line_index + 1}: {issue}: {line.strip()}")

    assert not invalid_refs, "invalid action refs:\n" + "\n".join(invalid_refs)


def test_workflows_use_read_only_permissions_and_safe_triggers() -> None:
    assert WORKFLOWS, "repository has no workflow files"
    issues: list[str] = []

    for workflow in WORKFLOWS:
        _text, document = _load_workflow(workflow)
        path = workflow.relative_to(ROOT)

        for issue in _permission_issues(document):
            issues.append(f"{path}: {issue}")
        for issue in _trigger_issues(document):
            issues.append(f"{path}: {issue}")
        for _mapping, _value, line in _entries_for_key(document, "pull_request_target"):
            issues.append(f"{path}: line {line + 1}: pull_request_target is forbidden")

    assert not issues, "workflow security issues:\n" + "\n".join(issues)


def test_workflows_use_only_trusted_shell_overrides() -> None:
    assert WORKFLOWS, "repository has no workflow files"
    issues: list[str] = []

    for workflow in WORKFLOWS:
        _text, document = _load_workflow(workflow)
        path = workflow.relative_to(ROOT)
        for issue in _shell_issues(document):
            issues.append(f"{path}: {issue}")

    assert not issues, "workflow shell issues:\n" + "\n".join(issues)


def test_backend_ci_runs_ruff_after_install_and_before_pytest() -> None:
    _text, document = _load_workflow(CI_WORKFLOW)
    jobs = document.get("jobs")
    assert isinstance(jobs, Mapping), "workflow is missing a top-level jobs mapping"
    backend_job = jobs.get("backend")
    assert isinstance(backend_job, Mapping), "workflow is missing the 'backend' job"

    workflow_defaults = document.get("defaults")
    workflow_run_defaults = (
        workflow_defaults.get("run") if isinstance(workflow_defaults, Mapping) else None
    )
    assert not (
        isinstance(workflow_run_defaults, Mapping) and "shell" in workflow_run_defaults
    ), "backend job must not inherit a workflow-level custom shell"

    defaults = backend_job.get("defaults")
    run_defaults = defaults.get("run") if isinstance(defaults, Mapping) else None
    assert (
        isinstance(run_defaults, Mapping)
        and run_defaults.get("working-directory") == "backend"
    ), "backend job must set defaults.run.working-directory to backend"

    working_directories = [
        value
        for _mapping, value, _line in _entries_for_key(backend_job, "working-directory")
    ]
    assert working_directories == ["backend"], (
        "backend job must declare exactly one working-directory: backend"
    )

    # Conservatively forbid escape hatches anywhere in this job so required
    # install, Ruff, and pytest steps cannot be conditionally bypassed.
    assert not _entries_for_key(backend_job, "continue-on-error"), (
        "backend job must not use continue-on-error"
    )
    assert not _entries_for_key(backend_job, "if"), (
        "backend job must not use conditional if"
    )
    assert not _entries_for_key(backend_job, "shell"), (
        "backend job must not use a custom shell"
    )

    steps = backend_job.get("steps")
    assert isinstance(steps, list), "backend job must define a steps sequence"
    commands = [
        command.strip()
        for step in steps
        if isinstance(step, Mapping) and isinstance((command := step.get("run")), str)
    ]

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


@pytest.mark.parametrize(
    ("action", "sha", "version"),
    (
        (
            "gitleaks/gitleaks-action",
            "ff98106e4c7b2bc287b24eaf42907196329070c7",
            "v2.3.9",
        ),
        (
            "aquasecurity/trivy-action",
            "b6643a29fecd7f34b3597bc6acb0a98b03d33ff8",
            "v0.33.1",
        ),
    ),
    ids=("gitleaks", "trivy"),
)
def test_security_scanner_action_pins_are_trusted(
    action: str,
    sha: str,
    version: str,
) -> None:
    assert TRUSTED_ACTIONS.get(action) == {sha: version}


def test_security_workflow_has_exact_triggers_permissions_and_concurrency() -> None:
    _text, document = _load_workflow(SECURITY_WORKFLOW)

    assert SECURITY_WORKFLOW in WORKFLOWS, (
        "security workflow must be covered by the generic workflow guards"
    )
    assert document.get("name") == "Security checks"
    assert document.get("permissions") == {"contents": "read"}
    assert document.get("concurrency") == {
        "group": "security-${{ github.ref }}",
        "cancel-in-progress": True,
    }

    triggers = document.get("on")
    assert isinstance(triggers, _MarkedMapping), (
        "security workflow triggers must be a mapping"
    )
    assert set(triggers) == {
        "push",
        "pull_request",
        "schedule",
        "workflow_dispatch",
    }
    assert triggers["push"] == {"branches": ["main"]}
    assert triggers["pull_request"] is None
    assert triggers["schedule"] == [{"cron": "41 2 * * 1"}]
    assert triggers["workflow_dispatch"] is None


def test_security_workflow_has_exact_blocking_and_advisory_jobs() -> None:
    _text, document = _load_workflow(SECURITY_WORKFLOW)
    jobs = document.get("jobs")
    assert isinstance(jobs, _MarkedMapping), (
        "security workflow must define a jobs mapping"
    )
    assert set(jobs) == {"gitleaks", "semgrep", "trivy"}

    for name, expected_advisory in {
        "gitleaks": False,
        "semgrep": True,
        "trivy": True,
    }.items():
        job = _workflow_job(document, name)
        assert job.get("continue-on-error", False) is expected_advisory
        entries = _entries_for_key(job, "continue-on-error")
        if expected_advisory:
            assert len(entries) == 1
            mapping, value, _line = entries[0]
            assert mapping is job
            assert value is True
        else:
            assert entries == []


def test_gitleaks_uses_full_history_checkout_and_github_token() -> None:
    _text, document = _load_workflow(SECURITY_WORKFLOW)
    job = _workflow_job(document, "gitleaks")
    checkout = "actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
    action = "gitleaks/gitleaks-action@ff98106e4c7b2bc287b24eaf42907196329070c7"
    assert _action_uses(job) == [checkout, action]

    steps = _job_steps(job)
    assert steps[0].get("with") == {"fetch-depth": 0}
    assert steps[1].get("env") == {"GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}"}


def test_gitleaks_config_extends_only_default_rules_without_allowlist() -> None:
    config = tomllib.loads(GITLEAKS_CONFIG.read_text(encoding="utf-8"))
    assert config == {"extend": {"useDefault": True}}


def test_semgrep_uses_exact_version_scopes_and_report_settings() -> None:
    _text, document = _load_workflow(SECURITY_WORKFLOW)
    job = _workflow_job(document, "semgrep")
    checkout = "actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
    setup_python = "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
    upload = "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
    assert _action_uses(job) == [checkout, setup_python, upload]

    steps = _job_steps(job)
    assert steps[1].get("with") == {"python-version": "3.12", "cache": "pip"}
    assert _named_step(job, "Install Semgrep").get("run") == (
        "pip install semgrep==1.176.0"
    )

    scan = _named_step(job, "Scan supported source and configuration")
    command = scan.get("run")
    assert isinstance(command, str)
    assert command.split() == [
        "semgrep",
        "scan",
        "--config",
        "p/security-audit",
        "--config",
        "p/owasp-top-ten",
        "--config",
        "p/secrets",
        "--error",
        "--json",
        "--output",
        "semgrep-results.json",
        "backend/src",
        "backend/scripts",
        ".github",
    ]

    report = _named_step(job, "Upload Semgrep report")
    assert report.get("if") == "always()"
    assert report.get("uses") == upload
    assert report.get("with") == {
        "name": "semgrep-results",
        "path": "semgrep-results.json",
        "if-no-files-found": "warn",
        "retention-days": 14,
    }


def test_trivy_uses_exact_filesystem_scan_and_report_settings() -> None:
    _text, document = _load_workflow(SECURITY_WORKFLOW)
    job = _workflow_job(document, "trivy")
    checkout = "actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
    trivy = "aquasecurity/trivy-action@b6643a29fecd7f34b3597bc6acb0a98b03d33ff8"
    upload = "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
    assert _action_uses(job) == [checkout, trivy, upload]

    scan = _named_step(job, "Scan dependencies and configuration")
    assert scan.get("uses") == trivy
    assert scan.get("with") == {
        "scan-type": "fs",
        "scan-ref": ".",
        "scanners": "vuln,secret,misconfig",
        "severity": "CRITICAL,HIGH",
        "ignore-unfixed": True,
        "exit-code": "1",
        "format": "json",
        "output": "trivy-results.json",
    }

    report = _named_step(job, "Upload Trivy report")
    assert report.get("if") == "always()"
    assert report.get("uses") == upload
    assert report.get("with") == {
        "name": "trivy-results",
        "path": "trivy-results.json",
        "if-no-files-found": "warn",
        "retention-days": 14,
    }


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


@pytest.mark.parametrize(
    "uses",
    (
        '- "uses": actions/checkout@v4',
        '"uses": actions/checkout@v4',
    ),
    ids=("quoted-step-uses", "quoted-job-uses"),
)
def test_quoted_uses_key_cannot_hide_mutable_action(
    tmp_path: Path,
    uses: str,
) -> None:
    guard = _load_guard(
        tmp_path,
        {"release.yml": _action_workflow(uses)},
    )

    with pytest.raises(AssertionError, match="malformed or mutable action ref"):
        guard["test_workflow_actions_are_pinned_to_versioned_commit_shas"]()


def test_alias_injected_uses_key_cannot_hide_mutable_action(tmp_path: Path) -> None:
    guard = _load_guard(
        tmp_path,
        {
            "release.yml": """\
action_key: &action_key uses
jobs:
  release:
    steps:
      - *action_key: actions/checkout@v4
"""
        },
    )

    with pytest.raises(AssertionError, match="malformed or mutable action ref"):
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


def test_quoted_nested_permissions_override_is_rejected(tmp_path: Path) -> None:
    guard = _load_guard(
        tmp_path,
        {
            "release.yml": """\
permissions:
  contents: read
jobs:
  release:
    "permissions":
      contents: write
"""
        },
    )

    with pytest.raises(AssertionError, match="nested permissions"):
        guard["test_workflows_use_read_only_permissions_and_safe_triggers"]()


def test_flow_style_nested_permissions_override_is_rejected(tmp_path: Path) -> None:
    guard = _load_guard(
        tmp_path,
        {
            "release.yml": """\
permissions:
  contents: read
jobs: {release: {permissions: {contents: write}}}
"""
        },
    )

    with pytest.raises(AssertionError, match="nested permissions"):
        guard["test_workflows_use_read_only_permissions_and_safe_triggers"]()


def test_custom_workflow_shell_override_is_rejected(tmp_path: Path) -> None:
    guard = _load_guard(
        tmp_path,
        {
            "release.yml": """\
permissions:
  contents: read
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - run: echo safe
        shell: bash -c 'exit 0' -- {0}
"""
        },
    )

    with pytest.raises(AssertionError, match="trusted bash runner shell"):
        guard["test_workflows_use_only_trusted_shell_overrides"]()


def test_merge_injected_job_permissions_are_rejected(tmp_path: Path) -> None:
    guard = _load_guard(
        tmp_path,
        {
            "release.yml": """\
permissions: &read_permissions
  contents: read
jobs:
  release:
    <<:
      permissions: *read_permissions
    runs-on: ubuntu-latest
"""
        },
    )

    with pytest.raises(AssertionError, match="nested permissions"):
        guard["test_workflows_use_read_only_permissions_and_safe_triggers"]()


def test_quoted_root_permissions_are_normalized(tmp_path: Path) -> None:
    guard = _load_guard(
        tmp_path,
        {
            "release.yml": """\
"permissions": {contents: read}
jobs:
  release:
    runs-on: ubuntu-latest
"""
        },
    )

    guard["test_workflows_use_read_only_permissions_and_safe_triggers"]()


def test_duplicate_mapping_keys_are_rejected(tmp_path: Path) -> None:
    guard = _load_guard(
        tmp_path,
        {
            "release.yml": """\
permissions:
  contents: read
jobs:
  release:
    runs-on: ubuntu-latest
  release:
    runs-on: windows-latest
"""
        },
    )

    with pytest.raises(AssertionError, match="duplicate key"):
        guard["test_workflows_use_read_only_permissions_and_safe_triggers"]()


def test_merge_collision_is_rejected_as_duplicate_key(tmp_path: Path) -> None:
    guard = _load_guard(
        tmp_path,
        {
            "release.yml": """\
permissions: &read_permissions
  contents: read
jobs:
  release:
    <<:
      permissions: *read_permissions
    permissions:
      contents: write
"""
        },
    )

    with pytest.raises(AssertionError, match="duplicate key"):
        guard["test_workflows_use_read_only_permissions_and_safe_triggers"]()


def test_recursively_normalized_pull_request_target_key_is_rejected(
    tmp_path: Path,
) -> None:
    guard = _load_guard(
        tmp_path,
        {
            "release.yml": """\
permissions:
  contents: read
on:
  "pull_request_\\u0074arget": {}
jobs: {}
"""
        },
    )

    with pytest.raises(AssertionError, match="pull_request_target"):
        guard["test_workflows_use_read_only_permissions_and_safe_triggers"]()


@pytest.mark.parametrize(
    "trigger",
    (
        "on: pull_request_target",
        "on: [push, pull_request_target]",
        '"on": "pull_request_target"',
        "'on': [push, 'pull_request_target']",
    ),
    ids=(
        "scalar",
        "list",
        "quoted-scalar",
        "quoted-list",
    ),
)
def test_pull_request_target_trigger_values_are_rejected(
    tmp_path: Path,
    trigger: str,
) -> None:
    guard = _load_guard(
        tmp_path,
        {
            "release.yml": f"""\
permissions:
  contents: read
{trigger}
jobs: {{}}
"""
        },
    )

    with pytest.raises(AssertionError, match="pull_request_target"):
        guard["test_workflows_use_read_only_permissions_and_safe_triggers"]()


@pytest.mark.parametrize(
    ("trigger", "expected"),
    (
        ("push", "push"),
        ("[push, pull_request]", ["push", "pull_request"]),
    ),
    ids=("scalar", "list"),
)
def test_safe_trigger_values_are_accepted_and_github_on_key_is_preserved(
    tmp_path: Path,
    trigger: str,
    expected: object,
) -> None:
    guard = _load_guard(
        tmp_path,
        {
            "release.yml": f"""\
permissions:
  contents: read
on: {trigger}
jobs: {{}}
"""
        },
    )

    guard["test_workflows_use_read_only_permissions_and_safe_triggers"]()
    _text, document = guard["_load_workflow"](guard["WORKFLOWS"][0])

    assert "on" in document
    assert True not in document
    assert document["on"] == expected


def test_unsupported_trigger_shape_is_rejected(tmp_path: Path) -> None:
    guard = _load_guard(
        tmp_path,
        {
            "release.yml": """\
permissions:
  contents: read
on: 42
jobs: {}
"""
        },
    )

    with pytest.raises(AssertionError, match="unsupported on trigger shape"):
        guard["test_workflows_use_read_only_permissions_and_safe_triggers"]()


def test_empty_workflow_directory_is_rejected(tmp_path: Path) -> None:
    guard = _load_guard(tmp_path, {})

    assert guard["WORKFLOWS"] == []
    with pytest.raises(AssertionError, match="no workflow files"):
        guard["test_workflow_actions_are_pinned_to_versioned_commit_shas"]()


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
    ("target", "replacement"),
    (
        (
            "jobs:",
            "defaults:\n  run:\n    shell: bash -c 'exit 0' -- {0}\njobs:",
        ),
        (
            "jobs:",
            '"defaults": {"run": {"shell": "bash -c \'exit 0\' -- {0}"}}\njobs:',
        ),
        (
            "        working-directory: backend",
            "        working-directory: backend\n"
            "        shell: bash -c 'exit 0' -- {0}",
        ),
        (
            "      - run: ruff check .",
            "      - run: ruff check .\n        shell: bash -c 'exit 0' -- {0}",
        ),
    ),
    ids=(
        "workflow-defaults-run-shell",
        "quoted-flow-workflow-defaults-run-shell",
        "defaults-run-shell",
        "ruff-step-shell",
    ),
)
def test_backend_ruff_gate_rejects_custom_shell(
    tmp_path: Path,
    target: str,
    replacement: str,
) -> None:
    assert target in VALID_BACKEND_WORKFLOW
    mutated_workflow = VALID_BACKEND_WORKFLOW.replace(target, replacement)
    guard = _load_guard(tmp_path, {"ci.yml": mutated_workflow})

    with pytest.raises(AssertionError, match="custom shell"):
        guard["test_backend_ci_runs_ruff_after_install_and_before_pytest"]()


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
            "      - run: ruff check .",
            '      - run: ruff check .\n        "continue-on-error": true',
            "continue-on-error",
        ),
        (
            "      - run: ruff format --check .",
            '      - run: ruff format --check .\n        "if": false',
            "conditional if",
        ),
        (
            "        working-directory: backend",
            "        working-directory: elsewhere",
            "working-directory",
        ),
        (
            "    defaults:\n"
            "      run:\n"
            "        working-directory: backend\n"
            "    steps:\n"
            "      - run: pip install -r requirements-dev.txt",
            "    defaults:\n"
            "      run:\n"
            "        shell: bash\n"
            "    steps:\n"
            "      - run: pip install -r requirements-dev.txt\n"
            "        working-directory: backend",
            "working-directory",
        ),
    ),
    ids=(
        "continue-on-error",
        "conditional-skip",
        "quoted-continue-on-error",
        "quoted-conditional-skip",
        "working-directory",
        "working-directory-not-default",
    ),
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
