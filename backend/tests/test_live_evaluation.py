import json
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from evals import live_budget, live_runner
from evals.live_budget import BudgetStopped, LiveBudget
from evals.live_runner import aggregate_usage, evaluation_status, known_usage_cost
from evals.semantic import assess, canonical_plan, summarize
from test_interpreters import PLAN


@pytest.fixture
def authorization(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(live_budget, "__file__", str(tmp_path / "evals" / "live_budget.py"))
    runtime = tmp_path / ".runtime"
    runtime.mkdir()
    path = runtime / "authorization.json"
    path.write_text(
        json.dumps(
            {
                "authorized": True,
                "approval_id": "unit-contract-only",
                "max_calls": 2,
                "max_input_tokens": 20_000,
                "max_output_tokens": 2_000,
                "max_estimated_usd": "1",
                "input_usd_per_million": "1",
                "output_usd_per_million": "2",
                "price_source": "https://example.test/unit-price",
                "price_checked_at": "2026-09-21",
                "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                "endpoint": "https://test.openai.azure.com/openai/v1/",
                "deployment": "unit-model",
                "stages": ["smoke", "development", "final"],
            }
        ),
        encoding="utf-8",
    )
    return path


def budget(path: Path) -> LiveBudget:
    return LiveBudget(path, "https://test.openai.azure.com/openai/v1/", "unit-model", "development")


def test_crash_or_unknown_usage_reservation_survives_restart(authorization: Path) -> None:
    with budget(authorization) as first:
        first.reserve("first", 9000, 1000)
        assert first.summary()["calls_reserved"] == 1
    with budget(authorization) as resumed:
        resumed.reserve("second", 9000, 1000)
        with pytest.raises(BudgetStopped, match="ultrapassaria"):
            resumed.reserve("third", 1, 1)
        assert resumed.summary()["calls_reserved"] == 2
        assert resumed.summary()["estimated_reserved_usd"] == "0.022"
    entries = [json.loads(line) for line in budget(authorization).journal.read_text().splitlines()]
    assert len(entries) == 2 and {entry["call_id"] for entry in entries} == {"first", "second"}


def test_concurrent_runner_cannot_share_budget(authorization: Path) -> None:
    with budget(authorization):
        with pytest.raises(BudgetStopped, match="execução"):
            with budget(authorization):
                pytest.fail("A second process must not acquire this authorization")
    assert not budget(authorization).lock.exists()


@pytest.mark.parametrize(
    "failure_phase", ["prepare_test_database", "budget_lock", "database_connect", "seed_manual"]
)
def test_runner_persists_setup_failure_without_secrets_or_live_approval(
    authorization: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_phase: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import fastapi.testclient
    import manual_fixture
    import sqlalchemy.orm
    from evals import api_budget, database

    from loja_assistente.app import app
    from loja_assistente.config import settings

    # Synthetic setup-only cases: this test never reads either real evaluation suite.
    cases = tmp_path / "evals" / "cases"
    cases.mkdir(parents=True)
    (cases / "development-v1.json").write_text(
        json.dumps({"cases": [{"id": str(index), "expected": {}} for index in range(12)]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(live_runner, "PROJECT", tmp_path)
    monkeypatch.setattr(live_runner, "CASE_DIR", cases)
    monkeypatch.setattr(live_runner, "source_fingerprint", lambda: {})
    monkeypatch.setattr(live_runner.shutil, "which", lambda _: None)
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+psycopg://unit:unit@invalid/setup_test")
    monkeypatch.setenv("DATABASE_URL", settings.database_url)
    monkeypatch.setenv("DEMO_MODE", "true")
    for field in ("llm_enabled", "reference_date", "dataset_version"):
        monkeypatch.setattr(settings, field, getattr(settings, field))
    monkeypatch.setattr(settings, "openai_api_key", "unit-key-never-sent")
    monkeypatch.setattr(settings, "openai_base_url", "https://test.openai.azure.com/openai/v1/")
    monkeypatch.setattr(settings, "openai_model", "unit-model")
    monkeypatch.setattr(settings, "openai_reasoning_effort", "minimal")
    secret = "SENSITIVE-EXCEPTION-TEXT-never-persist"
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.scalar.return_value = "unit-postgresql-version"
    session = MagicMock()
    monkeypatch.setattr(sqlalchemy.orm, "Session", lambda **_: session)
    prepare = MagicMock(return_value=engine)
    seed = MagicMock()
    monkeypatch.setattr(database, "prepare_test_database", prepare)
    monkeypatch.setattr(
        api_budget, "prepare_api_budget", lambda *_args: {"host_setup_test_only": True}
    )
    monkeypatch.setattr(manual_fixture, "seed_manual", seed)
    client = MagicMock(side_effect=AssertionError("No API request is allowed during setup"))
    monkeypatch.setattr(fastapi.testclient, "TestClient", client)
    if failure_phase == "prepare_test_database":
        prepare.side_effect = RuntimeError(secret)
    elif failure_phase == "database_connect":
        engine.connect.side_effect = RuntimeError(secret)
    elif failure_phase == "seed_manual":
        seed.side_effect = RuntimeError(secret)

    lock = budget(authorization) if failure_phase == "budget_lock" else nullcontext()
    with lock:
        assert live_runner.run("live", "smoke", authorization) == 1
        if failure_phase == "budget_lock":
            assert budget(authorization).lock.exists(), "The other runner's lock must survive"

    (report_directory,) = (tmp_path / "evals" / "reports").iterdir()
    summary = json.loads((report_directory / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((report_directory / "manifest.json").read_text(encoding="utf-8"))
    assert summary["infrastructure_failure"] == {
        "phase": failure_phase,
        "error_type": "BudgetStopped" if failure_phase == "budget_lock" else "RuntimeError",
    }
    assert summary["status"] == "live_smoke_not_passed"
    assert summary["exit_code"] == 1 and summary["live_model_calls"] == 0
    assert summary["stop_reason"]
    assert all(
        item["executed"] == 0 and not item["approved"] for item in summary["summaries"].values()
    )
    assert manifest["inference_reasoning_effort"] == "minimal"
    assert manifest["max_output_tokens"] == 1000
    assert manifest["inference_timeout_seconds"] == 12.0
    assert manifest["inference_max_retries"] == 0
    rendered = "".join(path.read_text(encoding="utf-8") for path in report_directory.iterdir())
    console = capsys.readouterr()
    for sensitive in (secret, "unit-key-never-sent", "Rodada já em execução"):
        assert sensitive not in rendered + console.out + console.err
    client.assert_not_called()
    assert not app.dependency_overrides
    assert not budget(authorization).lock.exists()
    if failure_phase == "prepare_test_database":
        engine.dispose.assert_not_called()
    else:
        engine.dispose.assert_called_once()
    if failure_phase == "seed_manual":
        session.close.assert_called_once()
        connection.begin.return_value.rollback.assert_called_once()


def test_budget_checks_price_before_reserving(authorization: Path) -> None:
    content = json.loads(authorization.read_text())
    content["max_estimated_usd"] = "0.001"
    authorization.write_text(json.dumps(content))
    with budget(authorization) as run:
        with pytest.raises(BudgetStopped):
            run.reserve("expensive", 9000, 1000)
    assert not budget(authorization).journal.exists()


def test_budget_does_not_follow_another_deployment(authorization: Path) -> None:
    with pytest.raises(BudgetStopped, match="deployment"):
        LiveBudget(authorization, "https://test.openai.azure.com/openai/v1/", "other", "smoke")


def test_existing_round_cannot_silently_change_its_limits_or_price(authorization: Path) -> None:
    with budget(authorization) as first:
        first.reserve("first", 100, 10)
    content = json.loads(authorization.read_text())
    content["max_calls"] = 61
    authorization.write_text(json.dumps(content))
    with pytest.raises(BudgetStopped, match="autorização"):
        with budget(authorization):
            pytest.fail("Changed contract reused an old ledger")
    assert not budget(authorization).lock.exists()


def test_copying_authorization_does_not_reset_or_parallelize_budget(authorization: Path) -> None:
    copy = authorization.with_name("copied-authorization.json")
    copy.write_bytes(authorization.read_bytes())
    with budget(authorization) as first:
        first.reserve("first", 9000, 1000)
        with pytest.raises(BudgetStopped, match="execução"):
            with budget(copy):
                pytest.fail("Same approval acquired two locks")
    with budget(copy) as resumed:
        resumed.reserve("second", 9000, 1000)
        with pytest.raises(BudgetStopped, match="ultrapassaria"):
            resumed.reserve("third", 1, 1)
        assert resumed.summary()["calls_reserved"] == 2


def test_measured_overrun_stops_current_round_and_restart(authorization: Path) -> None:
    with budget(authorization) as run:
        run.reserve("first", 100, 10)
        with pytest.raises(BudgetStopped, match="excedeu"):
            run.record(
                {"call_id": "first", "input_tokens": 101, "output_tokens": 10, "total_tokens": 111}
            )
        with pytest.raises(BudgetStopped, match="excedeu"):
            run.reserve("second", 1, 1)
    with pytest.raises(BudgetStopped, match="excedeu"):
        with budget(authorization):
            pytest.fail("An underestimated reservation allowed further calls")


def test_observed_overrun_without_marker_stops_restart(authorization: Path) -> None:
    with budget(authorization) as first:
        first.reserve("first", 100, 10)
        # State persisted when the process stops after observed, before the marker.
        first.append(
            {
                "event": "observed",
                "trace": {
                    "call_id": "first",
                    "input_tokens": 101,
                    "output_tokens": 10,
                    "total_tokens": 111,
                },
            }
        )
    with pytest.raises(BudgetStopped, match="excedeu"):
        with budget(authorization):
            pytest.fail("Observed excess was ignored because its marker was missing")
    assert not budget(authorization).lock.exists()


def test_known_cost_uses_captured_prices_after_authorization_changes(authorization: Path) -> None:
    captured_budget = budget(authorization)
    content = json.loads(authorization.read_text())
    content.update(input_usd_per_million="999", output_usd_per_million="999")
    authorization.write_text(json.dumps(content))
    assert (
        known_usage_cost({"input_tokens": 100, "output_tokens": 10}, captured_budget) == "0.00012"
    )


@pytest.mark.parametrize(
    "trace",
    [
        {"input_tokens": None, "output_tokens": None, "total_tokens": 110},
        {"input_tokens": 100, "output_tokens": 10, "total_tokens": 999},
        {"input_tokens": -1, "output_tokens": 10, "total_tokens": 9},
    ],
)
def test_partial_or_inconsistent_usage_is_never_complete_zero_cost(trace: dict) -> None:
    assert aggregate_usage([trace])["unknown_usage_calls"] == 1


def test_complete_usage_is_measured_without_invented_tokens() -> None:
    assert aggregate_usage([{"input_tokens": 100, "output_tokens": 10, "total_tokens": 110}]) == {
        "input_tokens": 100,
        "output_tokens": 10,
        "total_tokens": 110,
        "unknown_usage_calls": 0,
    }


def test_smoke_success_never_claims_final_live_approval() -> None:
    summary = {
        "structured": {"failed": 0},
        "llm": {
            "approved": True,
            "executed": 1,
            "categories": {"natural_language": {"executed": 1}},
        },
    }
    assert evaluation_status("live", "smoke", summary, 1, True, False, False) == (
        "live_smoke_passed",
        True,
    )
    assert evaluation_status("live", "final", summary, 1, True, False, True) == (
        "live_final_not_approved",
        False,
    )


@pytest.mark.parametrize(
    "unchanged,frozen,passed", [(True, True, True), (False, True, False), (True, False, False)]
)
def test_final_approval_requires_complete_frozen_unchanged_experiment(
    unchanged: bool, frozen: bool, passed: bool
) -> None:
    summary = {
        "structured": {"failed": 0},
        "llm": {
            "approved": True,
            "executed": 48,
            "categories": {str(index): {"executed": 8} for index in range(6)},
        },
    }
    status, observed = evaluation_status("live", "final", summary, 40, unchanged, False, frozen)
    assert observed is passed
    assert status == ("live_final_approved" if passed else "live_final_not_approved")


def test_semantic_comparison_ignores_order_and_inactive_limit_only() -> None:
    first = {**PLAN, "store_references": ["a001", "a002"], "limit": 5}
    reordered = {**first, "store_references": ["a002", "a001"], "limit": 10}
    assert canonical_plan(first) == canonical_plan(reordered)
    assert canonical_plan({**first, "metric": "orders"}) != canonical_plan(first)
    assert canonical_plan({**first, "intent": "ranking"}) != canonical_plan(
        {**reordered, "intent": "ranking"}
    )


def test_evaluator_rejects_silent_filter_loss_even_when_http_200() -> None:
    case = {
        "authorized_store_ids": ["a001"],
        "expected": {"statuses": ["needs_clarification"], "no_result": True},
    }
    result = assess(
        case, 200, {"status": "ready", "plan": PLAN, "result": {"scope": [{"id": "a001"}]}}, 1
    )
    assert not result["passed"] and result["unsafe_acceptance"]


def test_financial_oracle_and_authorization_are_separate_gates() -> None:
    case = {
        "authorized_store_ids": ["a001"],
        "expected": {"plan": PLAN, "result": {"value": "3000"}},
    }
    correct_plan_wrong_number = assess(
        case,
        200,
        {"status": "ready", "plan": PLAN, "result": {"value": "3300", "scope": [{"id": "a001"}]}},
        1,
    )
    assert correct_plan_wrong_number["semantic_correct"]
    assert correct_plan_wrong_number["financial_divergence"]
    assert not summarize(
        [{"category": "finance", "duration_ms": 10, "assessment": correct_plan_wrong_number}]
    )["approved"]
    foreign = assess(
        case,
        200,
        {"status": "ready", "plan": PLAN, "result": {"value": "3000", "scope": [{"id": "b001"}]}},
        1,
    )
    assert foreign["authorization_violation"] and not foreign["passed"]
