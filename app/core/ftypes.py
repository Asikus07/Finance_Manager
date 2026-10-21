"""Контейнеры Maybe и Either (лаба 4).

Идея: вместо `None` и исключений функция возвращает «коробку»:
  Maybe  = Just(значение) | Nothing()      — значение есть или его нет
  Either = Right(значение) | Left(ошибка)  — успех или ошибка с описанием

Над коробкой работают три операции:
  map(f)          применить f к значению внутри (пустая коробка остаётся пустой)
  bind(f)         применить f, которая сама возвращает коробку (цепочка проверок)
  get_or_else(x)  достать значение или вернуть x, если его нет
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

A = TypeVar("A")
B = TypeVar("B")
E = TypeVar("E")
F = TypeVar("F")


@dataclass(frozen=True)
class Just(Generic[A]):
    value: A

    def map(self, f: Callable[[A], B]) -> Just[B]:
        return Just(f(self.value))

    def bind(self, f: Callable[[A], Maybe[B]]) -> Maybe[B]:
        return f(self.value)

    def get_or_else(self, default: A) -> A:
        return self.value

    def to_either(self, error: E) -> Either[E, A]:
        return Right(self.value)


@dataclass(frozen=True)
class Nothing:
    def map(self, f: Callable) -> Nothing:
        return self

    def bind(self, f: Callable) -> Nothing:
        return self

    def get_or_else(self, default: A) -> A:
        return default

    def to_either(self, error: E) -> Either[E, A]:
        return Left(error)


@dataclass(frozen=True)
class Right(Generic[A]):
    value: A

    def map(self, f: Callable[[A], B]) -> Right[B]:
        return Right(f(self.value))

    def bind(self, f: Callable[[A], Either[E, B]]) -> Either[E, B]:
        return f(self.value)

    def get_or_else(self, default: A) -> A:
        return self.value

    def map_left(self, f: Callable) -> Right[A]:
        return self


@dataclass(frozen=True)
class Left(Generic[E]):
    error: E

    def map(self, f: Callable) -> Left[E]:
        return self

    def bind(self, f: Callable) -> Left[E]:
        return self

    def get_or_else(self, default: A) -> A:
        return default

    def map_left(self, f: Callable[[E], F]) -> Left[F]:
        return Left(f(self.error))


Maybe = Just[A] | Nothing
Either = Left[E] | Right[A]
