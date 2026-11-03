from pathlib import Path

WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "backend-beta-sync.yml"
)


def test_beta_sync_workflow_uses_protected_database_secret():
    workflow = WORKFLOW.read_text()

    assert "environment: backend-beta" in workflow
    assert "DATABASE_URL: ${{ secrets.DATABASE_URL }}" in workflow
    assert 'ADMIN_ENABLED: "0"' in workflow
    assert 'ENABLE_SCHEDULER: "0"' in workflow


def test_database_secret_is_scoped_to_database_steps_only():
    workflow = WORKFLOW.read_text()
    job_env = workflow.split("\n    env:\n", 1)[1].split("\n\n    steps:", 1)[0]

    assert "DATABASE_URL" not in job_env
    for step_name in (
        "Require the Neon connection secret",
        "Apply database migrations",
        "Refresh news, staff, and official schedule",
    ):
        step = workflow.split(f"- name: {step_name}", 1)[1].split("\n      - ", 1)[0]
        assert "DATABASE_URL: ${{ secrets.DATABASE_URL }}" in step


def test_beta_sync_workflow_migrates_before_refreshing_all_sources():
    workflow = WORKFLOW.read_text()

    migration = workflow.index("alembic upgrade head")
    refresh = workflow.index("python -m src.beta_sync")
    assert migration < refresh


def test_beta_sync_workflow_supports_manual_and_daily_runs():
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow


def test_beta_sync_job_only_runs_from_main():
    workflow = WORKFLOW.read_text()

    job = workflow.split("jobs:\n", 1)[1].split("\n    steps:", 1)[0]

    assert "if: github.ref == 'refs/heads/main'" in job
