from core.domain import Account, Budget, Category, Transaction
from core.ftypes import Either, Left, Maybe, Nothing, Right, Some


def safe_category(cats: tuple[Category, ...], cat_id: str) -> Maybe:
    found = tuple(filter(lambda c: c.id == cat_id, cats))
    return Some(found[0]) if found else Nothing()


# Проверка: существует ли аккаунт?
def check_account(t: Transaction, accs: tuple[Account, ...]) -> Either:
    if any(a.id == t.account_id for a in accs):
        return Right(t)
    return Left(
        {"field": "account_id", "error": f"Account {t.account_id} was not found"}
    )


def check_sign(t: Transaction, cat: Category) -> Either:
    ok = t.amount < 0 if cat.type == "expense" else t.amount > 0
    if ok:
        return Right(t)
    return Left(
        {"field": "amount", "error": "The sum sign does not match the category type."}
    )


def check_category(t: Transaction, cats: tuple[Category, ...]) -> Either:
    not_found = Left({"field": "cat_id", "error": f"Category {t.cat_id} was not found"})
    return (
        safe_category(cats, t.cat_id)
        .map(lambda c: check_sign(t, c))
        .get_or_else(not_found)
    )


def validate_transaction(
    t: Transaction, accs: tuple[Account, ...], cats: tuple[Category, ...]
) -> Either:
    return check_account(t, accs).bind(lambda tx: check_category(tx, cats))


def spent_in(cat_id: str, trans: tuple[Transaction, ...]) -> int:
    return sum(-t.amount for t in trans if t.cat_id == cat_id and t.amount < 0)


def check_budget(b: Budget, trans: tuple[Transaction, ...]) -> Either:
    spent = spent_in(b.cat_id, trans)
    if spent <= b.limit:
        return Right(b)
    return Left(
        {
            "field": "limit",
            "error": f"The budget {b.cat_id} has been exceeded.",
            "spent": spent,
            "limit": b.limit,
        }
    )
