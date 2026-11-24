import asyncio
from time import perf_counter

from core.domain import Account, Budget, Category, Transaction
from core.final import final_report
from core.parallel import average_change, balance_forecast, expenses_by_month
from core.transforms import save_seed

ACCS = (
    Account("a1", "Kaspi", 1000, "KZT"),
    Account("a2", "Halyk", 500, "KZT"),
)

CATS = (
    Category("food", "Food", None, "expense"),
    Category("cafe", "Cafe", "food", "expense"),
    Category("salary", "Salary", None, "income"),
)

TRANS = (
    Transaction("t1", "a1", "cafe", -300, "2026-09-05", "coffee"),
    Transaction("t2", "a1", "salary", 2000, "2026-09-10", "salary"),
    Transaction("t3", "a2", "food", -400, "2026-10-02", "market"),
    Transaction("t4", "a1", "cafe", -100, "2026-10-15", "lunch"),
)

BUDGETS = (Budget("b1", "food", 350, "month"),)


def test_expenses_by_month_counts_each_month():
    result = asyncio.run(expenses_by_month(TRANS, ("2026-09", "2026-10")))
    assert result == {"2026-09": 300, "2026-10": 500}


def test_expenses_by_month_empty_month_is_zero():
    assert asyncio.run(expenses_by_month(TRANS, ("2030-01",))) == {"2030-01": 0}
    assert asyncio.run(expenses_by_month(TRANS, ())) == {}


def test_average_change_uses_last_months():
    assert average_change(TRANS, "a1", n=1) == -100
    assert average_change(TRANS, "a1", n=3) == (1700 - 100) // 2
    assert average_change(TRANS, "nope") == 0


def test_balance_forecast_for_every_account():
    result = asyncio.run(balance_forecast(ACCS, TRANS))
    assert result == {"a1": 1000 + 1600 + 800, "a2": 500 - 400 - 400}


def test_gather_runs_in_parallel():
    start = perf_counter()
    asyncio.run(expenses_by_month(TRANS, ("2026-08", "2026-09", "2026-10"), 0.1))
    assert perf_counter() - start < 0.25


def test_final_report_has_balance_expenses_and_over_budget(tmp_path):
    path = tmp_path / "seed.json"
    save_seed(str(path), (ACCS, CATS, TRANS, BUDGETS))

    report = asyncio.run(final_report(str(path), "2026-09-01", "2026-10-31"))

    assert report["balance"] == 1500 + 1200
    assert report["expenses"] == 800
    assert tuple(b["month"] for b in report["over_budget"]) == ("2026-10",)
    assert report["steps"][0] == ("load", 4)


def test_final_report_empty_period(tmp_path):
    path = tmp_path / "seed.json"
    save_seed(str(path), (ACCS, CATS, TRANS, BUDGETS))

    report = asyncio.run(final_report(str(path), "2030-01-01", "2030-12-31"))

    assert report["expenses"] == 0
    assert report["expenses_by_month"] == {}
    assert report["over_budget"] == ()
    assert report["balance"] == 2700