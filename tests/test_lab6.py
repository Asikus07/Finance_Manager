from core.domain import Account, Budget, Category, Event, Transaction
from core.frp import (
    BALANCE_ALERT,
    BUDGET_ALERT,
    TRANSACTION_ADDED,
    EventBus,
    budget_root,
    check_balance,
    check_budget_limit,
    initial_state,
    make_bus,
    notify,
    update_balance,
)
from core.transforms import load_seed

ACCOUNTS = (Account("acc_001", "Kaspi", 50000, "KZT"),)
CATS = (
    Category("food", "Food", None, "expense"),
    Category("fast_food", "Fast Food", "food", "expense"),
    Category("salary", "Salary", None, "income"),
)
TRANS = (Transaction("t1", "acc_001", "fast_food", -10000, "2026-10-01", ""),)
BUDGETS = (Budget("b1", "food", 30000, "month"),)


def state():
    return initial_state(ACCOUNTS, CATS, TRANS, BUDGETS, low_balance=20000)


def tx_event(cat_id, amount):
    payload = {"account_id": "acc_001", "cat_id": cat_id, "amount": amount}
    return Event(TRANSACTION_ADDED, "2026-10-02T10:00:00", payload)


def bus():
    return make_bus(state(), clock=lambda: "2026-10-02T10:00:00")


def test_initial_state_from_data():
    s = state()
    assert s["balances"] == {"acc_001": 40000}
    assert s["spent"] == {"food": 10000}
    assert s["notifications"] == ()


def test_update_balance_is_pure():
    s = state()
    new = update_balance(tx_event("fast_food", -5000), s)
    assert new["balances"]["acc_001"] == 35000
    assert s["balances"]["acc_001"] == 40000


def test_budget_root_finds_parent():
    s = state()
    assert budget_root("fast_food", s["parents"], s["limits"]) == "food"
    assert budget_root("salary", s["parents"], s["limits"]) is None


def test_check_budget_limit_emits_alert_when_exceeded():
    new = check_budget_limit(tx_event("fast_food", -25000), state())
    assert new["spent"]["food"] == 35000
    assert new["outbox"][0][0] == BUDGET_ALERT


def test_check_budget_limit_no_alert_under_limit():
    new = check_budget_limit(tx_event("fast_food", -5000), state())
    assert new["outbox"] == ()


def test_check_balance_emits_alert_when_low():
    s = update_balance(tx_event("fast_food", -30000), state())
    new = check_balance(tx_event("fast_food", -30000), s)
    assert new["outbox"] == (
        (BALANCE_ALERT, {"account_id": "acc_001", "balance": 10000}),
    )


def test_notify_adds_notification():
    event = Event(BALANCE_ALERT, "ts", {"account_id": "acc_001", "balance": 100})
    new = notify(event, state())
    assert len(new["notifications"]) == 1
    assert new["notifications"][0]["type"] == BALANCE_ALERT


def test_subscribe_and_publish_calls_handler():
    b = EventBus({"count": 0}, clock=lambda: "ts")
    b.subscribe("PING", lambda e, s: {**s, "count": s["count"] + 1})
    b.publish("PING", {})
    b.publish("PING", {})
    assert b.state["count"] == 2
    assert len(b.log) == 2


def test_publish_chain_creates_two_alerts():
    b = bus()
    b.publish(
        TRANSACTION_ADDED,
        {"account_id": "acc_001", "cat_id": "fast_food", "amount": -25000},
    )
    names = tuple(e.name for e in b.log)
    assert names == (TRANSACTION_ADDED, BALANCE_ALERT, BUDGET_ALERT)
    assert len(b.state["notifications"]) == 2


def test_income_does_not_trigger_alerts():
    b = bus()
    b.publish(
        TRANSACTION_ADDED, {"account_id": "acc_001", "cat_id": "salary", "amount": 1000}
    )
    assert b.state["balances"]["acc_001"] == 41000
    assert b.state["notifications"] == ()


def test_bus_on_seed():
    b = make_bus(initial_state(*load_seed("data/seed.json")))
    before = b.state["balances"]["acc_001"]
    b.publish(
        TRANSACTION_ADDED, {"account_id": "acc_001", "cat_id": "taxi", "amount": -1000}
    )
    assert b.state["balances"]["acc_001"] == before - 1000