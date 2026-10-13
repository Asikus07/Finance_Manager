from pathlib import Path

import pandas as pd
import streamlit as st

from core.recursion import flatten_categories, sum_expenses_recursive
from core.transforms import (
    account_balance,
    by_amount_range,
    by_category,
    by_date_range,
    load_seed,
)

st.set_page_config(
    page_title="FinManager",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

SEED_PATH = Path(__file__).parent.parent / "data" / "seed.json"

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

st.markdown(
    """
    <style>
    .stApp {
        background: #0B0D0C;
    }

    [data-testid="stSidebar"] {
        background: #101310;
        border-right: 1px solid #252a26;
    }

    [data-testid="stSidebar"] h1 {
        font-size: 1.5rem;
        font-weight: 750;
        letter-spacing: -0.7px;
    }

    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    [data-testid="stMetric"] {
        background: #151917;
        border: 1px solid #292f2b;
        padding: 20px 22px;
        border-radius: 16px;
    }

    [data-testid="stMetricLabel"] {
        color: #a0aaa2;
    }

    [data-testid="stMetricValue"] {
        color: #f1f5f2;
        font-weight: 700;
    }

    [data-testid="stMetricDelta"] {
        color: #55cf7a;
    }

    h1, h2, h3 {
        letter-spacing: -0.6px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #292f2b;
        border-radius: 12px;
        overflow: hidden;
    }

    div.stButton > button {
        border-radius: 10px;
        border: 1px solid #303831;
    }

    hr {
        border-color: #252a26;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def get_data():
    return load_seed(str(SEED_PATH))


def money(value: int) -> str:
    return f"{value:,.0f} ₸".replace(",", " ")


def transaction_frame(trans, names):
    return pd.DataFrame(
        [
            {
                "Date": t.ts,
                "Category": names.get(t.cat_id, t.cat_id),
                "Description": t.note,
                "Amount": t.amount,
                "Type": "Income" if t.amount > 0 else "Expense",
            }
            for t in trans
        ]
    )


def page_overview():
    accounts, cats, trans, budgets = get_data()

    initial_balance = sum(a.balance for a in accounts)
    transaction_total = sum(t.amount for t in trans)
    current_balance = initial_balance + transaction_total

    income = sum(t.amount for t in trans if t.amount > 0)
    expenses = -sum(t.amount for t in trans if t.amount < 0)

    st.title("Financial Overview")
    st.caption("Your money, clearly organized.")

    st.write("")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Current balance", money(current_balance))
    c2.metric("Total income", money(income))
    c3.metric("Total expenses", money(expenses))
    c4.metric("Transactions", f"{len(trans):,}")

    st.write("")

    left, right = st.columns([1.6, 1])

    with left:
        st.subheader("Income vs expenses")

        chart_data = pd.DataFrame(
            [
                {"Type": "Income", "Amount": income},
                {"Type": "Expenses", "Amount": expenses},
            ]
        ).set_index("Type")

        st.bar_chart(
            chart_data,
            color=["#3FA95C"],
            height=300,
        )

    with right:
        st.subheader("Your accounts")

        for account in accounts:
            balance = account.balance + account_balance(
                trans, account.id
            )

            st.markdown(
                f"""
                <div style="
                    background:#151917;
                    border:1px solid #292f2b;
                    border-radius:13px;
                    padding:16px;
                    margin-bottom:12px;
                ">
                    <div style="color:#a0aaa2;font-size:13px;">
                        ACCOUNT
                    </div>
                    <div style="
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                        gap:12px;
                        margin-top:8px;
                    ">
                        <span style="font-weight:650;">
                            {account.name}
                        </span>
                        <span style="font-weight:700;color:#55cf7a;">
                            {money(balance)}
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")

    left, right = st.columns([1.2, 1])

    names = {c.id: c.name for c in cats}

    with left:
        st.subheader("Recent transactions")

        recent = sorted(trans, key=lambda t: t.ts, reverse=True)[:8]
        df = transaction_frame(recent, names)

        if not df.empty:
            df["Amount"] = df["Amount"].map(money)
            st.dataframe(
                df,
                hide_index=True,
                use_container_width=True,
            )

    with right:
        st.subheader("Budget overview")

        for budget in budgets:
            category = names.get(budget.cat_id, budget.cat_id)

            category_ids = {
                c.id
                for c in flatten_categories(cats, budget.cat_id)
            }

            spent = -sum(
                t.amount
                for t in trans
                if t.cat_id in category_ids and t.amount < 0
            )

            ratio = spent / budget.limit if budget.limit > 0 else 0
            progress = min(max(ratio, 0.0), 1.0)

            st.markdown(f"**{category}**")
            st.progress(progress)
            st.caption(
                f"{money(spent)} of {money(budget.limit)}"
                f" · {ratio:.0%} used"
            )


def page_data():
    st.title("Transactions")
    accounts, cats, trans, _ = get_data()

    names = {c.id: c.name for c in cats}
    df = transaction_frame(trans, names)

    if not df.empty:
        st.dataframe(df, hide_index=True, use_container_width=True)


def page_core():
    st.title("Functional Core")
    _, cats, trans, _ = get_data()

    roots = [
        c for c in cats
        if c.parent_id is None and c.type == "expense"
    ]

    if not roots:
        st.info("No expense categories found.")
        return

    names = {c.id: c.name for c in cats}

    root_id = st.selectbox(
        "Category",
        [c.id for c in roots],
        format_func=lambda x: names[x],
    )

    total = sum_expenses_recursive(cats, trans, root_id)
    st.metric("Total expenses", money(total))

    rows = [
        {
            "Category": c.name,
            "Expenses": money(
                sum(
                    -t.amount
                    for t in trans
                    if t.cat_id == c.id and t.amount < 0
                )
            ),
        }
        for c in flatten_categories(cats, root_id)
    ]

    st.dataframe(rows, hide_index=True, use_container_width=True)


def page_pipelines():
    st.title("Transaction Explorer")
    _, cats, trans, _ = get_data()

    names = {c.id: c.name for c in cats}

    cat_id = st.selectbox(
        "Category",
        ["All"] + [c.id for c in cats],
        format_func=lambda x: names.get(x, x),
    )

    c1, c2 = st.columns(2)
    start = c1.text_input("From date", "2026-09-01")
    end = c2.text_input("To date", "2026-10-31")

    c3, c4 = st.columns(2)
    min_amount = c3.number_input("Minimum amount", value=-100000)
    max_amount = c4.number_input("Maximum amount", value=1000000)

    result = filter(by_date_range(start, end), trans)
    result = filter(by_amount_range(min_amount, max_amount), result)

    if cat_id != "All":
        result = filter(by_category(cat_id), result)

    result = tuple(result)

    st.metric("Matching transactions", len(result))

    df = transaction_frame(result, names)
    st.dataframe(df, hide_index=True, use_container_width=True)


def page_async():
    st.title("Async / FRP")
    st.info("Event processing will be connected here.")


def page_reports():
    st.title("Reports")
    st.info("Detailed reports and forecasts will be connected here.")


def page_tests():
    st.title("Tests")
    st.info("Test results and project checks will be connected here.")


def page_about():
    st.title("About FinManager")
    st.write(
        "A financial management project built with Python and Streamlit."
    )


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
    st.title("FinManager")
    st.caption("PERSONAL FINANCE")
    st.divider()

    choice = st.radio(
        "Navigation",
        MENU,
        label_visibility="collapsed",
    )

PAGES[choice]()
