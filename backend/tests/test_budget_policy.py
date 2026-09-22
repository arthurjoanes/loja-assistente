import pytest

from loja_assistente.assistant.budget_policy import (
    BudgetRejected,
    admit,
    known_usage,
    observed_excess,
)


def test_reservation_counts_unknown_and_pending_calls_against_all_three_ceilings() -> None:
    values = {
        "blocked": False,
        "calls": 1,
        "input_units": 9000,
        "output_units": 1000,
        "calls_limit": 2,
        "input_limit": 18000,
        "output_limit": 2000,
        "reserve_input": 9000,
        "reserve_output": 1000,
    }
    admit(**values)
    for field in ("calls", "input_units", "output_units"):
        with pytest.raises(BudgetRejected):
            admit(**{**values, field: values[field] + 1})
    with pytest.raises(BudgetRejected):
        admit(**{**values, "blocked": True})


@pytest.mark.parametrize(
    "values",
    [
        (None, None, None),
        (100, None, 110),
        (100, 10, 999),
        (-1, 10, 9),
        (True, 1, 2),
        (2**63, 0, 2**63),
    ],
)
def test_missing_partial_inconsistent_or_out_of_range_usage_is_not_zero(values: tuple) -> None:
    assert known_usage(*values) is None


def test_explicit_complete_zero_usage_is_distinct_from_unknown() -> None:
    actual = known_usage(0, 0, 0)
    assert actual is not None and actual.total_tokens == 0


def test_partial_measured_overrun_still_blocks_future_authorization() -> None:
    assert known_usage(101, None, None) is None
    assert observed_excess(101, None, None, 100, 10)
    assert observed_excess(None, None, 111, 100, 10)
    assert not observed_excess(None, None, None, 100, 10)


@pytest.mark.parametrize("invalid", [0, -1, True, 1.5, 2**63])
def test_invalid_reservation_cannot_authorize_a_call(invalid: int) -> None:
    with pytest.raises(BudgetRejected):
        admit(
            blocked=False,
            calls=0,
            input_units=0,
            output_units=0,
            calls_limit=9,
            input_limit=99999,
            output_limit=99999,
            reserve_input=invalid,
            reserve_output=1000,
        )
