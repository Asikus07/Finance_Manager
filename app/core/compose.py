from collections.abc import Callable
from functools import reduce


def pipe(x, *funcs: Callable):
    return reduce(lambda acc, f: f(acc), funcs, x)


def compose(*funcs: Callable) -> Callable:
    return lambda x: pipe(x, *reversed(funcs))


def pipe_steps(x, *funcs: Callable) -> tuple[tuple[str, object], ...]:
    return reduce(
        lambda steps, f: steps + ((f.__name__, f(steps[-1][1])),),
        funcs,
        (("start", x),),
    )
