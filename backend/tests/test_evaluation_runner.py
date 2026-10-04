import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from evals.harness import load_suite
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from loja_assistente.models import LoginAdmission, User


def test_standalone_runner_accepts_committed_fixtures_and_repeats_without_login_locks(
    db: Session, test_engine: Engine
) -> None:
    assert db.scalar(select(func.count(User.id))) == 3
    db.rollback()
    project = Path(__file__).resolve().parents[2]
    local_reports = project / "evals/reports/local"
    local_reports.mkdir(parents=True, exist_ok=True)
    environment = {
        **os.environ,
        "DEMO_MODE": "true",
        "LLM_ENABLED": "false",
        "OPENAI_API_KEY": "",
        "TEST_DATABASE_URL": test_engine.url.render_as_string(hide_password=False),
        # Independent login reservations must bind to the validated test engine,
        # even when the process's ordinary application database differs.
        "DATABASE_URL": "postgresql+psycopg://unused:unused@127.0.0.1:1/not_the_test_database",
        "PYTHONPATH": os.pathsep.join((str(project / "backend/src"), str(project))),
    }
    with TemporaryDirectory(prefix="runner-check-", dir=local_reports) as temporary:
        for _ in range(2):
            result = subprocess.run(
                [sys.executable, "-m", "evals.runner", "--output-dir", temporary],
                cwd=project / "backend",
                env=environment,
                capture_output=True,
                text=True,
                timeout=60,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            report = json.loads((Path(temporary) / "latest.json").read_text(encoding="utf-8"))
            assert report["passed"] == report["executed"] == len(load_suite()["cases"])
            assert report["failed"] == report["skipped"] == 0
            assert report["live_llm_evaluated"] is False
            with test_engine.connect() as connection:
                assert connection.scalar(select(func.count(User.id))) == 0
                assert connection.scalar(select(func.count(LoginAdmission.key))) == 0
