from collections.abc import Callable, Iterable, Iterator
from functools import reduce
from heapq import nlargest
from itertools import islice

from core.domain import Category, Transaction


def iter_transactions(
    trans: Iterable[Transaction], pred: Callable[[Transaction], bool]
) -> Iterator[Transaction]:
    for t in trans:
        if pred(t):
            yield t


def expenses(
    trans: Iterable[Transaction], expense_ids: frozenset[str]
) -> Iterator[Transaction]:
    return iter_transactions(trans, lambda t: t.amount < 0 and t.cat_id in expense_ids)


def add_expense(totals: dict[str, int], t: Transaction) -> dict[str, int]:
    return {**totals, t.cat_id: totals.get(t.cat_id, 0) - t.amount}


def lazy_top_categories(
    trans: Iterable[Transaction], cats: tuple[Category, ...], k: int
) -> Iterator[tuple[str, int]]:
    expense_ids = frozenset(c.id for c in cats if c.type == "expense")
    totals = reduce(add_expense, expenses(trans, expense_ids), {})
    yield from nlargest(k, totals.items(), key=lambda kv: kv[1])


def take(stream: Iterable, n: int) -> tuple:
    return tuple(islice(stream, n))
