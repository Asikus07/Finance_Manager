from collections.abc import Callable
from datetime import datetime
from functools import reduce

from core.domain import Account, Budget, Category, Event, Transaction
from core.recursion import flatten_categories
from core.transforms import account_balance

TRANSACTION_ADDED = "TRANSACTION_ADDED"
BUDGET_ALERT = "BUDGET_ALERT"
BALANCE_ALERT = "BALANCE_ALERT"

Handler = Callable[[Event, dict], dict]


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


class EventBus:
    def __init__(self, state: dict, clock: Callable[[], str] = now_ts):
        self.handlers: dict[str, tuple[Handler, ...]] = {}
        self.state = {**state, "outbox": ()}
        self.log: tuple[Event, ...] = ()
        self.clock = clock

    def subscribe(self, name: str, handler: Handler) -> None:
        self.handlers = {
            **self.handlers,
            name: self.handlers.get(name, ()) + (handler,),
        }

    def publish(self, name: str, payload: dict) -> dict:
        event = Event(name, self.clock(), payload)
        self.log = self.log + (event,)
        handlers = self.handlers.get(name, ())
        new_state = reduce(lambda s, h: h(event, s), handlers, self.state)
        outbox = new_state["outbox"]
        self.state = {**new_state, "outbox": ()}
        for next_name, next_payload in outbox:
            self.publish(next_name, next_payload)
        return self.state


# ---------- вспомогательные чистые функции ----------


def emit(state: dict, name: str, payload: dict) -> dict:
    return {**state, "outbox": state["outbox"] + ((name, payload),)}


def budget_root(cat_id: str | None, parents: dict, limits: dict) -> str | None:
    if cat_id is None:
        return None
    if cat_id in limits:
        return cat_id
    return budget_root(parents.get(cat_id), parents, limits)


def initial_state(
    accounts: tuple[Account, ...],
    cats: tuple[Category, ...],
    trans: tuple[Transaction, ...],
    budgets: tuple[Budget, ...],
    low_balance: int = 20000,
) -> dict:
    latest = max((t.ts for t in trans), default="")

    def spent_this_month(b: Budget) -> int:
        ids = {c.id for c in flatten_categories(cats, b.cat_id)}
        return -sum(
            t.amount
            for t in trans
            if t.cat_id in ids and t.amount < 0 and t.ts[:7] == latest[:7]
        )

    return {
        "balances": {a.id: a.balance + account_balance(trans, a.id) for a in accounts},
        "limits": {b.cat_id: b.limit for b in budgets},
        "spent": {b.cat_id: spent_this_month(b) for b in budgets},
        "parents": {c.id: c.parent_id for c in cats},
        "low_balance": low_balance,
        "notifications": (),
        "outbox": (),
    }


# ---------- подписчики (чистые функции: событие + состояние -> новое состояние) ----------


def update_balance(event: Event, state: dict) -> dict:
    acc_id = event.payload["account_id"]
    balances = state["balances"]
    new_balance = balances.get(acc_id, 0) + event.payload["amount"]
    return {**state, "balances": {**balances, acc_id: new_balance}}


def check_balance(event: Event, state: dict) -> dict:
    acc_id = event.payload["account_id"]
    balance = state["balances"].get(acc_id, 0)
    if balance < state["low_balance"]:
        return emit(state, BALANCE_ALERT, {"account_id": acc_id, "balance": balance})
    return state


def check_budget_limit(event: Event, state: dict) -> dict:
    amount = event.payload["amount"]
    root = budget_root(event.payload["cat_id"], state["parents"], state["limits"])
    if amount >= 0 or root is None:
        return state
    spent = state["spent"].get(root, 0) - amount
    new_state = {**state, "spent": {**state["spent"], root: spent}}
    limit = state["limits"][root]
    if spent > limit:
        return emit(
            new_state, BUDGET_ALERT, {"cat_id": root, "spent": spent, "limit": limit}
        )
    return new_state


def notification_text(event: Event) -> str:
    p = event.payload
    if event.name == BUDGET_ALERT:
        return f"Budget '{p['cat_id']}' exceeded: {p['spent']} of {p['limit']}"
    if event.name == BALANCE_ALERT:
        return f"Low balance on {p['account_id']}: {p['balance']}"
    return event.name


def notify(event: Event, state: dict) -> dict:
    note = {"ts": event.ts, "type": event.name, "text": notification_text(event)}
    return {**state, "notifications": state["notifications"] + (note,)}


def make_bus(state: dict, clock: Callable[[], str] = now_ts) -> EventBus:
    bus = EventBus(state, clock)
    bus.subscribe(TRANSACTION_ADDED, update_balance)
    bus.subscribe(TRANSACTION_ADDED, check_balance)
    bus.subscribe(TRANSACTION_ADDED, check_budget_limit)
    bus.subscribe(BUDGET_ALERT, notify)
    bus.subscribe(BALANCE_ALERT, notify)
    return bus