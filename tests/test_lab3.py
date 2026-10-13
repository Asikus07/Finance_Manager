from core.domain import Transaction
from core.memo import forecast_expenses, forecast_raw, last_months, measure_ms, month_of


TRANS = (
    Transaction("t1", "acc_001", "taxi", -1000, "2026-09-05", ""),
    Transaction("t2", "acc_001", "taxi", -3000, "2026-09-20", ""),
    Transaction("t3", "acc_001", "taxi", -2000, "2026-10-03", ""),
    Transaction("t4", "acc_001", "bus", -500, "2026-10-10", ""),
    Transaction("t4", "acc_001", "taxi", 700, "2026-10-11", "refund"),
)


def test_month_of_cuts_day():
    assert month_of(TRANS[0]) == "2026-09"


def test_last_months_return_lastest():
    assert last_months(TRANS, 1) == ("2026-10",)


def test_last_months_more_than_available():
    assert last_months(TRANS, 5) == ("2026-09", "2026-10")


def test_last_months_zero_is_empty():
    assert last_months(TRANS, 0) == ()


def test_forecast_raw_average_two_months():
    assert forecast_raw("taxi", TRANS, 2) == 3000


def test_forecast_raw_ignores_other_category_and_incomes():
    assert forecast_raw("taxi", TRANS, 1) == 2000


def test_forecast_raw_empty_is_zero():
    assert forecast_raw("taxi", (), 3) == 0


