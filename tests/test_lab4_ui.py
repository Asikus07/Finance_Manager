from pathlib import Path

from streamlit.testing.v1 import AppTest

MAIN = str(Path(__file__).parent.parent / "app" / "main.py")


def open_core(setup=None):
    at = AppTest.from_file(MAIN, default_timeout=60)
    at.session_state["current_page"] = "Functional Core"
    at.run()
    if setup:
        setup(at)
        at.run()
    return at


def steps(at):
    return [m.value for m in at.markdown if m.value[:1] in "✅❌⏭"]


def test_pipeline_valid_transaction_passes_all_steps():
    at = open_core()
    assert not at.exception
    assert len(steps(at)) == 3
    assert all(s.startswith("✅") for s in steps(at))
    assert at.success[0].value.startswith("Right")


def test_pipeline_unknown_account_stops_chain():
    def pick(at):
        box = at.selectbox(key="val_account")
        box.select_index(len(box.options) - 1)

    at = open_core(pick)
    assert steps(at)[0].startswith("❌")
    assert all(s.startswith("⏭") for s in steps(at)[1:])
    assert at.error[0].value.startswith("Left")


def test_pipeline_wrong_sign_is_rejected():
    at = open_core(lambda a: a.number_input(key="val_amount").set_value(5000))
    assert steps(at)[1].startswith("❌")
    assert steps(at)[2].startswith("⏭")


def test_pipeline_budget_exceeded():
    at = open_core(lambda a: a.number_input(key="val_amount").set_value(-900000))
    assert steps(at)[2].startswith("❌")
    assert at.json[0].value  # описание ошибки Left показано


def test_add_valid_transaction_extends_data():
    at = open_core()
    before = len(at.session_state["data"][2])
    at.button(key="val_add").click()
    at.run()
    assert len(at.session_state["data"][2]) == before + 1


def test_reports_shows_budget_check_expander():
    at = AppTest.from_file(MAIN, default_timeout=60)
    at.session_state["current_page"] = "Reports"
    at.run()
    assert not at.exception
    assert "Budget check (Either)" in [e.label for e in at.expander]
