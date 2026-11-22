from collections.abc import Callable
from functools import reduce

from core.domain import Budget, Category, Transaction
from core.ftypes import Either
from core.recursion import flatten_categories
from core.validation import check_budget


def only_expenses(trans: tuple[Transaction, ...]) -> tuple[Transaction, ...]:
    return tuple(t for t in trans if t.amount < 0)


def in_month(month: str) -> Callable:
    def month_filter(trans: tuple[Transaction, ...]) -> tuple[Transaction, ...]:
        return tuple(t for t in trans if t.ts[:7] == month)

    return month_filter


def total_spent(trans: tuple[Transaction, ...]) -> int:
    return sum(-t.amount for t in trans if t.amount < 0)


def spent_by_category(trans: tuple[Transaction, ...]) -> dict[str, int]:
    return reduce(
        lambda acc, t: {**acc, t.cat_id: acc.get(t.cat_id, 0) - t.amount},
        only_expenses(trans),
        {},
    )


def tree_budget_check(cats: tuple[Category, ...]) -> Callable:
    def check_budget_tree(b: Budget, trans: tuple[Transaction, ...]) -> Either:
        ids = {c.id for c in flatten_categories(cats, b.cat_id)}
        branch = tuple(t._replace(cat_id=b.cat_id) for t in trans if t.cat_id in ids)
        return check_budget(b, branch)

    return check_budget_tree


def in_branch(cats: tuple[Category, ...], root_id: str) -> Callable:
    ids = {c.id for c in flatten_categories(cats, root_id)}

    def branch_filter(trans: tuple[Transaction, ...]) -> tuple[Transaction, ...]:
        return tuple(t for t in trans if t.cat_id in ids)

    return branch_filter


def count_expenses(trans: tuple[Transaction, ...]) -> int:
    return len(only_expenses(trans))


def average_spent(trans: tuple[Transaction, ...]) -> int:
    count = count_expenses(trans)
    return total_spent(trans) // count if count else 0
