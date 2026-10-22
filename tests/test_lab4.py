from core.domain import Account, Budget, Category, Transaction
from core.ftypes import Left, Nothing, Right, Some
from core.validation import check_budget, safe_category, spent_in, validate_transaction

CATS = (
    Category("transport", "Transport", None, "expense"),
    Category("car", "Car", "transport", "expense"),
    Category("fuel", "Fuel", "car", "expense"),
    Category("salary", "Salary", None, "income"),
)

ACCS = (Account("acc_001", "Kaspi", 150000, "KZT"),)


def test_safe_category_found():
    assert safe_category(CATS, "fuel") == Some(CATS[2])


def test_safe_category_missing():
    assert safe_category(CATS, "pizza") == Nothing()


def test_maybe_map_and_get_or_else():
    name = safe_category(CATS, "fuel").map(lambda c: c.name).get_or_else("?")
    assert name == "Fuel"


def test_nothing_skips_map():
    name = safe_category(CATS, "pizza").map(lambda c: c.name).get_or_else("?")
    assert name == "?"


def test_bind_finds_parent_category():
    parent = safe_category(CATS, "fuel").bind(
        lambda c: safe_category(CATS, c.parent_id)
    )
    assert parent == Some(CATS[1])


def test_bind_root_has_no_parent():
    parent = safe_category(CATS, "transport").bind(
        lambda c: safe_category(CATS, c.parent_id)
    )
    assert parent == Nothing()


def test_right_map_and_left_map():
    assert Right(5).map(lambda x: x * 2) == Right(10)
    assert Left({"error": "x"}).map(lambda x: x * 2) == Left({"error": "x"})


def test_validate_ok_expense():
    t = Transaction("t1", "acc_001", "fuel", -5000, "2026-10-01", "")
    assert validate_transaction(t, ACCS, CATS) == Right(t)


def test_validate_ok_income():
    t = Transaction("t2", "acc_001", "salary", 200000, "2026-10-01", "")
    assert validate_transaction(t, ACCS, CATS) == Right(t)


def test_validate_unknown_account():
    t = Transaction("t3", "acc_999", "fuel", -5000, "2026-10-01", "")
    result = validate_transaction(t, ACCS, CATS)
    assert isinstance(result, Left)
    assert result.error["field"] == "account_id"


def test_validate_unknown_category():
    t = Transaction("t4", "acc_001", "pizza", -5000, "2026-10-01", "")
    result = validate_transaction(t, ACCS, CATS)
    assert result.error["field"] == "cat_id"


def test_validate_wrong_sign():
    t = Transaction("t5", "acc_001", "fuel", 500, "2026-10-01", "")
    result = validate_transaction(t, ACCS, CATS)
    assert result.error["field"] == "amount"


BUDGET = Budget("b1", "car", 10000, "month")


def test_spent_in_ignores_incomes_and_other_categories():
    trans = (
        Transaction("t1", "acc_001", "car", -3000, "2026-10-01", ""),
        Transaction("t2", "acc_001", "car", 500, "2026-10-02", "refund"),
        Transaction("t3", "acc_001", "fuel", -7000, "2026-10-03", ""),
    )
    assert spent_in("car", trans) == 3000


def test_check_budget_within_limit():
    trans = (Transaction("t1", "acc_001", "car", -4000, "2026-10-01", ""),)
    assert check_budget(BUDGET, trans) == Right(BUDGET)


def test_check_budget_exactly_limit_is_ok():
    trans = (Transaction("t1", "acc_001", "car", -10000, "2026-10-01", ""),)
    assert check_budget(BUDGET, trans) == Right(BUDGET)


def test_check_budget_exceeded():
    trans = (
        Transaction("t1", "acc_001", "car", -8000, "2026-10-01", ""),
        Transaction("t2", "acc_001", "car", -5000, "2026-10-02", ""),
    )
    result = check_budget(BUDGET, trans)
    assert isinstance(result, Left)
    assert result.error["spent"] == 13000
