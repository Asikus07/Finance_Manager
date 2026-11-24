import asyncio

from core.ftypes import Left
from core.lazy import lazy_top_categories
from core.memo import forecast_expenses
from core.parallel import balance_forecast, expenses_by_month
from core.report import in_month, tree_budget_check
from core.transforms import account_balance, by_date_range, load_seed


async def final_report(
    path: str, start: str, end: str, k: int = 3, period: int = 3, delay: float = 0.0
) -> dict:
    accounts, cats, trans, budgets = load_seed(path)

    chosen = tuple(filter(by_date_range(start, end), trans))
    months = tuple(sorted({t.ts[:7] for t in chosen}))

    top = tuple(lazy_top_categories(iter(chosen), cats, k))

    roots = tuple(c for c in cats if c.parent_id is None and c.type == "expense")
    forecast = {c.id: forecast_expenses(c.id, trans, period) for c in roots}

    spent, balances = await asyncio.gather(
        expenses_by_month(chosen, months, delay),
        balance_forecast(accounts, trans, delay),
    )

    check = tree_budget_check(cats)
    over_budget = tuple(
        {**r.error, "month": m}
        for m in months
        for r in (check(b, in_month(m)(chosen)) for b in budgets)
        if isinstance(r, Left)
    )

    balance = sum(a.balance + account_balance(trans, a.id) for a in accounts)

    return {
        "balance": balance,
        "expenses": sum(spent.values()),
        "expenses_by_month": spent,
        "balance_forecast": balances,
        "top_categories": top,
        "forecast": forecast,
        "over_budget": over_budget,
        "steps": (
            ("load", len(trans)),
            ("filter", len(chosen)),
            ("lazy top", len(top)),
            ("cached forecast", len(forecast)),
            ("async", len(spent) + len(balances)),
            ("budgets", len(over_budget)),
        ),
    }
