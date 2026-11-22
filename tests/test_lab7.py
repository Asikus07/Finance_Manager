from core.compose import compose, pipe, pipe_steps
from core.domain import Budget, Category, Transaction
from core.ftypes import Left, Right
from core.report import (
    average_spent,
    count_expenses,
    only_expenses,
    spent_by_category,
    total_spent,
    tree_budget_check,
)
from core.service import BudgetService, ReportService
from core.validation import check_budget

CATS = (
    Category("transport", "Transport", None, "expense"),
    Category("taxi", "Taxi", "transport", "expense"),
    Category("car", "Car", "transport", "expense"),
    Category("fuel", "Fuel", "car", "expense"),
    Category("food", "Food", None, "expense"),
)

TRANS = (
    Transaction("t1", "acc_001", "taxi", -1000, "2026-10-01", "taxi"),
    Transaction("t2", "acc_001", "fuel", -5000, "2026-10-10", "fuel"),
    Transaction("t3", "acc_001", "food", -2000, "2026-10-20", "lunch"),
    Transaction("t4", "acc_001", "transport", 300, "2026-10-25", "refund"),
    Transaction("t5", "acc_001", "taxi", -700, "2026-09-15", "taxi"),
)

BUDGET = Budget("b1", "transport", 5000, "month")


# ---------- compose.py ----------


def test_pipe_runs_left_to_right():
    assert pipe(2, lambda x: x + 1, lambda x: x * 10) == 30


def test_pipe_without_funcs_returns_value():
    assert pipe(TRANS) is TRANS


def test_compose_runs_right_to_left():
    assert compose(lambda x: x + 1, lambda x: x * 10)(2) == 21


def test_compose_gives_same_result_as_pipe():
    composed = compose(total_spent, only_expenses)
    assert composed(TRANS) == pipe(TRANS, only_expenses, total_spent) == 8700


def test_pipe_steps_keeps_every_step():
    steps = pipe_steps(TRANS, only_expenses, total_spent)
    assert tuple(name for name, _ in steps) == ("start", "only_expenses", "total_spent")
    assert steps[0][1] is TRANS
    assert steps[-1][1] == 8700


# ---------- report.py ----------


def test_spent_by_category_sums_each_category():
    assert spent_by_category(TRANS) == {"taxi": 1700, "fuel": 5000, "food": 2000}


def test_average_spent_empty_is_zero():
    assert average_spent(()) == 0


def test_tree_budget_check_counts_subcategories():
    assert check_budget(BUDGET, TRANS) == Right(BUDGET)
    result = tree_budget_check(CATS)(BUDGET, TRANS)
    assert isinstance(result, Left)
    assert result.error["spent"] == 6700


# ---------- service.py ----------


def test_monthly_report():
    service = BudgetService(
        validators=(tree_budget_check(CATS),),
        calculators=(total_spent, spent_by_category),
        trans=TRANS,
        budgets=(BUDGET,),
    )
    report = service.monthly_report("2026-10")
    assert report["total_spent"] == 8000
    assert report["spent_by_category"] == {"taxi": 1000, "fuel": 5000, "food": 2000}
    assert len(report["over_budget"]) == 1
    assert report["over_budget"][0]["spent"] == 6000


def test_budget_service_uses_injected_functions():
    def fake_total(trans):
        return 999

    service = BudgetService((), (fake_total,), TRANS, (BUDGET,))
    report = service.monthly_report("2026-10")
    assert report["fake_total"] == 999
    assert report["over_budget"] == ()


def test_category_report():
    service = ReportService(
        aggregators=(total_spent, spent_by_category, count_expenses, average_spent),
        cats=CATS,
        trans=TRANS,
    )
    report = service.category_report("transport")
    assert report["total_spent"] == 6700
    assert report["spent_by_category"] == {"taxi": 1700, "fuel": 5000}
    assert report["count_expenses"] == 3
    assert report["average_spent"] == 2233


def test_services_do_not_change_input():
    BudgetService((tree_budget_check(CATS),), (), TRANS, (BUDGET,)).monthly_report(
        "2026-10"
    )
    assert tuple(t.cat_id for t in TRANS) == (
        "taxi",
        "fuel",
        "food",
        "transport",
        "taxi",
    )
