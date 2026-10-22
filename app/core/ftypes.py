from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Some:
    value: Any

    def map(self, f: Callable) -> "Some":
        return Some(f(self.value))

    def bind(self, f: Callable):
        return f(self.value)

    def get_or_else(self, default: Any) -> Any:
        return self.value


@dataclass(frozen=True)
class Nothing:
    def map(self, f: Callable) -> "Nothing":
        return self

    def bind(self, f: Callable) -> "Nothing":
        return self

    def get_or_else(self, default: Any) -> Any:
        return default


Maybe = Some | Nothing


@dataclass(frozen=True)
class Right:
    value: Any

    def map(self, f: Callable) -> "Right":
        return Right(f(self.value))

    def bind(self, f: Callable):
        return f(self.value)

    def get_or_else(self, default: Any) -> Any:
        return self.value


@dataclass(frozen=True)
class Left:
    error: dict

    def map(self, f: Callable) -> "Left":
        return self

    def bind(self, f: Callable) -> "Left":
        return self

    def get_or_else(self, default: Any) -> Any:
        return default


Either = Left | Right
