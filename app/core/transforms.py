import json
from dataclasses import replace
from functools import reduce

from core.domain import Account, Budget, Category, Transaction


def add_transaction(
    trans: tuple[Transaction, ...], t: Transaction
) -> tuple[Transaction, ...]:
    return trans + (t,)


def update_budget(
    budgets: tuple[Budget, ...], bid: str, new_limit: int
) -> tuple[Budget, ...]:
    def apply(b: Budget) -> Budget:
        return replace(b, limit=new_limit) if b.id == bid else b

    return tuple(map(apply, budgets))


def account_balance(trans: tuple[Transaction, ...], acc_id: str) -> int:
    return reduce(
        lambda total, t: total + t.amount,
        filter(lambda t: t.account_id == acc_id, trans),
        0,
    )


def load_seed(path: str) -> tuple[tuple, tuple, tuple, tuple]:
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    return (
        tuple(Account(**a) for a in data["accounts"]),
        tuple(Category(**c) for c in data["categories"]),
        tuple(Transaction(**t) for t in data["transactions"]),
        tuple(Budget(**b) for b in data["budgets"]),
    )
