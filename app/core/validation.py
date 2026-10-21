"""Валидация транзакции и проверка бюджета на Maybe/Either (лаба 4).

В «счастливом пути» нет ни try/except, ни `if x is None`: каждая проверка
возвращает Either, а цепочка собирается через bind. Первая ошибка
останавливает цепочку, остальные проверки не выполняются.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from core.domain import Account, Budget, Category, Transaction
from core.ftypes import Either, Just, Left, Maybe, Nothing, Right
from core.recursion import flatten_categories
from core.transforms import add_transaction

Check = Callable[[Transaction], Either]


def safe_category(cats: tuple[Category, ...], cat_id: str) -> Maybe[Category]:
    """Категория по id: Just(категория) или Nothing, если такой нет."""
    return next((Just(c) for c in cats if c.id == cat_id), Nothing())


def in_period(ts: str, period: str, latest: str) -> bool:
    """Попадает ли дата в период бюджета: последние 7 дней или тот же месяц."""
    if period == "week":
        return 0 <= (date.fromisoformat(latest) - date.fromisoformat(ts)).days < 7
    return ts[:7] == latest[:7]


def budget_spent(
    b: Budget, trans: tuple[Transaction, ...], cats: tuple[Category, ...] = ()
) -> int:
    """Расходы бюджета за текущий период (с подкатегориями, если переданы cats)."""
    if not trans:
        return 0
    latest = max(t.ts for t in trans)
    ids = {c.id for c in flatten_categories(cats, b.cat_id)} | {b.cat_id}
    return -sum(
        t.amount
        for t in trans
        if t.cat_id in ids and t.amount < 0 and in_period(t.ts, b.period, latest)
    )


def find_budget(
    budgets: tuple[Budget, ...], cats: tuple[Category, ...], cat_id: str
) -> Maybe[Budget]:
    """Бюджет, который покрывает категорию (сама категория или её родитель)."""
    return next(
        (
            Just(b)
            for b in budgets
            if cat_id in {c.id for c in flatten_categories(cats, b.cat_id)}
        ),
        Nothing(),
    )


def check_account(accs: tuple[Account, ...]) -> Check:
    def check(t: Transaction) -> Either:
        exists = any(a.id == t.account_id for a in accs)
        return (
            Right(t)
            if exists
            else Left({"field": "account", "error": "account_not_found"})
        )

    return check


def check_category(cats: tuple[Category, ...]) -> Check:
    """Категория существует и подходит по знаку: расход < 0, доход > 0."""

    def matches_sign(t: Transaction) -> Callable[[Category], Either]:
        def check(c: Category) -> Either:
            ok = (c.type == "expense" and t.amount < 0) or (
                c.type == "income" and t.amount > 0
            )
            return (
                Right(t)
                if ok
                else Left(
                    {
                        "field": "category",
                        "error": "category_type_mismatch",
                        "category_type": c.type,
                    }
                )
            )

        return check

    def check(t: Transaction) -> Either:
        return (
            safe_category(cats, t.cat_id)
            .to_either({"field": "category", "error": "category_not_found"})
            .bind(matches_sign(t))
        )

    return check


def check_amount(t: Transaction) -> Either:
    return (
        Right(t)
        if t.amount != 0
        else Left({"field": "amount", "error": "amount_is_zero"})
    )


def validate_transaction(
    t: Transaction, accs: tuple[Account, ...], cats: tuple[Category, ...]
) -> Either[dict, Transaction]:
    """Счёт существует -> сумма не 0 -> категория существует и подходит."""
    return check_account(accs)(t).bind(check_amount).bind(check_category(cats))


def check_budget(
    b: Budget, trans: tuple[Transaction, ...], cats: tuple[Category, ...] = ()
) -> Either[dict, Budget]:
    """Right(бюджет), если расходы не больше лимита, иначе Left с деталями."""
    spent = budget_spent(b, trans, cats)
    return (
        Right(b)
        if spent <= b.limit
        else Left(
            {
                "field": "budget",
                "error": "budget_exceeded",
                "budget": b.id,
                "limit": b.limit,
                "spent": spent,
            }
        )
    )


def check_transaction_budget(
    trans: tuple[Transaction, ...],
    cats: tuple[Category, ...],
    budgets: tuple[Budget, ...],
) -> Check:
    """Не превысит ли новая транзакция бюджет своей категории (доходы не в счёт)."""

    def check(t: Transaction) -> Either:
        if t.amount >= 0:
            return Right(t)
        return (
            find_budget(budgets, cats, t.cat_id)
            .map(
                lambda b: check_budget(b, add_transaction(trans, t), cats).map(
                    lambda _: t
                )
            )
            .get_or_else(Right(t))
        )

    return check


def validation_pipeline(
    accs: tuple[Account, ...],
    cats: tuple[Category, ...],
    trans: tuple[Transaction, ...],
    budgets: tuple[Budget, ...],
) -> tuple[tuple[str, Check], ...]:
    """Шаги проверки по порядку: (название, функция Transaction -> Either)."""
    return (
        ("Account exists", check_account(accs)),
        ("Amount is not zero", check_amount),
        ("Category is valid", check_category(cats)),
        ("Budget is not exceeded", check_transaction_budget(trans, cats, budgets)),
    )
