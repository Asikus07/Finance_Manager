from collections.abc import Callable
from dataclasses import dataclass
from typing import Any



@dataclass(frozen=True)
class Some:
    value: Any


    def map(self, f: Callable) -> "Some":
        return Some(f(self.value))
    

    def bind(self, f:Callable):
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
