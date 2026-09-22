from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    balance: int
    currency: str


@dataclass(frozen=True)
class Category:
    id: str
    name: str
    parent_id: Optional[str]
    type: str  # "income" или "expense"