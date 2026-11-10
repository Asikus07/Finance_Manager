from inspect import isgenerator
from itertools import cycle

from core.domain import Category, Transaction
from core.lazy import iter_transactions, lazy_top_categories, take
from core.transforms import by_amount_range, by_category, load_seed

CATS = (
    Category("taxi", "Taxi", None, "expense"),
    Category("fuel", "Fuel", None, "expense"),
    Category("food", "Food", None, "expense"),
    Category("salary", "Salary", None, "income"),
)

TRANS = (
    Transaction("t1", "acc_001", "taxi", -1000, "2026-09-01", ""),
    Transaction("t2", "acc_001", "fuel", -5000, "2026-09-02", ""),
    Transaction("t3", "acc_001", "food", -2000, "2026-09-03", ""),
    Transaction("t4", "acc_001", "taxi", -3000, "2026-09-04", ""),
    Transaction("t5", "acc_001", "salary", 200000, "2026-09-05", ""),
    Transaction("t6", "acc_001", "fuel", -500, "2026-09-06", ""),
)


def counted(items, log):
    for x in items:
        log.append(x.id)
        yield x


def ids(items):
    return tuple(t.id for t in items)


def test_iter_transactions_is_generator():
    assert isgenerator(iter_transactions(TRANS, by_category("taxi")))


def test_iter_transactions_filters_with_closure():
    result = iter_transactions(TRANS, by_amount_range(-3000, -1000))
    assert ids(result) == ("t1", "t3", "t4")


def test_iter_transactions_reads_nothing_until_asked():
    log = []
    iter_transactions(counted(TRANS, log), by_category("taxi"))
    assert log == []


def test_take_stops_early():
    log = []
    stream = iter_transactions(counted(TRANS, log), by_category("taxi"))
    assert ids(take(stream, 1)) == ("t1",)
    assert log == ["t1"]


def test_take_works_with_infinite_stream():
    stream = iter_transactions(cycle(TRANS), by_category("fuel"))
    assert ids(take(stream, 3)) == ("t2", "t6", "t2")


def test_top_categories_order_and_k():
    result = tuple(lazy_top_categories(TRANS, CATS, 2))
    assert result == (("fuel", 5500), ("taxi", 4000))


def test_top_categories_ignores_income():
    result = dict(lazy_top_categories(TRANS, CATS, 10))
    assert "salary" not in result
    assert len(result) == 3


def test_top_categories_is_lazy():
    log = []
    top = lazy_top_categories(counted(TRANS, log), CATS, 2)
    assert log == []
    next(top)
    assert len(log) == len(TRANS)


def test_top_categories_zero_k_is_empty():
    assert tuple(lazy_top_categories(TRANS, CATS, 0)) == ()


def test_top_categories_on_seed():
    _, cats, trans, _ = load_seed("data/seed.json")
    top = tuple(lazy_top_categories(trans, cats, 3))
    assert len(top) == 3
    assert top[0][1] >= top[1][1] >= top[2][1]
