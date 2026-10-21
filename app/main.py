import calendar
from datetime import date, datetime
from html import escape
from pathlib import Path
from uuid import uuid4

import altair as alt
import pandas as pd
import streamlit as st
from core.domain import Account, Category, Transaction
from core.ftypes import Left, Right
from core.memo import forecast_expenses, forecast_raw, last_months, measure_ms
from core.recursion import flatten_categories, sum_expenses_recursive
from core.transforms import (
    account_balance,
    add_transaction,
    by_amount_range,
    by_category,
    by_date_range,
    load_seed,
)
from core.validation import check_budget, in_period, validation_pipeline

st.set_page_config(
    page_title="FinManager",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="collapsed",
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
        display: none;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    [data-testid="stHeader"] {
        height: 0;
        background: transparent;
    }

    [data-testid="stAppViewBlockContainer"] {
        padding-top: 2rem;
    }

    [data-testid="stPopover"] {
        position: relative;
        z-index: 1000;
    }

    [data-testid="stMetric"] {
        background: #151917;
        border: 1px solid #292F2B;
        padding: 20px;
        border-radius: 16px;
    }

    [data-testid="stMetricLabel"] {
        color: #A0AAA2;
    }

    [data-testid="stMetricValue"] {
        color: #F1F5F2;
        font-weight: 700;
    }

    [data-testid="stMetricDelta"] svg {
        color: #55CF7A;
    }

    h1, h2, h3 {
        letter-spacing: -0.6px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #292F2B;
        border-radius: 12px;
        overflow: hidden;
    }

    div.stButton > button {
        border-radius: 10px;
        border: 1px solid #303831;
    }

    [data-testid="stPopover"] button {
        border-radius: 10px;
    }

    hr {
        border-color: #252A26;
    }

    .account-card {
        background: #151917;
        border: 1px solid #292F2B;
        border-radius: 13px;
        padding: 16px;
        margin-bottom: 12px;
    }

    .muted {
        color: #A0AAA2;
        font-size: 12px;
    }

    .account-line {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        margin-top: 8px;
    }

    .account-balance {
        color: #55CF7A;
        font-weight: 700;
    }

    .transaction-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        background: #151917;
        border: 1px solid #292F2B;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 8px;
    }

    .positive {
        color: #55CF7A;
        font-weight: 700;
        white-space: nowrap;
    }

    .negative {
        color: #F07878;
        font-weight: 700;
        white-space: nowrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_data():
    if "data" not in st.session_state:
        st.session_state.data = load_seed(str(SEED_PATH))
    return st.session_state.data


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


def set_page(page):
    st.session_state["current_page"] = page


def render_header():
    left, right = st.columns([1.3, 5])

    with left, st.popover("☰  Menu", use_container_width=True):
        st.caption("PERSONAL FINANCE")

        for item in MENU:
            if st.button(
                item,
                key=f"menu_{item}",
                use_container_width=True,
                type=(
                    "primary"
                    if st.session_state.get("current_page", "Overview") == item
                    else "secondary"
                ),
            ):
                set_page(item)
                st.rerun()

    with right:
        st.markdown(
            """
            <div style="padding-top:5px">
                <span style="font-size:22px;font-weight:750">
                    Fin<span style="color:#55CF7A">Manager</span>
                </span>
                <span style="color:#A0AAA2;font-size:12px;margin-left:12px">
                    PERSONAL FINANCE
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()


def page_overview():
    accounts, cats, trans, budgets = get_data()
    names = {c.id: c.name for c in cats}

    # account_balance (через reduce) считает движения по счёту,
    # поэтому общий баланс = начальный остаток + движения по каждому счёту
    total_balance = sum(a.balance + account_balance(trans, a.id) for a in accounts)

    income = sum(t.amount for t in trans if t.amount > 0)
    expenses = -sum(t.amount for t in trans if t.amount < 0)

    st.title("Financial Overview")
    st.caption("Your money, clearly organized.")

    # --- ряд 1: ровно то, что требует ТЗ ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accounts", len(accounts))
    c2.metric("Categories", len(cats))
    c3.metric("Transactions", f"{len(trans):,}")
    c4.metric("Total balance", money(total_balance))

    # --- ряд 2: доходы и расходы ---
    c5, c6 = st.columns(2)
    c5.metric("Total income", money(income))
    c6.metric("Total expenses", money(expenses))

    st.write("")

    left, right = st.columns([1.6, 1])

    with left:
        st.subheader("Income vs expenses")

        daily = {}

        for t in trans:
            row = daily.setdefault(
                t.ts,
                {"Income": 0, "Expenses": 0},
            )

            if t.amount > 0:
                row["Income"] += t.amount
            elif t.amount < 0:
                row["Expenses"] += -t.amount

        chart_data = pd.DataFrame.from_dict(daily, orient="index")
        chart_data.index.name = "Date"
        chart_data = chart_data.sort_index()

        if not chart_data.empty:
            st.bar_chart(
                chart_data,
                color=["#3FA95C", "#E56B6F"],
                height=300,
                width="stretch",
            )
        else:
            st.info("There are no transactions to display yet.")

        st.caption("Daily transaction totals. Expenses are shown as positive values.")

    with right:
        st.subheader("Your accounts")

        for account in accounts:
            balance = account.balance + account_balance(trans, account.id)

            st.markdown(
                f"""
                <div class="account-card">
                    <div class="muted">ACCOUNT · {escape(account.currency)}</div>
                    <div class="account-line">
                        <span style="font-weight:650">
                            {escape(account.name)}
                        </span>
                        <span class="account-balance">
                            {money(balance)}
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")

    left, right = st.columns([1.2, 1])

    with left:
        st.subheader("Recent transactions")

        recent = sorted(trans, key=lambda t: t.ts, reverse=True)[:8]

        if not recent:
            st.info("No transactions yet.")
        else:
            for t in recent:
                category = escape(names.get(t.cat_id, t.cat_id))
                note = escape(t.note or "No description")
                date = escape(t.ts)

                amount_class = "positive" if t.amount > 0 else "negative"
                amount_sign = "+" if t.amount > 0 else ""

                st.markdown(
                    f"""
                    <div class="transaction-row">
                        <div style="min-width:0">
                            <div style="font-weight:600">{category}</div>
                            <div class="muted">{date} · {note}</div>
                        </div>
                        <div class="{amount_class}">
                            {amount_sign}{money(t.amount)}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with right:
        st.subheader("Budget overview")

        if not budgets:
            st.info("No budgets have been configured.")
        else:
            for budget in budgets:
                category = names.get(budget.cat_id, budget.cat_id)

                category_ids = {c.id for c in flatten_categories(cats, budget.cat_id)}

                spent = -sum(
                    t.amount for t in trans if t.cat_id in category_ids and t.amount < 0
                )

                ratio = spent / budget.limit if budget.limit > 0 else 0
                progress = min(max(ratio, 0.0), 1.0)

                st.markdown(f"**{category}**")

                st.progress(progress)

                remaining = budget.limit - spent

                if ratio >= 1:
                    st.caption(f"🔴 Limit exceeded by {money(abs(remaining))}")
                elif ratio >= 0.8:
                    st.caption(
                        f"🟠 {money(spent)} of {money(budget.limit)} · "
                        f"{ratio:.0%} used"
                    )
                else:
                    st.caption(
                        f"{money(spent)} of {money(budget.limit)} · "
                        f"{money(remaining)} remaining"
                    )


PALETTE = ["#F2B94B", "#6FA8DC", "#B28DFF", "#55CF7A", "#E56B6F", "#4DD0C4", "#F28CB1"]
NEUTRAL = "#8FA396"

DATA_CSS = """
<style>
.tx-row { display:flex; justify-content:space-between; align-items:center; gap:16px; padding:16px 18px; border-bottom:1px dashed #2E352F; transition:background .15s; }
.tx-row:hover { background:#151917; }
.tx-main { min-width:0; }
.tx-chips { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px; }
.chip { font-size:10px; letter-spacing:.6px; text-transform:uppercase; padding:2px 9px; border-radius:999px; border:1px solid; font-weight:600; }
.tx-title { font-size:17px; color:#E8ECE9; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.tx-side { text-align:right; flex-shrink:0; }
.tx-date { font-size:12px; color:#A0AAA2; margin-bottom:6px; }
.tx-amount { font-size:22px; font-weight:750; letter-spacing:-.5px; }
</style>
"""


def root_id(by_id, cat_id):
    """Рекурсивно поднимается по parent_id до корневой категории."""
    cat = by_id.get(cat_id)
    if cat is None or cat.parent_id is None:
        return cat_id
    return root_id(by_id, cat.parent_id)


def chip(text, color):
    return (
        f'<span class="chip" style="color:{color};'
        f'background:{color}26;border-color:{color}55">{escape(text)}</span>'
    )


def transaction_row(t, cat_name, acc_name, color):
    positive = t.amount > 0
    sign = "+" if positive else "−"
    amount_cls = "positive" if positive else "negative"
    note = escape(t.note) if t.note else "—"
    return (
        '<div class="tx-row">'
        '<div class="tx-main">'
        f'<div class="tx-chips">{chip(cat_name, color)}{chip(acc_name, NEUTRAL)}</div>'
        f'<div class="tx-title">{note}</div>'
        "</div>"
        '<div class="tx-side">'
        f'<div class="tx-date">{escape(t.ts)}</div>'
        f'<div class="tx-amount {amount_cls}">{sign} {money(abs(t.amount))}</div>'
        "</div>"
        "</div>"
    )


@st.dialog("Add transaction")
def add_transaction_dialog():
    accounts, cats, trans, budgets = get_data()

    kind = st.radio("Type", ["Expense", "Income"], horizontal=True)
    account = st.selectbox("Account", accounts, format_func=lambda a: a.name)

    options = tuple(c for c in cats if c.type == kind.lower())
    if not options:
        st.warning("No categories of this type.")
        return
    category = st.selectbox("Category", options, format_func=lambda c: c.name)

    amount = st.number_input("Amount", min_value=1, step=500, value=1000)
    day = st.date_input("Date", value=datetime.now().astimezone().date())
    note = st.text_input("Note")

    if st.button("Save", type="primary"):
        signed = amount if kind == "Income" else -amount
        new_t = Transaction(
            id=f"tx_{uuid4().hex[:8]}",
            account_id=account.id,
            cat_id=category.id,
            amount=int(signed),
            ts=day.isoformat(),
            note=note.strip(),
        )

        st.session_state.data = (accounts, cats, add_transaction(trans, new_t), budgets)
        st.rerun()


def page_data():
    st.markdown(DATA_CSS, unsafe_allow_html=True)

    accounts, cats, trans, _ = get_data()
    cat_names = {c.id: c.name for c in cats}
    acc_names = {a.id: a.name for a in accounts}
    by_id = {c.id: c for c in cats}

    roots = [c.id for c in cats if c.parent_id is None]
    root_color = {rid: PALETTE[i % len(PALETTE)] for i, rid in enumerate(roots)}

    title_col, button_col = st.columns([5, 1.4])
    title_col.title("Activity")
    if button_col.button("+ Add transaction", type="primary"):
        add_transaction_dialog()

    months = sorted({t.ts[:7] for t in trans}, reverse=True)
    search_col, month_col, type_col = st.columns([3, 1.4, 1.4])
    query = search_col.text_input(
        "Search",
        placeholder="Search by note or category",
        label_visibility="collapsed",
    )
    month = month_col.selectbox(
        "Month",
        ["All"] + months,
        format_func=lambda m: (
            "All months" if m == "All" else month_label(m, full=True)
        ),
        label_visibility="collapsed",
    )
    kind = type_col.selectbox(
        "Type", ["All", "Income", "Expense"], label_visibility="collapsed"
    )

    def matches(t):
        text = f"{t.note} {cat_names.get(t.cat_id, '')}".lower()
        return (
            query.lower() in text
            and (month == "All" or t.ts[:7] == month)
            and (kind == "All" or (kind == "Income") == (t.amount > 0))
        )

    visible = tuple(sorted(filter(matches, trans), key=lambda t: t.ts, reverse=True))

    left, right = st.columns([1, 1.25], gap="large")

    with left:
        st.caption(f"{len(visible)} transactions")
        with st.container(height=720, border=True):
            if not visible:
                st.info("Nothing found. Try changing the filters.")
            else:
                rows = (
                    transaction_row(
                        t,
                        cat_names.get(t.cat_id, t.cat_id),
                        acc_names.get(t.account_id, t.account_id),
                        root_color.get(root_id(by_id, t.cat_id), NEUTRAL),
                    )
                    for t in visible
                )
                st.markdown("".join(rows), unsafe_allow_html=True)

    with right:
        monthly = {}
        for t in trans:
            row = monthly.setdefault(t.ts[:7], {"Income": 0, "Expenses": 0})
            if t.amount > 0:
                row["Income"] += t.amount
            else:
                row["Expenses"] += -t.amount

        if not monthly:
            st.info("No data for charts yet.")
            return

        df = pd.DataFrame.from_dict(monthly, orient="index").sort_index()
        df["Savings"] = df["Income"] - df["Expenses"]
        # короткие подписи "Sep 2026" вместо "2026-09"
        df["Month"] = [month_label(m) for m in df.index]
        order = df["Month"].tolist()

        x_axis = alt.X("Month:N", sort=order, axis=alt.Axis(labelAngle=0, title=None))

        st.subheader("Expenses, income and savings")
        long_df = df.melt(
            id_vars="Month",
            value_vars=["Expenses", "Income", "Savings"],
            var_name="Series",
            value_name="Amount",
        )
        line = (
            alt.Chart(long_df)
            .mark_line(interpolate="monotone", point=True, strokeWidth=3)
            .encode(
                x=x_axis,
                y=alt.Y("Amount:Q", title=None),
                color=alt.Color(
                    "Series:N",
                    scale=alt.Scale(
                        domain=["Expenses", "Income", "Savings"],
                        range=["#E56B6F", "#3FA95C", "#F2B94B"],
                    ),
                    legend=alt.Legend(orient="bottom", title=None),
                ),
                tooltip=["Month", "Series", alt.Tooltip("Amount:Q", format=",.0f")],
            )
            .properties(height=300)
        )
        st.altair_chart(line, width="stretch")

        st.subheader("Savings by month")
        bars = (
            alt.Chart(df)
            .mark_bar(color="#F2B94B", cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=x_axis,
                y=alt.Y("Savings:Q", title=None),
                tooltip=["Month", alt.Tooltip("Savings:Q", format=",.0f")],
            )
            .properties(height=260)
        )
        st.altair_chart(bars, width="stretch")


UNKNOWN_ACCOUNT = Account("acc_999", "⚠ Unknown account (acc_999)", 0, "KZT")
UNKNOWN_CATEGORY = Category("ghost", "⚠ Unknown category (ghost)", None, "expense")

ERROR_TEXT = {
    "account_not_found": "Account does not exist",
    "amount_is_zero": "Amount must not be zero",
    "category_not_found": "Category does not exist",
    "category_type_mismatch": "Category type does not match the amount sign",
    "budget_exceeded": "Budget would be exceeded",
}


def error_text(error):
    text = ERROR_TEXT.get(error["error"], error["error"])
    if error["error"] == "budget_exceeded":
        text += f": {money(error['spent'])} of {money(error['limit'])}"
    return text


def render_validation_pipeline():
    accounts, cats, trans, budgets = get_data()

    st.divider()
    st.subheader("Transaction validation pipeline")
    st.caption(
        "Every step returns Right(transaction) or Left(error). "
        "bind runs the next step only after a Right, so the first error stops the chain."
    )

    c1, c2, c3, c4 = st.columns(4)
    account = c1.selectbox(
        "Account",
        accounts + (UNKNOWN_ACCOUNT,),
        format_func=lambda a: a.name,
        key="val_account",
    )
    category = c2.selectbox(
        "Category",
        cats + (UNKNOWN_CATEGORY,),
        format_func=lambda c: c.name,
        key="val_category",
    )
    amount = c3.number_input(
        "Amount (minus = expense)", value=-1000, step=500, key="val_amount"
    )
    latest = max(
        (t.ts for t in trans), default=datetime.now().astimezone().date().isoformat()
    )
    day = c4.date_input("Date", value=date.fromisoformat(latest), key="val_date")

    t = Transaction(
        id=f"tx_{uuid4().hex[:8]}",
        account_id=account.id,
        cat_id=category.id,
        amount=int(amount),
        ts=day.isoformat(),
        note="",
    )

    result = Right(t)
    for name, step in validation_pipeline(accounts, cats, trans, budgets):
        if isinstance(result, Left):
            st.markdown(f"⏭ {name} — skipped")
            continue
        result = result.bind(step)
        if isinstance(result, Left):
            st.markdown(f"❌ **{name}** — {error_text(result.error)}")
        else:
            st.markdown(f"✅ {name}")

    if isinstance(result, Left):
        st.error("Left: transaction rejected")
        st.json(result.error)
        return

    st.success("Right: transaction is valid")
    if st.button("Add to data", type="primary", key="val_add"):
        st.session_state.data = (accounts, cats, add_transaction(trans, t), budgets)
        st.rerun()


def page_core():
    st.title("Functional Core")
    _, cats, trans, _ = get_data()

    roots = [c for c in cats if c.parent_id is None and c.type == "expense"]

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
                sum(-t.amount for t in trans if t.cat_id == c.id and t.amount < 0)
            ),
        }
        for c in flatten_categories(cats, root_id)
    ]

    st.dataframe(rows, hide_index=True, use_container_width=True)

    render_validation_pipeline()


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


def page_tests():
    st.title("Tests")
    st.info("Test results and project checks will be connected here.")


def page_about():
    st.title("About FinManager")
    st.write("A financial management project built with Python and Streamlit.")


GREEN = "#3FA95C"
RED = "#E56B6F"
AMBER = "#F2B94B"
TRACK = "#232B26"

REPORTS_CSS = """
<style>
.kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:18px; }
.kpi { background:#151917; border:1px solid #292F2B; border-radius:16px; padding:18px 20px; }
.kpi-label { font-size:12px; letter-spacing:.6px; text-transform:uppercase; color:#A0AAA2; }
.kpi-value { font-size:28px; font-weight:750; letter-spacing:-.6px; margin:6px 0 4px; color:#F1F5F2; }
.kpi-sub { font-size:12px; }
.budget-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:14px; }
.b-card { background:#101311; border:1px solid #292F2B; border-radius:14px; padding:14px 16px; }
.b-name { font-weight:650; display:flex; align-items:center; gap:8px; }
.dot { width:9px; height:9px; border-radius:50%; display:inline-block; }
.b-sub { font-size:12px; color:#A0AAA2; margin-top:6px; }
.b-track { height:8px; border-radius:99px; background:#232B26; margin:10px 0 6px; overflow:hidden; }
.b-fill { height:100%; border-radius:99px; }
.b-pct { font-size:22px; font-weight:750; }
.note-pill { margin-top:14px; background:#1B221E; border:1px solid #2E352F; border-radius:999px; padding:9px 16px; font-size:12px; color:#A0AAA2; text-align:center; }
@media (max-width: 900px) { .kpi-grid { grid-template-columns:repeat(2,1fr); } }
</style>
"""


# ---------- ЧИСТЫЕ ПОМОЩНИКИ ----------
def month_label(m, full=False):
    """'2026-09' -> 'Sep 2026' (или 'September 2026' при full=True)"""
    names = calendar.month_name if full else calendar.month_abbr
    return f"{names[int(m[5:7])]} {m[:4]}"


def next_month(m):
    year, month = map(int, m.split("-"))
    year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return f"{year}-{month:02d}"


def status_color(ratio):
    """Зелёный до 80% лимита, жёлтый 80-100%, красный от 100%."""
    return RED if ratio >= 1 else AMBER if ratio >= 0.8 else GREEN


def budget_spent(b, cats, trans, latest):
    """Расходы по категории бюджета И всем её подкатегориям за текущий период."""
    ids = {c.id for c in flatten_categories(cats, b.cat_id)}
    return -sum(
        t.amount
        for t in trans
        if t.cat_id in ids and t.amount < 0 and in_period(t.ts, b.period, latest)
    )


def kpi(label, value, sub, sub_color="#A0AAA2"):
    return (
        '<div class="kpi">'
        f'<div class="kpi-label">{escape(label)}</div>'
        f'<div class="kpi-value">{escape(value)}</div>'
        f'<div class="kpi-sub" style="color:{sub_color}">{escape(sub)}</div>'
        "</div>"
    )


def budget_card(name, spent, limit, dot_color):
    ratio = spent / limit if limit > 0 else 0
    fill = status_color(ratio)
    width = min(ratio, 1) * 100
    return (
        '<div class="b-card">'
        f'<div class="b-name"><span class="dot" style="background:{dot_color}"></span>{escape(name)}</div>'
        f'<div class="b-sub">{money(spent)} / {money(limit)}</div>'
        f'<div class="b-track"><div class="b-fill" style="width:{width:.0f}%;background:{fill}"></div></div>'
        f'<div class="b-pct" style="color:{fill}">{ratio:.0%}</div>'
        "</div>"
    )


def run_forecasts(fn, cat_ids, trans, period, repeats):
    """Вызывает прогноз для всех категорий `repeats` раз (нужно для замера)."""
    return tuple(fn(cid, trans, period) for _ in range(repeats) for cid in cat_ids)


def page_reports():
    st.markdown(REPORTS_CSS, unsafe_allow_html=True)

    _, cats, trans, budgets = get_data()

    head, control = st.columns([4, 1.8])
    head.title("Reports")
    period = control.select_slider(
        "Months averaged for forecast", options=[1, 2, 3, 4, 5, 6], value=3
    )

    if not trans:
        st.info("No transactions yet.")
        return

    by_id = {c.id: c for c in cats}
    roots = tuple(c for c in cats if c.parent_id is None)
    root_color = {c.id: PALETTE[i % len(PALETTE)] for i, c in enumerate(roots)}
    expense_roots = tuple(c for c in roots if c.type == "expense")
    expense_ids = tuple(c.id for c in cats if c.type == "expense")

    latest = max(t.ts for t in trans)
    cur_month = latest[:7]
    monthly = {}
    for t in trans:
        row = monthly.setdefault(t.ts[:7], {"Income": 0, "Expenses": 0})
        if t.amount > 0:
            row["Income"] += t.amount
        else:
            row["Expenses"] += -t.amount
    months = sorted(monthly)

    forecasts = {
        r.id: sum(
            forecast_expenses(c.id, trans, period)
            for c in flatten_categories(cats, r.id)
        )
        for r in expense_roots
    }
    forecast_total = sum(forecasts.values())

    status = tuple((b, budget_spent(b, cats, trans, latest)) for b in budgets)
    total_limit = sum(b.limit for b, _ in status)
    total_spent = sum(s for _, s in status)
    used_ratio = total_spent / total_limit if total_limit > 0 else 0
    at_limit = sum(1 for b, s in status if b.limit > 0 and s / b.limit >= 1)

    spent_now = monthly[cur_month]["Expenses"]
    if len(months) > 1 and monthly[months[-2]]["Expenses"] > 0:
        prev = monthly[months[-2]]["Expenses"]
        change = (spent_now - prev) / prev
        sub = f"{'▲' if change > 0 else '▼'} {abs(change):.0%} vs previous month"
        sub_color = RED if change > 0 else GREEN
    else:
        sub, sub_color = "first month in the data", "#A0AAA2"

    cards = (
        kpi(
            "Forecast next month",
            money(forecast_total),
            f"average of last {len(last_months(trans, period))} month(s)",
        ),
        kpi(f"Spent in {month_label(cur_month)}", money(spent_now), sub, sub_color),
        kpi(
            "Budgets used",
            f"{used_ratio:.0%}",
            f"{money(max(total_limit - total_spent, 0))} remaining",
            status_color(used_ratio),
        ),
        kpi(
            "Budgets at limit",
            str(at_limit),
            f"of {len(status)} budgets",
            RED if at_limit else GREEN,
        ),
    )
    st.markdown(
        '<div class="kpi-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True
    )

    left, right = st.columns([1.7, 1], gap="large")

    with left, st.container(border=True):
        st.subheader("Income vs expenses")
        fc_label = f"{month_label(next_month(months[-1]))} (forecast)"
        order = [month_label(m) for m in months] + [fc_label]

        actual = pd.DataFrame(
            [
                {"Month": month_label(m), "Series": s, "Amount": monthly[m][s]}
                for m in months
                for s in ("Income", "Expenses")
            ]
        )
        fc = pd.DataFrame(
            [{"Month": fc_label, "Series": "Expenses", "Amount": forecast_total}]
        )

        x = alt.X("Month:N", sort=order, axis=alt.Axis(labelAngle=0, title=None))
        offset = alt.XOffset("Series:N", sort=["Income", "Expenses"])
        y = alt.Y("Amount:Q", title=None)

        bars = (
            alt.Chart(actual)
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=x,
                xOffset=offset,
                y=y,
                color=alt.Color(
                    "Series:N",
                    scale=alt.Scale(domain=["Income", "Expenses"], range=[GREEN, RED]),
                    legend=alt.Legend(orient="bottom", title=None),
                ),
                tooltip=["Month", "Series", alt.Tooltip("Amount:Q", format=",.0f")],
            )
        )
        fc_bar = (
            alt.Chart(fc)
            .mark_bar(
                fillOpacity=0.12,
                stroke=RED,
                strokeDash=[5, 3],
                strokeWidth=2,
                cornerRadiusTopLeft=3,
                cornerRadiusTopRight=3,
            )
            .encode(
                x=x,
                xOffset=offset,
                y=y,
                tooltip=[
                    "Month",
                    alt.Tooltip("Amount:Q", format=",.0f", title="Forecast"),
                ],
            )
        )
        st.altair_chart(alt.layer(bars, fc_bar).properties(height=320), width="stretch")

    with right, st.container(border=True):
        st.subheader("Budget usage")
        used = min(used_ratio, 1)
        ring_df = pd.DataFrame(
            {"Part": ["Used", "Left"], "Value": [used, 1 - used], "Rank": [0, 1]}
        )
        ring = (
            alt.Chart(ring_df)
            .mark_arc(innerRadius=72, outerRadius=100, cornerRadius=6)
            .encode(
                theta=alt.Theta("Value:Q", stack=True),
                order=alt.Order("Rank:Q"),
                color=alt.Color(
                    "Part:N",
                    scale=alt.Scale(
                        domain=["Used", "Left"],
                        range=[status_color(used_ratio), TRACK],
                    ),
                    legend=None,
                ),
            )
        )
        center = (
            alt.Chart(pd.DataFrame({"t": [f"{used_ratio:.0%}"]}))
            .mark_text(size=34, fontWeight="bold", color="#E8ECE9")
            .encode(text="t:N")
        )
        st.altair_chart((ring + center).properties(height=250), width="stretch")
        st.caption(f"{money(total_spent)} of {money(total_limit)} budgeted this period")

    left, right = st.columns([1, 1.25], gap="large")

    with left, st.container(border=True):
        st.subheader("Forecast (cached)")
        st.caption(f"Average monthly expenses over the last {period} month(s)")
        st.dataframe(
            [
                {"Category": r.name, "Forecast / month": money(forecasts[r.id])}
                for r in expense_roots
            ],
            hide_index=True,
            width="stretch",
        )

        repeats = st.number_input(
            "Repetitions", min_value=10, max_value=5000, value=500, step=100
        )
        if st.button("Measure cache", type="primary"):
            forecast_expenses.cache_clear()
            _, raw_ms = measure_ms(
                run_forecasts, forecast_raw, expense_ids, trans, period, repeats
            )
            _, cached_ms = measure_ms(
                run_forecasts,
                forecast_expenses,
                expense_ids,
                trans,
                period,
                repeats,
            )
            info = forecast_expenses.cache_info()
            st.session_state.bench = {
                "raw": raw_ms,
                "cached": cached_ms,
                "hits": info.hits,
                "misses": info.misses,
            }

        bench = st.session_state.get("bench")
        if bench:
            m1, m2, m3 = st.columns(3)
            m1.metric("Without cache", f"{bench['raw']:.2f} ms")
            m2.metric("With cache", f"{bench['cached']:.2f} ms")
            m3.metric("Speedup", f"×{bench['raw'] / max(bench['cached'], 1e-9):.1f}")
            st.caption(f"lru_cache: {bench['hits']} hits, {bench['misses']} misses")

    with right, st.container(border=True):
        st.subheader("Monthly budget overview")
        if not status:
            st.info("No budgets have been configured.")
        else:
            cards = (
                budget_card(
                    by_id[b.cat_id].name if b.cat_id in by_id else b.cat_id,
                    spent,
                    b.limit,
                    root_color.get(root_id(by_id, b.cat_id), NEUTRAL),
                )
                for b, spent in status
            )
            st.markdown(
                '<div class="budget-grid">' + "".join(cards) + "</div>",
                unsafe_allow_html=True,
            )

            worst, worst_spent = max(
                status, key=lambda p: p[1] / p[0].limit if p[0].limit > 0 else 0
            )
            worst_name = (
                by_id[worst.cat_id].name if worst.cat_id in by_id else worst.cat_id
            )
            worst_ratio = worst_spent / worst.limit if worst.limit > 0 else 0
            if worst_ratio >= 1:
                note = f"The {worst_name} budget is exceeded. Consider reviewing your spending."
            elif worst_ratio >= 0.8:
                note = (
                    f"You're close to exceeding your {worst_name} budget this period."
                )
            else:
                note = "All budgets are on track."
            st.markdown(
                f'<div class="note-pill">{escape(note)}</div>',
                unsafe_allow_html=True,
            )

            with st.expander("Budget check (Either)"):
                for b, _ in status:
                    name = by_id[b.cat_id].name if b.cat_id in by_id else b.cat_id
                    checked = check_budget(b, trans, cats)
                    if isinstance(checked, Left):
                        e = checked.error
                        st.markdown(
                            f"❌ **{name}** — {money(e['spent'])} of {money(e['limit'])}"
                        )
                    else:
                        st.markdown(f"✅ {name}")


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

render_header()

choice = st.session_state.get("current_page", "Overview")
PAGES[choice]()
