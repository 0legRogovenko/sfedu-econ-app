import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def _requirement_names(path: Path) -> set[str]:
    names: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "-r")):
            continue
        names.add(re.split(r"[<>=!~\[]", line, maxsplit=1)[0].lower())
    return names


def test_runtime_requirements_exclude_development_tools() -> None:
    runtime = _requirement_names(BACKEND / "requirements.txt")
    assert runtime.isdisjoint({"pytest", "httpx", "ruff"})


def test_development_requirements_extend_runtime() -> None:
    text = (BACKEND / "requirements-dev.txt").read_text(encoding="utf-8")
    development = _requirement_names(BACKEND / "requirements-dev.txt")
    assert "-r requirements.txt" in text.splitlines()
    assert {"pytest", "httpx", "ruff"} <= development
