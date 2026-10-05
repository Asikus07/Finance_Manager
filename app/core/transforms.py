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
    return tuple(
        map(lambda b: replace(b, limit=new_limit) if b.id == bid else b, budgets)
    )


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
        tuple(map(lambda a: Account(**a), data["accounts"])),
        tuple(map(lambda c: Category(**c), data["categories"])),
        tuple(map(lambda t: Transaction(**t), data["transactions"])),
        tuple(map(lambda b: Budget(**b), data["budgets"])),
    )
