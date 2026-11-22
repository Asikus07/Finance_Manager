from collections.abc import Callable

from core.compose import pipe_steps
from core.domain import Budget, Category, Transaction
from core.ftypes import Left
from core.report import in_branch, in_month, only_expenses


class BudgetService:
    def __init__(
        self,
        validators: tuple[Callable, ...],
        calculators: tuple[Callable, ...],
        trans: tuple[Transaction, ...],
        budgets: tuple[Budget, ...],
    ):
        self.validators = tuple(validators)
        self.calculators = tuple(calculators)
        self.trans = trans
        self.budgets = budgets

    def monthly_report(self, month: str) -> dict:
        steps = pipe_steps(self.trans, in_month(month), only_expenses)
        month_trans = steps[-1][1]

        results = {f.__name__: f(month_trans) for f in self.calculators}

        checks = tuple(
            check(b, month_trans) for b in self.budgets for check in self.validators
        )
        over_budget = tuple(r.error for r in checks if isinstance(r, Left))

        return {
            "month": month,
            "steps": steps,
            **results,
            "over_budget": over_budget,
        }


class ReportService:
    def __init__(
        self,
        aggregators: tuple[Callable, ...],
        cats: tuple[Category, ...],
        trans: tuple[Transaction, ...],
    ):
        self.aggregators = tuple(aggregators)
        self.cats = cats
        self.trans = trans

    def category_report(self, cat_id: str) -> dict:
        steps = pipe_steps(self.trans, in_branch(self.cats, cat_id), only_expenses)
        branch_trans = steps[-1][1]

        results = {f.__name__: f(branch_trans) for f in self.aggregators}

        return {"category": cat_id, "steps": steps, **results}
