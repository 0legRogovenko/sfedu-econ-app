import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
README = BACKEND / "README.md"


def _requirement_names(path: Path) -> set[str]:
    names: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "-r")):
            continue
        names.add(re.split(r"[<>=!~\[]", line, maxsplit=1)[0].lower())
    return names


def _workflow_job(text: str, name: str) -> str:
    jobs = re.search(r"(?m)^jobs:\s*$", text)
    assert jobs is not None
    jobs_text = text[jobs.end() :]
    job = re.search(rf"(?m)^  {re.escape(name)}:\s*$", jobs_text)
    assert job is not None
    following = jobs_text[job.end() :]
    next_job = re.search(r"(?m)^  [A-Za-z0-9_-]+:\s*$", following)
    end = job.end() + next_job.start() if next_job else len(jobs_text)
    return jobs_text[job.start() : end]


def _yaml_value_lines(block: str, key: str) -> list[str]:
    match = re.search(
        rf"(?m)^(?P<indent> +){re.escape(key)}:\s*(?P<value>[^\n]*)$", block
    )
    assert match is not None
    value = match.group("value").strip()
    if value not in {"", "|", ">"}:
        return [value.strip("'\"")]

    key_indent = len(match.group("indent"))
    values: list[str] = []
    for raw_line in block[match.end() :].splitlines():
        if not raw_line.strip():
            continue
        indentation = len(raw_line) - len(raw_line.lstrip())
        if indentation <= key_indent:
            break
        values.append(raw_line.strip().strip("'\""))
    return values


def test_runtime_requirements_exclude_development_tools() -> None:
    runtime = _requirement_names(BACKEND / "requirements.txt")
    assert runtime.isdisjoint({"pytest", "ruff"})
    assert "httpx" in runtime


def test_development_requirements_extend_runtime() -> None:
    lines = (BACKEND / "requirements-dev.txt").read_text(encoding="utf-8").splitlines()
    development = _requirement_names(BACKEND / "requirements-dev.txt")
    assert "-r requirements.txt" in lines
    assert {"pytest", "ruff"} <= development
    assert "ruff==0.16.5" in lines
    assert "httpx" not in development


def test_backend_ci_installs_development_requirements() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    backend_job = _workflow_job(workflow, "backend")
    assert "pip install -r requirements-dev.txt" in backend_job


def test_backend_ci_cache_tracks_development_requirements() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    backend_job = _workflow_job(workflow, "backend")
    cache_paths = set(_yaml_value_lines(backend_job, "cache-dependency-path"))
    assert {"backend/requirements.txt", "backend/requirements-dev.txt"} <= cache_paths


def test_local_development_installs_test_requirements() -> None:
    readme = README.read_text(encoding="utf-8")
    development_start = readme.index("## Разработка локально")
    tests_start = readme.index("## Тесты", development_start)
    development = readme[development_start:tests_start]
    install_command = "pip install -r requirements-dev.txt"
    assert install_command in development
    assert readme.index(install_command, development_start) < readme.index(
        "pytest", tests_start
    )
