import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

MAIN = str(Path(__file__).parent.parent / "app" / "main.py")


def open_page(page, setup=None):
    at = AppTest.from_file(MAIN, default_timeout=60)
    at.session_state["current_page"] = page
    at.run()
    if setup:
        setup(at)
        at.run()
    return at


def scenario(name):
    def click(at):
        at.button(key=f"preset_{name}").click()

    return open_page("Functional Core", click)


def states(at):
    """Состояния шагов пайплайна: ok / fail / skip."""
    html = " ".join(m.value for m in at.markdown if 'class="steps"' in m.value)
    return re.findall(r'data-state="(\w+)"', html)


def verdict(at):
    html = " ".join(m.value for m in at.markdown if 'class="verdict' in m.value)
    return re.search(r'class="verdict (\w+)"', html).group(1)


def test_page_renders_without_errors():
    at = open_page("Functional Core")
    assert not at.exception
    assert states(at) == ["ok", "ok", "ok"]
    assert verdict(at) == "ok"


def test_valid_expense_scenario():
    at = scenario("expense")
    assert states(at) == ["ok", "ok", "ok"]


def test_positive_amount_is_valid_for_income_category():
    at = scenario("income")
    assert states(at) == ["ok", "ok", "ok"]
    assert verdict(at) == "ok"


def test_unknown_account_stops_chain():
    at = scenario("account")
    assert states(at) == ["fail", "skip", "skip"]
    assert verdict(at) == "fail"


def test_unknown_category_stops_after_account():
    at = scenario("category")
    assert states(at) == ["ok", "fail", "skip"]


def test_wrong_sign_is_rejected_by_category_step():
    at = scenario("sign")
    assert states(at) == ["ok", "fail", "skip"]


def test_budget_exceeded_fails_last_step():
    at = scenario("budget")
    assert states(at) == ["ok", "ok", "fail"]


def test_add_valid_transaction_extends_data():
    at = open_page("Functional Core")
    before = len(at.session_state["data"][2])
    at.button(key="val_add").click()
    at.run()
    assert len(at.session_state["data"][2]) == before + 1


def test_invalid_transaction_has_no_add_button():
    at = scenario("account")
    assert not [b for b in at.button if b.key == "val_add"]


def test_reports_shows_budget_check_expander():
    at = open_page("Reports")
    assert not at.exception
    assert "Budget check (Either)" in [e.label for e in at.expander]
