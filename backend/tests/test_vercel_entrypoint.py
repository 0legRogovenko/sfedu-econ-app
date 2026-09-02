import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_vercel_entrypoint_exports_the_existing_fastapi_app():
    import app as vercel_entrypoint
    from src.main import app

    assert vercel_entrypoint.app is app


def test_vercel_config_keeps_compute_near_the_european_database():
    config = json.loads((BACKEND_ROOT / "vercel.json").read_text())

    assert config["regions"] == ["fra1"]
    assert config["functions"]["app.py"]["maxDuration"] == 60


def test_vercel_bundle_excludes_the_real_schedule_test_corpus():
    config = json.loads((BACKEND_ROOT / "vercel.json").read_text())

    excluded = config["functions"]["app.py"]["excludeFiles"]
    assert "tests/**" in excluded


def test_vercel_bundle_excludes_the_workflow_only_schedule_snapshot():
    config = json.loads((BACKEND_ROOT / "vercel.json").read_text())

    excluded = config["functions"]["app.py"]["excludeFiles"]
    assert "data/schedule_snapshot/**" in excluded


def test_vercel_uses_the_same_python_version_as_the_backend_container():
    assert (BACKEND_ROOT / ".python-version").read_text().strip() == "3.12"


def test_disabled_scheduler_does_not_load_parser_stack_on_cold_start():
    environment = os.environ.copy()
    environment["ENABLE_SCHEDULER"] = "0"

    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import src.main; "
            "raise SystemExit(1 if 'src.scheduler' in sys.modules else 0)",
        ],
        cwd=BACKEND_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert probe.returncode == 0, probe.stderr
