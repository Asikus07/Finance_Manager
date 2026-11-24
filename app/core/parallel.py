import asyncio

from core.domain import Account, Transaction
from core.memo import last_months
from core.report import in_month, total_spent
from core.transforms import account_balance


async def month_total(
    trans: tuple[Transaction, ...], month: str, delay: float = 0.0
) -> tuple[str, int]:
    await asyncio.sleep(delay)
    return month, total_spent(in_month(month)(trans))


async def expenses_by_month(
    trans: tuple[Transaction, ...], months: tuple[str, ...], delay: float = 0.0
) -> dict[str, int]:
    pairs = await asyncio.gather(*(month_total(trans, m, delay) for m in months))
    return dict(pairs)


def average_change(trans: tuple[Transaction, ...], acc_id: str, n: int = 3) -> int:
    own = tuple(t for t in trans if t.account_id == acc_id)
    months = last_months(own, n)
    recent = tuple(t for t in own if t.ts[:7] in months)
    return account_balance(recent, acc_id) // len(months) if months else 0


async def account_forecast(
    acc: Account, trans: tuple[Transaction, ...], delay: float = 0.0
) -> tuple[str, int]:
    await asyncio.sleep(delay)
    current = acc.balance + account_balance(trans, acc.id)
    return acc.id, current + average_change(trans, acc.id)


async def balance_forecast(
    accounts: tuple[Account, ...], trans: tuple[Transaction, ...], delay: float = 0.0
) -> dict[str, int]:
    pairs = await asyncio.gather(*(account_forecast(a, trans, delay) for a in accounts))
    return dict(pairs)
