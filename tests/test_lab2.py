from core.domain import Category, Transaction
from core.recursion import flatten_categories, sum_expenses_recursive
from core.transforms import by_amount_range, by_category, by_date_range

CATS = (
    Category("transport", "Transport", None, "expense"),
    Category("taxi", "Taxi", "transport", "expense"),
    Category("car", "Car", "transport", "expense"),
    Category("fuel", "Fuel", "car", "expense"),
    Category("food", "Food", None, "expense"),
)

TRANS = (
    Transaction("t1", "acc_001", "taxi", -1000, "2026-09-01", "taxi"),
    Transaction("t2", "acc_001", "fuel", -5000, "2026-09-10", "fuel"),
    Transaction("t3", "acc_001", "food", -2000, "2026-09-20", "lunch"),
    Transaction("t4", "acc_001", "transport", 300, "2026-09-25", "refund"),
)


def ids(items):
    return tuple(x.id for x in items)


def test_by_category():
    assert ids(filter(by_category("taxi"), TRANS)) == ("t1",)


def test_by_date_range_includes_borders():
    result = filter(by_date_range("2026-09-10", "2026-09-20"), TRANS)
    assert ids(result) == ("t2", "t3")


def test_by_amount_range_negative_expenses():
    result = filter(by_amount_range(-3000, -1000), TRANS)
    assert ids(result) == ("t1", "t3")


def test_flatten_categories_full_tree():
    result = flatten_categories(CATS, "transport")
    assert ids(result) == ("transport", "taxi", "car", "fuel")


def test_flatten_categories_leaf():
    assert ids(flatten_categories(CATS, "fuel")) == ("fuel",)


def test_flatten_categories_unknown_root():
    assert flatten_categories(CATS, "nothing") == ()


def test_sum_expenses_recursive_tree():
    assert sum_expenses_recursive(CATS, TRANS, "transport") == 6000


def test_sum_expenses_recursive_leaf():
    assert sum_expenses_recursive(CATS, TRANS, "food") == 2000
