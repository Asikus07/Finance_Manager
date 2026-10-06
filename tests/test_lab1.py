from core.domain import Account, Budget, Category, Transaction
from core.transforms import account_balance, add_transaction, load_seed, update_budget


def test_add_transaction_returns_new_tuple():
    t = Transaction("t1", "acc_001", "taxi", -300, "2026-10-01", "")
    old = ()
    new = add_transaction(old, t)
    assert old == ()
    assert new == (t,)


def test_add_transaction_keeps_order():
    t1 = Transaction("t1", "acc_001", "taxi", -300, "2026-10-01", "")
    t2 = Transaction("t2", "acc_001", "bus", -100, "2026-10-02", "")
    result = add_transaction((t1,), t2)
    assert result == (t1, t2)


def test_update_budget_changes_only_target():
    b1 = Budget("b1", "food", 100, "month")
    b2 = Budget("b2", "car", 50, "month")
    result = update_budget((b1, b2), "b1", 999)
    new_b1, new_b2 = result
    assert new_b1.limit == 999
    assert new_b2 == b2
    assert b1.limit == 100


def test_account_balance_sums_only_own_account():
    trans = (
        Transaction("t1", "acc_001", "salary", 1000, "2026-10-01", ""),
        Transaction("t2", "acc_001", "taxi", -300, "2026-10-02", ""),
        Transaction("t3", "acc_002", "taxi", -50, "2026-10-02", ""),
    )
    assert account_balance(trans, "acc_001") == 700
    assert account_balance(trans, "acc_002") == -50


def test_account_balance_is_zero_without_transactions():
    assert account_balance((), "acc_001") == 0


def test_load_seed_returns_tuples_of_models():
    accounts, categories, trans, budgets = load_seed("data/seed.json")
    assert len(accounts) >= 3
    assert len(categories) >= 10
    assert len(budgets) >= 3
    assert isinstance(accounts[0], Account)
    assert isinstance(categories[0], Category)
    assert isinstance(trans[0], Transaction)
    assert isinstance(budgets[0], Budget)
