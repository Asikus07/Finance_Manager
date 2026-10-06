from pathlib import Path

import streamlit as st

from core.recursion import flatten_categories, sum_expenses_recursive
from core.transforms import (
    account_balance,
    by_amount_range,
    by_category,
    by_date_range,
    load_seed,
)

st.set_page_config(page_title="Финансовый Менеджер", page_icon="💰", layout="wide")

MENU = [
    "Overview",
    "Data",
    "Functional Core",
    "Pipelines",
    "Async/FRP",
    "Reports",
    "Tests",
    "About",
]

SEED_PATH = Path(__file__).parent.parent / "data" / "seed.json"


@st.cache_data
def get_data():
    return load_seed(str(SEED_PATH))


def page_overview():
    st.title("Обзор", anchor=False)
    accounts, cats, trans, _ = get_data()

    total = sum(a.balance + account_balance(trans, a.id) for a in accounts)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Счета", len(accounts))
    c2.metric("Категории", len(cats))
    c3.metric("Операции", len(trans))
    c4.metric("Общий баланс", f"{total:,} ₸".replace(",", " "))


def page_data():
    st.title("Данные", anchor=False)


def page_core():
    st.title("Расходы по категориям", anchor=False)
    _, cats, trans, _ = get_data()

    roots = [c.id for c in cats if c.parent_id is None and c.type == "expense"]
    names = {c.id: c.name for c in cats}
    root = st.selectbox("Категория", roots, format_func=lambda x: names[x])

    rows = [
        {"Категория": c.name, "Расходы": sum_expenses_recursive(cats, trans, c.id)}
        for c in flatten_categories(cats, root)
    ]

    st.metric("Итого расходов", sum_expenses_recursive(cats, trans, root))
    st.dataframe(rows, hide_index=True)


def page_pipelines():
    st.title("Поиск операций", anchor=False)
    _, cats, trans, _ = get_data()
    names = {c.id: c.name for c in cats}

    cat_id = st.selectbox(
        "Категория",
        ["Все"] + [c.id for c in cats],
        format_func=lambda x: names.get(x, x),
    )
    c1, c2 = st.columns(2)
    start = c1.text_input("С даты", "2026-09-01")
    end = c2.text_input("По дату", "2026-10-31")
    c3, c4 = st.columns(2)
    min_amount = c3.number_input("Сумма от", value=-100000)
    max_amount = c4.number_input("Сумма до", value=1000000)

    result = filter(by_date_range(start, end), trans)
    result = filter(by_amount_range(min_amount, max_amount), result)
    if cat_id != "Все":
        result = filter(by_category(cat_id), result)
    result = tuple(result)

    st.metric("Найдено операций", len(result))
    rows = [
        {"Дата": t.ts, "Категория": names[t.cat_id], "Сумма": t.amount} for t in result
    ]
    st.dataframe(rows, hide_index=True)


def page_async():
    st.title("События", anchor=False)


def page_reports():
    st.title("Отчёты", anchor=False)


def page_tests():
    st.title("Тесты", anchor=False)


def page_about():
    st.title("О проекте", anchor=False)


PAGES = {
    "Overview": page_overview,
    "Data": page_data,
    "Functional Core": page_core,
    "Pipelines": page_pipelines,
    "Async/FRP": page_async,
    "Reports": page_reports,
    "Tests": page_tests,
    "About": page_about,
}

with st.sidebar:
    st.title("Finance Manager ASML", anchor=False)
    choice = st.radio("Меню", MENU, label_visibility="collapsed")

PAGES[choice]()
