from collections.abc import Callable
from functools import lru_cache
from time import perf_counter

from core.domain import Transaction


def month_of(t: Transaction) -> str:
    return t.ts[:7]


def last_months(trans: tuple[Transaction, ...], n: int) -> tuple[str, ...]:
    months = sorted(set(map(month_of, trans)))
    return tuple(months[-n:]) if n > 0 else ()


def month_spent(cat_id: str, trans: tuple[Transaction, ...], month: str) -> int:
    return sum(
        -t.amount
        for t in trans
        if t.cat_id == cat_id and t.amount < 0 and month_of(t) == month
    )


def sum_by_months(cat_id: str, trans: tuple[Transaction, ...], months: tuple[str, ...]) -> int:
    if not months:
        return 0
    return month_spent(cat_id, trans, months[0]) + sum_by_months(cat_id, trans, months[1:]) 

def forecast_raw(cat_id: str, trans: tuple[Transaction, ...], period: int) -> int:
    months = last_months(trans, period)
    if not months:
        return 0
    spent = sum(
        -t.amount
        for t in trans
        if t.cat_id == cat_id and t.amount < 0 and month_of(t) in months
    )
    return spent // len(months)


@lru_cache
def forecast_expenses(cat_id: str, trans: tuple[Transaction, ...], period: int) -> int:
    return forecast_raw(cat_id, trans, period)


def measure_ms(func: Callable, *args) -> tuple[object, float]:
    start = perf_counter()
    result = func(*args)
    return result, (perf_counter() - start) * 1000
