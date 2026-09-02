import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

ACTION_STEP = re.compile(r"^\s*(?:-\s+)?uses:")
SHA_PIN = re.compile(
    r"^\s*(?:-\s+)?uses:\s+[^\s@]+@[0-9a-f]{40}\s+# v[0-9]+(?:\.[0-9]+)*\s*$"
)
RUN_STEP = re.compile(r"(?m)^\s*-\s+run:\s*(?P<command>[^\n]+?)\s*$")


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


def _top_level_permissions(lines: list[str]) -> list[str] | None:
    starts = [index for index, line in enumerate(lines) if line == "permissions:"]
    if len(starts) != 1:
        return None

    block: list[str] = []
    for line in lines[starts[0] + 1 :]:
        if line and not line[0].isspace():
            break
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            block.append(stripped)
    return block


def test_workflow_actions_are_pinned_to_versioned_commit_shas() -> None:
    mutable_refs: list[str] = []

    for workflow in WORKFLOWS:
        for line_number, line in enumerate(
            workflow.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if ACTION_STEP.match(line) and SHA_PIN.fullmatch(line) is None:
                path = workflow.relative_to(ROOT)
                mutable_refs.append(f"{path}:{line_number}: {line.strip()}")

    assert not mutable_refs, "mutable action refs:\n" + "\n".join(mutable_refs)


def test_workflows_use_read_only_permissions_and_safe_triggers() -> None:
    issues: list[str] = []

    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        path = workflow.relative_to(ROOT)
        permissions = _top_level_permissions(text.splitlines())

        if permissions != ["contents: read"]:
            issues.append(
                f"{path}: top-level permissions must contain only contents: read"
            )
        if "pull_request_target" in text:
            issues.append(f"{path}: pull_request_target is forbidden")

    assert not issues, "workflow security issues:\n" + "\n".join(issues)


def test_backend_ci_runs_ruff_after_install_and_before_pytest() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    backend_job = _workflow_job(workflow, "backend")
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
