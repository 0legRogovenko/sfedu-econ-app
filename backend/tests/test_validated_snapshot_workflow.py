from pathlib import Path

WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "backend-validated-snapshot.yml"
)


def test_validated_snapshot_workflow_is_manual_main_only_and_secret_scoped():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "if: github.ref == 'refs/heads/main'" in workflow
    assert "environment: backend-beta" in workflow
    assert "concurrency:\n  group: backend-beta-data-sync" in workflow

    job_env = workflow.split("\n    env:\n", 1)[1].split("\n\n    steps:", 1)[0]
    assert "DATABASE_URL" not in job_env

    migration = workflow.index("alembic upgrade head")
    snapshot_import = workflow.index("python -m src.schedule.validated_snapshot")
    assert migration < snapshot_import

    for step_name in (
        "Require the Neon connection secret",
        "Apply database migrations",
        "Import reviewed official schedule snapshot",
    ):
        step = workflow.split(f"- name: {step_name}", 1)[1].split("\n      - ", 1)[0]
        assert "DATABASE_URL: ${{ secrets.DATABASE_URL }}" in step
