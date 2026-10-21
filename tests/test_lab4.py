from core.domain import Account, Budget, Category, Transaction
from core.ftypes import Just, Left, Nothing, Right
from core.validation import (
    check_budget,
    check_transaction_budget,
    find_budget,
    safe_category,
    validate_transaction,
)

ACCS = (Account("acc_001", "Kaspi", 1000, "KZT"),)
CATS = (
    Category("food", "Food", None, "expense"),
    Category("cafe", "Cafe", "food", "expense"),
    Category("salary", "Salary", None, "income"),
)
BUDGET = Budget("b1", "food", 5000, "month")


def tx(amount, acc="acc_001", cat="cafe", ts="2026-10-05"):
    return Transaction("t", acc, cat, amount, ts, "")


def test_maybe_map_and_get_or_else():
    assert Just(2).map(lambda x: x * 10).get_or_else(0) == 20
    assert Nothing().map(lambda x: x * 10).get_or_else(0) == 0


def test_maybe_bind_chains_and_short_circuits():
    half = lambda x: Just(x // 2) if x % 2 == 0 else Nothing()
    assert Just(8).bind(half).bind(half) == Just(2)
    assert Just(6).bind(half).bind(half) == Nothing()


def test_either_map_bind_and_get_or_else():
    assert Right(3).map(lambda x: x + 1) == Right(4)
    assert Left("err").map(lambda x: x + 1) == Left("err")
    assert Right(3).bind(lambda x: Left("boom")) == Left("boom")
    assert Left("err").get_or_else(7) == 7


def test_either_map_left_changes_only_error():
    assert Left("e").map_left(str.upper) == Left("E")
    assert Right(1).map_left(str.upper) == Right(1)


def test_safe_category_found_and_missing():
    assert safe_category(CATS, "cafe") == Just(CATS[1])
    assert safe_category(CATS, "ghost") == Nothing()


def test_validate_transaction_ok():
    t = tx(-1000)
    assert validate_transaction(t, ACCS, CATS) == Right(t)


def test_validate_transaction_unknown_account():
    result = validate_transaction(tx(-1000, acc="acc_999"), ACCS, CATS)
    assert result == Left({"field": "account", "error": "account_not_found"})


def test_validate_transaction_unknown_category():
    result = validate_transaction(tx(-1000, cat="ghost"), ACCS, CATS)
    assert result == Left({"field": "category", "error": "category_not_found"})


def test_validate_transaction_sign_must_match_category_type():
    result = validate_transaction(tx(1000, cat="cafe"), ACCS, CATS)
    assert result.error["error"] == "category_type_mismatch"


def test_validate_transaction_first_error_wins():
    result = validate_transaction(tx(0, acc="nope", cat="ghost"), ACCS, CATS)
    assert result.error["error"] == "account_not_found"


def test_check_budget_within_limit_and_exceeded():
    ok = check_budget(BUDGET, (tx(-5000),), CATS)
    assert ok == Right(BUDGET)
    bad = check_budget(BUDGET, (tx(-3000), tx(-2500)), CATS)
    assert bad.error["error"] == "budget_exceeded"
    assert bad.error["spent"] == 5500


def test_check_budget_ignores_other_months():
    old = tx(-9000, ts="2026-09-01")
    now = tx(-1000, ts="2026-10-05")
    assert check_budget(BUDGET, (old, now), CATS) == Right(BUDGET)


def test_find_budget_covers_child_category():
    assert find_budget((BUDGET,), CATS, "cafe") == Just(BUDGET)
    assert find_budget((BUDGET,), CATS, "salary") == Nothing()


def test_new_transaction_is_checked_against_budget():
    check = check_transaction_budget((tx(-4000),), CATS, (BUDGET,))
    assert check(tx(-1000)).get_or_else(None) is not None
    assert check(tx(-2000)).error["error"] == "budget_exceeded"
    assert check(tx(100000, cat="salary")) == Right(tx(100000, cat="salary"))


def test_inputs_are_not_mutated():
    trans = (tx(-4000),)
    check_transaction_budget(trans, CATS, (BUDGET,))(tx(-2000))
    assert trans == (tx(-4000),)
