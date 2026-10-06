from functools import reduce

from core.domain import Category, Transaction


def flatten_categories(cats: tuple[Category, ...], root: str) -> tuple[Category, ...]:
    current = tuple(c for c in cats if c.id == root)
    children = tuple(c for c in cats if c.parent_id == root)
    return reduce(
        lambda acc, child: acc + flatten_categories(cats, child.id),
        children,
        current,
    )


def sum_expenses_recursive(
    cats: tuple[Category, ...], trans: tuple[Transaction, ...], root_id: str
) -> int:
    own = sum(-t.amount for t in trans if t.cat_id == root_id and t.amount < 0)
    children = tuple(c for c in cats if c.parent_id == root_id)
    return own + sum(sum_expenses_recursive(cats, trans, c.id) for c in children)
