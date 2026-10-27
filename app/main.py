from datetime import date, datetime
from uuid import uuid4

from pathlib import Path
from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from core.domain import Account, Category, Transaction
from core.ftypes import Left, Nothing, Right, Some

from core.memo import forecast_expenses, forecast_raw, last_months, measure_ms
from core.recursion import flatten_categories, sum_expenses_recursive
from core.transforms import (
    account_balance,
    by_amount_range,
    by_category,
    by_date_range,
    load_seed,
    add_transaction,
)
from core.validation import check_account, check_budget, check_category

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
    :root {
        color-scheme: light;
        --fm-ink: #19372B;
        --fm-muted: #6F8074;
        --fm-forest: #12372A;
        --fm-green: #367D58;
        --fm-sage: #DDEBDD;
        --fm-paper: #F4F6F0;
        --fm-border: #E2E9E0;
        --fm-card: #FFFFFF;
    }

    html, body, [class*="css"] {
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
                     "Segoe UI", sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at 86% 3%, rgba(218, 233, 215, .58), transparent 25rem),
            linear-gradient(135deg, #F7F8F3 0%, #F1F4EE 100%);
        color: var(--fm-ink);
    }

    /* Hide Streamlit's own toolbar, Deploy button, overflow menu and footer. */
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stToolbarActions"],
    [data-testid="stDecoration"],
    [data-testid="stAppDeployButton"],
    .stAppDeployButton,
    #MainMenu,
    footer {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }

    [data-testid="stAppViewBlockContainer"] {
        padding-top: 1.35rem;
    }

    .block-container {
        max-width: 1680px;
        padding: 1.25rem 2rem 3rem;
    }

    [data-testid="stSidebar"] {
        min-width: 255px;
        max-width: 255px;
        width: 255px;
        border-right: 1px solid rgba(255,255,255,.06);
    }

    [data-testid="stSidebar"] > div:first-child {
        position: relative;
        isolation: isolate;
        overflow: hidden;
        background: linear-gradient(180deg, #102F24 0%, #12382A 58%, #0E2A20 100%);
    }
    [data-testid="stSidebar"] > div:first-child::after {
        display: none !important;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        position: relative;
        z-index: 1;
        padding-bottom: 1.25rem;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #D5E5D9;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        color: #FFFFFF;
    }

    [data-testid="stSidebar"] [data-testid="stButton"] {
        margin: .15rem 0;
    }

    [data-testid="stSidebar"] [data-testid="stButton"] button {
        min-height: 44px;
        border: 1px solid transparent;
        border-radius: 12px;
        background: transparent;
        color: #D7E7DB;
        text-align: left;
        justify-content: flex-start;
        padding: .65rem .85rem;
        transition: background .18s ease, border-color .18s ease, transform .18s ease;
    }

    [data-testid="stSidebar"] [data-testid="stButton"] button:hover {
        background: rgba(232, 244, 235, .10);
        border-color: rgba(220, 239, 225, .13);
        color: #FFFFFF;
        transform: translateX(2px);
    }

    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {
        background: linear-gradient(135deg, rgba(177, 219, 188, .24), rgba(114, 170, 132, .15));
        border-color: rgba(188, 226, 197, .24);
        color: #FFFFFF;
        box-shadow: inset 3px 0 0 #A9D8B4;
    }

    [data-testid="stSidebar"] hr {
        border-color: rgba(229, 242, 232, .13);
    }

    [data-testid="stSidebar"] .sidebar-footer {
        color: #B8CDBE;
        font-size: 12px;
        line-height: 1.7;
        margin-top: 2rem;
        padding: 1rem .85rem;
        border: 1px solid rgba(227, 241, 231, .15);
        border-radius: 14px;
        background: rgba(255,255,255,.035);
    }

    .fm-brand {
        color: #FFFFFF;
        font-size: 25px;
        font-weight: 760;
        letter-spacing: -.9px;
        line-height: 1.15;
        padding: .6rem .2rem .2rem;
    }
    .fm-brand-mark {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 34px;
        height: 34px;
        margin-right: 9px;
        border-radius: 11px;
        color: #12372A;
        background: linear-gradient(140deg, #D8EBDC, #93C3A0);
        font-size: 19px;
        vertical-align: middle;
    }
    .fm-brand-sub {
        color: #A9C5B2;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 2px;
        margin: .45rem 0 1.1rem 3px;
    }

    .fm-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        margin: 0 0 1.25rem;
        padding: .1rem 0 1rem;
        border-bottom: 1px solid rgba(190, 207, 191, .55);
    }
    .fm-topbar-title {
        color: #18372A;
        font-size: 25px;
        font-weight: 750;
        letter-spacing: -.8px;
    }
    .fm-topbar-sub {
        color: #758579;
        font-size: 12px;
        margin-top: 3px;
    }
    .fm-user-pill {
        display: inline-flex;
        align-items: center;
        gap: 9px;
        border: 1px solid #E0E8DD;
        border-radius: 999px;
        padding: 6px 12px 6px 6px;
        background: rgba(255,255,255,.82);
        color: #2C4A38;
        font-size: 12px;
        white-space: nowrap;
    }
    .fm-avatar {
        display: inline-flex;
        width: 29px;
        height: 29px;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        color: #FFFFFF;
        background: #173C2C;
        font-size: 11px;
        font-weight: 700;
    }

    h1, h2, h3, h4 {
        color: #19372B;
        letter-spacing: -.55px;
    }
    h1 { font-size: 2rem; font-weight: 760; }
    h2 { font-weight: 730; }
    h3 { font-weight: 700; }
    p, label, .stMarkdown { color: #2B4436; }
    [data-testid="stCaptionContainer"] { color: #728277; }

    [data-testid="stMetric"] {
        background: rgba(255,255,255,.92);
        border: 1px solid #E0E8DE;
        padding: 19px 20px;
        border-radius: 19px;
        box-shadow: 0 8px 22px rgba(36, 67, 43, .045);
        min-height: 126px;
    }
    [data-testid="stMetricLabel"] {
        color: #708074;
        font-size: 12px;
        font-weight: 600;
    }
    [data-testid="stMetricValue"] {
        color: #18372A;
        font-weight: 760;
        letter-spacing: -.7px;
    }
    [data-testid="stMetricDelta"] {
        font-size: 12px;
    }
    [data-testid="stMetricDelta"] svg { color: #367D58; }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255,255,255,.76);
        border-color: #E1E8DE !important;
        border-radius: 18px !important;
        box-shadow: 0 7px 22px rgba(34, 63, 40, .035);
    }
    div[data-testid="stDataFrame"],
    div[data-testid="stTable"] {
        border: 1px solid #E0E8DE;
        border-radius: 14px;
        overflow: hidden;
        background: #FFFFFF;
    }

    /* Strong, high-contrast button system — secondary actions stay visible */
    div[data-testid="stButton"] > button,
    div[data-testid="stPopover"] button,
    div[data-testid="stFormSubmitButton"] > button,
    button[data-testid^="stBaseButton-"] {
        min-height: 2.45rem;
        border-radius: 12px !important;
        border: 1px solid #A8C2AC !important;
        background: #D9E7D8 !important;
        color: #173D2B !important;
        font-weight: 700 !important;
        text-shadow: none !important;
        box-shadow: 0 3px 9px rgba(24, 61, 42, .07) !important;
        transition: background .16s ease, border-color .16s ease, transform .16s ease, box-shadow .16s ease;
    }
    div[data-testid="stButton"] > button:hover,
    div[data-testid="stPopover"] button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover,
    button[data-testid^="stBaseButton-"]:hover {
        border-color: #648F70 !important;
        background: #C5DCC6 !important;
        color: #102F21 !important;
        box-shadow: 0 5px 12px rgba(24, 61, 42, .12) !important;
        transform: translateY(-1px);
    }
    div[data-testid="stButton"] > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button[kind="primary"],
    button[data-testid="stBaseButton-primary"] {
        border: 1px solid #164B32 !important;
        color: #FFFFFF !important;
        background: linear-gradient(135deg, #236743, #12452E) !important;
        box-shadow: 0 5px 13px rgba(22, 75, 50, .2) !important;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover,
    div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover {
        color: #FFFFFF !important;
        border-color: #0D3824 !important;
        background: linear-gradient(135deg, #1C5B3A, #0C3824) !important;
    }
    /* Sidebar has its own contrast-safe states */
    [data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"],
    [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {
        background: rgba(227, 242, 230, .055) !important;
        border-color: rgba(227, 242, 230, .02) !important;
        color: #D9E9DD !important;
        box-shadow: none !important;
        text-align: left !important;
    }
    [data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"]:hover,
    [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover {
        background: rgba(227, 242, 230, .14) !important;
        border-color: rgba(227, 242, 230, .18) !important;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #3F7654, #28563D) !important;
        border-color: rgba(205, 233, 210, .35) !important;
        color: #FFFFFF !important;
        box-shadow: inset 3px 0 0 #B3D8B8, 0 4px 12px rgba(0,0,0,.08) !important;
    }

    input, textarea,
    [data-baseweb="input"] > div,
    [data-baseweb="select"] > div,
    [data-baseweb="base-input"] {
        border-color: #DCE6DA !important;
        border-radius: 11px !important;
        background: #FFFFFF !important;
    }
    /* BaseWeb select controls: force legible selected text and a branded sage border. */
    [data-baseweb="select"] > div {
        background: #FDFEF9 !important;
        border: 1px solid #B7CBB7 !important;
        border-radius: 12px !important;
        box-shadow: none !important;
        outline: none !important;
    }
    [data-baseweb="select"]:focus-within > div,
    [data-baseweb="select"] > div:focus-within {
        border-color: #367D58 !important;
        box-shadow: 0 0 0 3px rgba(54, 125, 88, .15) !important;
        outline: none !important;
    }
    [data-baseweb="select"] *, [data-baseweb="input"] * {
        color: #18372A !important;
        -webkit-text-fill-color: #18372A !important;
        opacity: 1;
    }
    [data-baseweb="select"] input::placeholder,
    [data-baseweb="input"] input::placeholder,
    [data-baseweb="textarea"] textarea::placeholder {
        color: #718376 !important;
        -webkit-text-fill-color: #718376 !important;
        opacity: 1 !important;
    }
    [data-testid="stSelectbox"] label,
    [data-testid="stMultiSelect"] label {
        color: #2B4436 !important;
        font-weight: 600 !important;
    }
    [data-testid="stCheckbox"] label,
    [data-testid="stRadio"] label { color: #2B4436 !important; }
    [data-testid="stCheckbox"] input,
    [data-testid="stRadio"] input { accent-color: #245E3F; }
    [data-baseweb="select"] [role="combobox"],
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea,
    [data-testid="stDateInput"] input,
    [data-testid="stNumberInput"] input {
        color: #18372A !important;
        -webkit-text-fill-color: #18372A !important;
        caret-color: #245E3F !important;
    }
    [data-baseweb="popover"],
    [data-baseweb="menu"],
    [role="listbox"] {
        background: #FFFFFF !important;
        color: #18372A !important;
        border: 1px solid #DCE6DA !important;
        box-shadow: 0 12px 32px rgba(20, 51, 34, .16) !important;
    }
    [role="option"], [role="menuitem"] {
        color: #18372A !important;
        background: #FFFFFF !important;
    }
    [role="option"]:hover, [role="option"][aria-selected="true"],
    [role="menuitem"]:hover {
        color: #123A28 !important;
        background: #E3EEE1 !important;
    }
    [data-testid="stExpander"] summary {
        color: #1B3E2D !important;
        background: #F0F5ED !important;
        border-radius: 12px;
    }
    [data-testid="stProgressBar"] > div {
        background: #E5ECE3;
        border-radius: 999px;
    }
    [data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, #72AC83, #2F7955);
        border-radius: 999px;
    }
    hr { border-color: #E1E8DE; }

    .welcome-banner {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
        overflow: hidden;
        padding: 27px 31px;
        margin: 0 0 20px;
        min-height: 155px;
        border-radius: 22px;
        border: 1px solid rgba(208,224,205,.9);
        background:
            radial-gradient(circle at 84% 22%, rgba(191,220,190,.55), transparent 11rem),
            linear-gradient(115deg, #FFFFFF 0%, #F5F8F1 50%, #E7F0E3 100%);
        box-shadow: 0 10px 28px rgba(38, 67, 41, .045);
    }
    .welcome-eyebrow {
        color: #66836D;
        font-size: 10px;
        font-weight: 750;
        letter-spacing: 1.8px;
        text-transform: uppercase;
        margin-bottom: 9px;
    }
    .welcome-title {
        color: #17392A;
        font-size: clamp(25px, 2.4vw, 35px);
        font-weight: 780;
        letter-spacing: -1.25px;
        line-height: 1.1;
    }
    .welcome-copy {
        color: #66796A;
        font-size: 13px;
        margin-top: 10px;
        max-width: 560px;
    }
    .welcome-art {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        width: 160px;
        height: 104px;
        border-radius: 23px;
        color: #DDEBDA;
        background: linear-gradient(145deg, #1B5038, #103323);
        box-shadow: 0 13px 25px rgba(19, 58, 39, .18);
        transform: rotate(2deg);
    }
    .welcome-art::before, .welcome-art::after {
        content: "";
        position: absolute;
        border-radius: 100% 0 100% 0;
        background: linear-gradient(145deg, #B7D8B6, #57966A);
        transform: rotate(-22deg);
        opacity: .9;
    }
    .welcome-art::before { width: 45px; height: 69px; left: 25px; top: 12px; }
    .welcome-art::after { width: 35px; height: 54px; left: 61px; top: 34px; transform: rotate(36deg); }
    .welcome-art span {
        z-index: 1;
        margin-left: 54px;
        margin-top: 28px;
        color: #F1DDA4;
        font-size: 25px;
    }

    .account-card {
        background: #FFFFFF;
        border: 1px solid #E2E9E0;
        border-radius: 15px;
        padding: 16px;
        margin-bottom: 10px;
        box-shadow: 0 5px 15px rgba(38, 67, 41, .035);
    }
    .muted { color: #758579; font-size: 12px; }
    .account-line {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        margin-top: 8px;
    }
    .account-balance { color: #2F7955; font-weight: 750; }
    .transaction-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        background: #FFFFFF;
        border: 1px solid #E2E9E0;
        border-radius: 13px;
        padding: 13px 15px;
        margin-bottom: 8px;
        box-shadow: 0 4px 12px rgba(38,67,41,.025);
    }
    .positive { color: #2F7955; font-weight: 750; white-space: nowrap; }
    .negative { color: #C95853; font-weight: 750; white-space: nowrap; }

    /* Obvious focus rings and clear disabled states */
    div[data-testid="stButton"] > button:focus-visible,
    button[data-testid^="stBaseButton-"]:focus-visible,
    input:focus-visible, textarea:focus-visible {
        outline: 3px solid rgba(64, 126, 83, .28) !important;
        outline-offset: 2px !important;
    }
    div[data-testid="stButton"] > button:disabled,
    button[data-testid^="stBaseButton-"]:disabled {
        background: #E9EEE7 !important;
        color: #69786C !important;
        border-color: #D5DED3 !important;
        opacity: .82;
    }

    /* Dashboard cards inspired by the original FinManager concept */
    .sidebar-mountain-art {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 255px;
        height: 245px;
        pointer-events: none;
        z-index: -1;
        opacity: .96;
    }
    .sidebar-mountain-art svg { display: block; width: 100%; height: 100%; }
    [data-testid="stSidebar"] .sidebar-footer { position: relative; z-index: 2; }

    .fm-section-label {
        color: #718276;
        font-size: 11px;
        font-weight: 750;
        letter-spacing: 1.25px;
        text-transform: uppercase;
        margin: 2px 0 10px;
    }
    .fm-panel-title {
        color: #19372B;
        font-size: 16px;
        font-weight: 750;
        letter-spacing: -.35px;
        margin: 0 0 3px;
    }
    .fm-panel-subtitle { color: #78887B; font-size: 11px; margin-bottom: 12px; }
    .stay-card {
        position: relative;
        overflow: hidden;
        color: #F4F7F1;
        background: linear-gradient(145deg, #1D4B35 0%, #103323 75%, #0B281C 100%);
        border: 1px solid rgba(193, 220, 194, .22);
        border-radius: 18px;
        padding: 21px 20px 19px;
        margin: 0 0 15px;
        box-shadow: 0 10px 24px rgba(20, 54, 36, .12);
    }
    .stay-card::after {
        content: "";
        position: absolute;
        width: 170px;
        height: 170px;
        right: -64px;
        top: -74px;
        border: 1px solid rgba(211, 233, 208, .14);
        border-radius: 48% 52% 62% 38%;
        transform: rotate(28deg);
        box-shadow: 0 0 0 18px rgba(211, 233, 208, .035), 0 0 0 38px rgba(211, 233, 208, .025);
    }
    .stay-mark {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 34px;
        height: 34px;
        border-radius: 50%;
        color: #DDEBDD;
        background: rgba(224, 240, 221, .13);
        border: 1px solid rgba(224, 240, 221, .12);
        font-size: 17px;
        margin-bottom: 12px;
    }
    .stay-title { color: #FFFFFF; font-size: 17px; font-weight: 750; margin-bottom: 7px; }
    .stay-copy { color: #D0E0D2; font-size: 12px; line-height: 1.65; position: relative; z-index: 1; }
    .stay-kpi { color: #FFFFFF; font-size: 21px; font-weight: 760; margin-top: 12px; }
    .stay-foot { color: #B9D0BD; font-size: 10px; margin-top: 3px; }

    .fm-mini-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 0;
        border-bottom: 1px solid #EDF1EA;
    }
    .fm-mini-row:last-child { border-bottom: 0; padding-bottom: 1px; }
    .fm-mini-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        flex: 0 0 34px;
        width: 34px;
        height: 34px;
        border-radius: 12px;
        background: #E8F1E6;
        color: #2E704B;
        font-size: 15px;
        font-weight: 750;
    }
    .fm-mini-main { min-width: 0; flex: 1; }
    .fm-mini-title { color: #254333; font-size: 12px; font-weight: 700; overflow-wrap: anywhere; }
    .fm-mini-sub { color: #7D8A7E; font-size: 10px; margin-top: 3px; }
    .fm-mini-amount { font-size: 11px; font-weight: 750; white-space: nowrap; text-align: right; }
    .fm-panel {
        background: rgba(255,255,255,.87);
        border: 1px solid #E1E8DE;
        border-radius: 17px;
        padding: 16px 16px 13px;
        margin-bottom: 15px;
        box-shadow: 0 7px 20px rgba(34, 63, 40, .035);
    }
    .fm-budget-row { margin: 11px 0 13px; }
    .fm-budget-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
    .fm-budget-name { color: #294737; font-size: 12px; font-weight: 650; }
    .fm-budget-pct { color: #708174; font-size: 10px; font-weight: 700; white-space: nowrap; }
    .fm-budget-meta { display: flex; justify-content: space-between; gap: 6px; color: #7B897D; font-size: 10px; margin-top: 4px; }
    .fm-budget-track { width: 100%; height: 6px; border-radius: 100px; background: #E8EEE6; overflow: hidden; margin-top: 7px; }
    .fm-budget-fill { height: 100%; border-radius: inherit; }
    .fm-category-row { margin: 10px 0 12px; }
    .fm-category-line { display: flex; justify-content: space-between; gap: 10px; align-items: center; color: #304A39; font-size: 11px; }
    .fm-category-name { display: flex; gap: 8px; align-items: center; font-weight: 650; }
    .fm-category-dot { width: 8px; height: 8px; border-radius: 50%; flex: 0 0 8px; }
    .fm-category-amount { color: #244333; font-weight: 750; white-space: nowrap; }
    .fm-category-track { height: 5px; border-radius: 100px; background: #E8EEE6; overflow: hidden; margin-top: 7px; }
    .fm-category-fill { height: 100%; border-radius: inherit; }
    .goal-banner {
        min-height: 115px;
        border-radius: 17px;
        padding: 19px 21px;
        color: #FFFFFF;
        background: radial-gradient(circle at 5% 110%, rgba(127, 166, 112, .36), transparent 36%), linear-gradient(120deg, #214D35, #0F3022);
        border: 1px solid rgba(198, 223, 193, .18);
        box-shadow: 0 8px 20px rgba(20, 54, 36, .10);
        margin: 1px 0 10px;
    }
    .goal-eyebrow { color: #BBD6BD; text-transform: uppercase; font-size: 9px; font-weight: 750; letter-spacing: 1.4px; margin-bottom: 7px; }
    .goal-title { color: #FFFFFF; font-size: 16px; font-weight: 750; line-height: 1.35; }
    .goal-copy { color: #D1E1D1; font-size: 11px; margin-top: 6px; }
    .fm-empty { color: #76877A; background: #F7F9F4; border: 1px dashed #D8E3D5; border-radius: 12px; padding: 14px; font-size: 12px; }
    .fm-chart-note { color: #819084; font-size: 10px; margin-top: -4px; }

    @media (max-width: 1050px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .welcome-art { width: 115px; }
    }
    @media (max-width: 700px) {
        .welcome-banner { padding: 21px; }
        .welcome-art { display: none; }
        .fm-user-pill { display: none; }
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


def polish_chart(chart):
    """Apply FinManager's soft, light visual theme to Altair charts."""
    return (
        chart.configure(background="#FFFFFF", padding=12)
        .configure_view(strokeOpacity=0, fill="#FFFFFF")
        .configure_axis(
            gridColor="#E9EEE7",
            domainColor="#DCE5DA",
            tickColor="#DCE5DA",
            labelColor="#627669",
            titleColor="#627669",
            labelFont="Inter",
            titleFont="Inter",
            labelFontSize=11,
            titleFontSize=12,
        )
        .configure_legend(
            labelColor="#53685B",
            titleColor="#53685B",
            labelFont="Inter",
            titleFont="Inter",
            orient="bottom",
        )
    )


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
    current_page = st.session_state.get("current_page", "Overview")

    with st.sidebar:
        st.markdown(
            '<div class="fm-brand"><span class="fm-brand-mark">❧</span>FinManager</div>'
            '<div class="fm-brand-sub">PERSONAL FINANCE</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        icons = {
            "Overview": "⌂",
            "Data": "◫",
            "Functional Core": "⌘",
            "Pipelines": "⤳",
            "Async/FRP": "ϟ",
            "Reports": "▥",
            "Tests": "✓",
            "About": "ⓘ",
        }
        for item in MENU:
            label = f"{icons.get(item, '•')}   {item}"
            if st.button(
                label,
                key=f"menu_{item}",
                use_container_width=True,
                type="primary" if current_page == item else "secondary",
            ):
                set_page(item)
                st.rerun()

        st.markdown(
            '<div class="sidebar-footer"><strong>FinManager</strong><br>'
            'Your money, thoughtfully managed.<br><span style="opacity:.75">Functional finance · v1.0</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="sidebar-mountain-art" aria-hidden="true">
              <svg viewBox="0 0 255 245" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <linearGradient id="fmFar" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0" stop-color="#688A6D" stop-opacity=".58"/>
                    <stop offset="1" stop-color="#2E5940" stop-opacity=".76"/>
                  </linearGradient>
                  <linearGradient id="fmMid" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0" stop-color="#426E4D" stop-opacity=".82"/>
                    <stop offset="1" stop-color="#163F2C"/>
                  </linearGradient>
                  <linearGradient id="fmNear" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0" stop-color="#204A34"/>
                    <stop offset="1" stop-color="#071E15"/>
                  </linearGradient>
                </defs>
                <path d="M0 150 L29 120 L48 137 L83 72 L117 129 L146 98 L177 145 L210 91 L255 139 L255 245 L0 245Z" fill="url(#fmFar)"/>
                <path d="M0 177 L34 143 L60 162 L97 113 L126 164 L156 133 L188 179 L222 143 L255 166 L255 245 L0 245Z" fill="url(#fmMid)"/>
                <path d="M0 206 L31 179 L57 199 L88 160 L120 205 L153 180 L184 215 L214 181 L255 204 L255 245 L0 245Z" fill="url(#fmNear)"/>
                <path d="M48 137 L83 72 L102 107 M60 162 L97 113 L113 141 M156 133 L188 179 L222 143" fill="none" stroke="#B6D7B8" stroke-opacity=".25" stroke-width="1.2"/>
                <path d="M0 221 Q62 198 121 220 T255 216 L255 245 L0 245Z" fill="#061A12" fill-opacity=".5"/>
              </svg>
            </div>
            """,
            unsafe_allow_html=True,
        )

    page_titles = {
        "Overview": "Overview",
        "Data": "Transactions",
        "Functional Core": "Functional Core",
        "Pipelines": "Pipelines",
        "Async/FRP": "Async / FRP",
        "Reports": "Reports & Forecasts",
        "Tests": "Quality & Tests",
        "About": "About FinManager",
    }
    title = page_titles.get(current_page, current_page)
    left, right = st.columns([5, 1.35], vertical_alignment="center")
    with left:
        st.markdown(
            f'<div class="fm-topbar"><div><div class="fm-topbar-title">{escape(title)}</div>'
            '<div class="fm-topbar-sub">A clearer view of your financial life</div></div></div>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            '<div style="display:flex;justify-content:flex-end;padding-bottom:1rem">'
            '<div class="fm-user-pill"><span class="fm-avatar">AA</span>'
            '<span>Askar Abdrakhman</span></div></div>',
            unsafe_allow_html=True,
        )

def page_overview():
    accounts, cats, trans, budgets = get_data()
    names = {category.id: category.name for category in cats}
    account_names = {account.id: account.name for account in accounts}

    # The same domain calculations used elsewhere in the app remain the source of truth.
    total_balance = sum(account.balance + account_balance(trans, account.id) for account in accounts)
    base_balance = sum(account.balance for account in accounts)
    total_income = sum(t.amount for t in trans if t.amount > 0)
    total_expenses = -sum(t.amount for t in trans if t.amount < 0)
    latest_date = max((t.ts for t in trans), default=date.today().isoformat())

    monthly = {}
    for transaction in trans:
        row = monthly.setdefault(transaction.ts[:7], {"Income": 0, "Expenses": 0})
        if transaction.amount > 0:
            row["Income"] += transaction.amount
        elif transaction.amount < 0:
            row["Expenses"] += -transaction.amount
    months = sorted(monthly)
    active_month = months[-1] if months else date.today().strftime("%Y-%m")
    month_income = monthly.get(active_month, {}).get("Income", 0)
    month_expenses = monthly.get(active_month, {}).get("Expenses", 0)

    budget_status = [(budget, budget_spent(budget, cats, trans, latest_date)) for budget in budgets]
    budgets_on_track = sum(1 for budget, spent in budget_status if budget.limit <= 0 or spent < budget.limit)
    near_or_over = [
        (budget, spent, spent / budget.limit if budget.limit > 0 else 0)
        for budget, spent in budget_status
        if budget.limit > 0 and spent / budget.limit >= .8
    ]

    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    current_month_label = month_label(active_month) if months else datetime.now().strftime("%b %Y")

    # Main dashboard greeting and a compact status panel on the right.
    content_col, side_col = st.columns([2.45, 0.95], gap="large")

    with content_col:
        st.markdown(
            '<div class="welcome-banner">'
            '<div><div class="welcome-eyebrow">YOUR FINANCES AT A GLANCE</div>'
            f'<div class="welcome-title">{greeting}, Askar</div>'
            '<div class="welcome-copy">Here\'s what\'s happening with your finances today.</div>'
            f'<div class="welcome-copy" style="font-size:11px;margin-top:7px">{escape(datetime.now().strftime("%d %B %Y"))} · Latest activity: {escape(current_month_label)}</div>'
            '</div><div class="welcome-art"><span>✦</span></div></div>',
            unsafe_allow_html=True,
        )

        k1, k2, k3, k4 = st.columns(4, gap="small")
        k1.metric("Total balance", money(total_balance))
        k2.metric("Monthly income", money(month_income))
        k3.metric("Monthly expenses", money(month_expenses))
        k4.metric("Budgets on track", f"{budgets_on_track} / {len(budgets)}" if budgets else "0 / 0")

        chart_left, chart_right = st.columns([1.18, 1], gap="medium")
        with chart_left, st.container(border=True):
            st.markdown('<div class="fm-panel-title">Balance dynamics</div>', unsafe_allow_html=True)
            st.markdown('<div class="fm-panel-subtitle">Monthly balance movement across your accounts</div>', unsafe_allow_html=True)
            if months:
                running_balance = base_balance
                balance_rows = []
                for month in months:
                    running_balance += monthly[month]["Income"] - monthly[month]["Expenses"]
                    balance_rows.append({"Month": month_label(month), "Balance": running_balance, "MonthKey": month})
                balance_df = pd.DataFrame(balance_rows)
                month_order = balance_df["Month"].tolist()
                x_balance = alt.X("Month:N", sort=month_order, axis=alt.Axis(labelAngle=0, title=None, labelLimit=80))
                area = alt.Chart(balance_df).mark_area(color="#70A981", opacity=.15).encode(
                    x=x_balance,
                    y=alt.Y("Balance:Q", title=None, scale=alt.Scale(zero=False), axis=alt.Axis(format="~s")),
                    tooltip=["Month", alt.Tooltip("Balance:Q", format=",.0f", title="Balance (₸)")],
                )
                line = alt.Chart(balance_df).mark_line(color="#28764D", strokeWidth=2.8, point=alt.OverlayMarkDef(color="#28764D", filled=True, size=48)).encode(
                    x=x_balance,
                    y=alt.Y("Balance:Q", title=None, scale=alt.Scale(zero=False), axis=alt.Axis(format="~s")),
                    tooltip=["Month", alt.Tooltip("Balance:Q", format=",.0f", title="Balance (₸)")],
                )
                st.altair_chart(polish_chart((area + line).properties(height=235)), width="stretch")
            else:
                st.markdown('<div class="fm-empty">Add transactions to see your balance trend.</div>', unsafe_allow_html=True)

        with chart_right, st.container(border=True):
            st.markdown('<div class="fm-panel-title">Expenses by category</div>', unsafe_allow_html=True)
            st.markdown('<div class="fm-panel-subtitle">Where your money goes</div>', unsafe_allow_html=True)
            root_expenses = [category for category in cats if category.parent_id is None and category.type == "expense"]
            category_rows = []
            for root in root_expenses:
                branch_ids = {category.id for category in flatten_categories(cats, root.id)}
                spent = -sum(t.amount for t in trans if t.cat_id in branch_ids and t.amount < 0)
                if spent > 0:
                    category_rows.append({"Category": root.name, "Amount": spent})
            category_rows.sort(key=lambda row: row["Amount"], reverse=True)
            if category_rows:
                cat_df = pd.DataFrame(category_rows)
                colors = ["#245A40", "#5EAA71", "#8CC497", "#E1B45C", "#D9C99B", "#B9C0B4", "#6C9A7B"]
                domain = cat_df["Category"].tolist()
                donut = alt.Chart(cat_df).mark_arc(innerRadius=63, outerRadius=91, cornerRadius=5, padAngle=.015).encode(
                    theta=alt.Theta("Amount:Q", stack=True),
                    color=alt.Color("Category:N", scale=alt.Scale(domain=domain, range=colors[:len(domain)]), legend=alt.Legend(title=None, orient="bottom", labelLimit=120)),
                    tooltip=["Category", alt.Tooltip("Amount:Q", format=",.0f", title="Expenses (₸)")],
                ).properties(height=235)
                st.altair_chart(polish_chart(donut), width="stretch")
                st.caption(f"Total recorded expenses: {money(total_expenses)}")
            else:
                st.markdown('<div class="fm-empty">No expenses are available for the chart yet.</div>', unsafe_allow_html=True)

        account_col, budget_col, category_col = st.columns([1, 1.08, 1], gap="medium")
        with account_col, st.container(border=True):
            st.markdown('<div class="fm-panel-title">Your accounts</div><div class="fm-panel-subtitle">Balances across your accounts</div>', unsafe_allow_html=True)
            if accounts:
                account_icons = ["◉", "◇", "▣", "◈"]
                for index, account in enumerate(accounts[:5]):
                    balance = account.balance + account_balance(trans, account.id)
                    st.markdown(
                        '<div class="fm-mini-row">'
                        f'<div class="fm-mini-icon">{account_icons[index % len(account_icons)]}</div>'
                        '<div class="fm-mini-main">'
                        f'<div class="fm-mini-title">{escape(account.name)}</div>'
                        f'<div class="fm-mini-sub">{escape(account.currency)} · account</div>'
                        '</div>'
                        f'<div class="fm-mini-amount" style="color:#2F7955">{money(balance)}</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown('<div class="fm-empty">No accounts found.</div>', unsafe_allow_html=True)

        with budget_col, st.container(border=True):
            st.markdown('<div class="fm-panel-title">Budgets</div><div class="fm-panel-subtitle">Spending against your limits</div>', unsafe_allow_html=True)
            if budget_status:
                for budget, spent in budget_status[:5]:
                    category_name = names.get(budget.cat_id, budget.cat_id)
                    ratio = spent / budget.limit if budget.limit > 0 else 0
                    width = min(max(ratio, 0), 1) * 100
                    fill = "#C85E56" if ratio >= 1 else "#D4A548" if ratio >= .8 else "#3B895C"
                    st.markdown(
                        '<div class="fm-budget-row">'
                        '<div class="fm-budget-head">'
                        f'<span class="fm-budget-name">{escape(category_name)}</span>'
                        f'<span class="fm-budget-pct">{ratio:.0%}</span></div>'
                        '<div class="fm-budget-track">'
                        f'<div class="fm-budget-fill" style="width:{width:.1f}%;background:{fill}"></div></div>'
                        '<div class="fm-budget-meta">'
                        f'<span>{money(spent)} spent</span><span>{money(budget.limit)} limit</span>'
                        '</div></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown('<div class="fm-empty">Create a budget to track your spending.</div>', unsafe_allow_html=True)

        with category_col, st.container(border=True):
            st.markdown('<div class="fm-panel-title">Top categories</div><div class="fm-panel-subtitle">Highest expense categories</div>', unsafe_allow_html=True)
            if category_rows:
                max_spend = max(row["Amount"] for row in category_rows) or 1
                for row in category_rows[:5]:
                    share = row["Amount"] / max(total_expenses, 1)
                    width = row["Amount"] / max_spend * 100
                    color = ["#245A40", "#5EAA71", "#8CC497", "#D4A548", "#D76560"][category_rows.index(row) % 5]
                    st.markdown(
                        '<div class="fm-category-row"><div class="fm-category-line">'
                        f'<span class="fm-category-name"><span class="fm-category-dot" style="background:{color}"></span>{escape(row["Category"])}</span>'
                        f'<span class="fm-category-amount">{money(row["Amount"])}</span></div>'
                        '<div class="fm-category-track">'
                        f'<div class="fm-category-fill" style="width:{width:.1f}%;background:{color}"></div></div>'
                        f'<div class="fm-budget-meta"><span>{share:.0%} of expenses</span></div></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown('<div class="fm-empty">Category totals will appear here.</div>', unsafe_allow_html=True)

        goal_col, actions_col = st.columns([1.15, 1], gap="medium")
        with goal_col:
            st.markdown(
                '<div class="goal-banner"><div class="goal-eyebrow">Plan · Track · Grow</div>'
                '<div class="goal-title">Small steps make stronger financial habits.</div>'
                '<div class="goal-copy">Keep your spending visible and your budgets realistic.</div></div>',
                unsafe_allow_html=True,
            )
        with actions_col, st.container(border=True):
            st.markdown('<div class="fm-panel-title">Quick actions</div><div class="fm-panel-subtitle">Jump straight to what you need</div>', unsafe_allow_html=True)
            action1, action2 = st.columns(2, gap="small")
            action3, action4 = st.columns(2, gap="small")
            if action1.button("＋ Add transaction", key="overview_add_tx", use_container_width=True, type="primary"):
                add_transaction_dialog()
            if action2.button("▤ View reports", key="overview_reports", use_container_width=True):
                set_page("Reports")
                st.rerun()
            if action3.button("↗ Explore data", key="overview_data", use_container_width=True):
                set_page("Data")
                st.rerun()
            if action4.button("◎ Functional core", key="overview_core", use_container_width=True):
                set_page("Functional Core")
                st.rerun()

    with side_col:
        highest_ratio = max((spent / budget.limit for budget, spent in budget_status if budget.limit > 0), default=0)
        if any(b.limit > 0 and spent >= b.limit for b, spent in budget_status):
            status_message = "One or more budgets have reached their limit. Review the categories below."
        elif highest_ratio >= .8:
            status_message = "You are getting close to a budget limit. A quick review can help you stay on track."
        elif len(months) > 1:
            prev_expenses = monthly[months[-2]]["Expenses"]
            last_expenses = monthly[months[-1]]["Expenses"]
            if prev_expenses > 0 and last_expenses < prev_expenses:
                saved_pct = (prev_expenses - last_expenses) / prev_expenses
                status_message = f"Recorded expenses are {saved_pct:.0%} lower than the previous month. Nice progress."
            else:
                status_message = "Your activity is up to date. Keep an eye on spending and upcoming budget limits."
        else:
            status_message = "Your financial overview is ready. Track transactions to see your trends develop."
        st.markdown(
            '<div class="stay-card"><div class="stay-mark">❧</div>'
            '<div class="stay-title">Stay on track</div>'
            f'<div class="stay-copy">{escape(status_message)}</div>'
            f'<div class="stay-kpi">{money(total_balance)}</div>'
            '<div class="stay-foot">Current total balance</div></div>',
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown('<div class="fm-panel-title">Recent transactions</div><div class="fm-panel-subtitle">Latest account activity</div>', unsafe_allow_html=True)
            recent = sorted(trans, key=lambda transaction: (transaction.ts, transaction.id), reverse=True)[:5]
            if recent:
                for transaction in recent:
                    is_income = transaction.amount > 0
                    tx_color = "#2F7955" if is_income else "#C95853"
                    tx_sign = "+" if is_income else "−"
                    category_name = names.get(transaction.cat_id, transaction.cat_id)
                    st.markdown(
                        '<div class="fm-mini-row">'
                        f'<div class="fm-mini-icon" style="background:{"#E4F1E6" if is_income else "#F8E9E5"};color:{tx_color}">{"↑" if is_income else "↓"}</div>'
                        '<div class="fm-mini-main">'
                        f'<div class="fm-mini-title">{escape(transaction.note or category_name)}</div>'
                        f'<div class="fm-mini-sub">{escape(category_name)} · {escape(transaction.ts)}</div>'
                        '</div>'
                        f'<div class="fm-mini-amount" style="color:{tx_color}">{tx_sign}{money(abs(transaction.amount))}</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown('<div class="fm-empty">No transactions yet.</div>', unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown('<div class="fm-panel-title">Budget alerts</div><div class="fm-panel-subtitle">Budgets that may need attention</div>', unsafe_allow_html=True)
            if near_or_over:
                for budget, spent, ratio in sorted(near_or_over, key=lambda item: item[2], reverse=True)[:3]:
                    name = names.get(budget.cat_id, budget.cat_id)
                    alert_color = "#C95853" if ratio >= 1 else "#B78322"
                    alert_label = "Limit exceeded" if ratio >= 1 else "Near limit"
                    st.markdown(
                        '<div class="fm-mini-row">'
                        f'<div class="fm-mini-icon" style="background:{"#F8E8E5" if ratio >= 1 else "#F7F0DD"};color:{alert_color}">{"!" if ratio >= 1 else "⌁"}</div>'
                        '<div class="fm-mini-main">'
                        f'<div class="fm-mini-title">{escape(name)}</div>'
                        f'<div class="fm-mini-sub">{alert_label}</div>'
                        '</div>'
                        f'<div class="fm-mini-amount" style="color:{alert_color}">{ratio:.0%}</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown('<div class="fm-empty">All configured budgets are below 80% of their limits.</div>', unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown('<div class="fm-panel-title">Monthly forecast</div><div class="fm-panel-subtitle">Cached estimate from recent expense history</div>', unsafe_allow_html=True)
            forecast_period = min(3, max(1, len(last_months(trans, 3)))) if trans else 3
            expense_roots_for_forecast = [category for category in cats if category.parent_id is None and category.type == "expense"]
            forecast_total = sum(
                forecast_expenses(branch_category.id, trans, forecast_period)
                for root in expense_roots_for_forecast
                for branch_category in flatten_categories(cats, root.id)
            ) if trans else 0
            st.markdown(f'<div class="stay-kpi" style="color:#19372B;margin-top:2px">{money(forecast_total)}</div>', unsafe_allow_html=True)
            st.caption(f"Expected monthly expenses · average over {forecast_period} period(s)")
            if len(months) > 1:
                trend_rows = [
                    {"Month": month_label(month), "Expenses": monthly[month]["Expenses"]}
                    for month in months[-4:]
                ]
                trend_df = pd.DataFrame(trend_rows)
                trend_order = trend_df["Month"].tolist()
                sparkline = alt.Chart(trend_df).mark_line(color="#367D58", strokeWidth=2.5, point=alt.OverlayMarkDef(color="#367D58", filled=True, size=28)).encode(
                    x=alt.X("Month:N", sort=trend_order, axis=alt.Axis(labels=False, ticks=False, domain=False, title=None)),
                    y=alt.Y("Expenses:Q", axis=None, title=None),
                    tooltip=["Month", alt.Tooltip("Expenses:Q", format=",.0f")],
                ).properties(height=82)
                st.altair_chart(polish_chart(sparkline), width="stretch")
            if st.button("Open reports", key="overview_forecast_reports", use_container_width=True):
                set_page("Reports")
                st.rerun()


PALETTE = ["#D4A548", "#6B9ED2", "#9A8BCB", "#4F9B73", "#D86C68", "#64B8AD", "#D58BA9"]
NEUTRAL = "#7B8E80"
 
DATA_CSS = """
<style>
.tx-row { display:flex; justify-content:space-between; align-items:center; gap:16px; padding:16px 18px; border-bottom:1px dashed #E2E9E0; transition:background .15s; }
.tx-row:hover { background:#FFFFFF; }
.tx-main { min-width:0; }
.tx-chips { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px; }
.chip { font-size:10px; letter-spacing:.6px; text-transform:uppercase; padding:2px 9px; border-radius:999px; border:1px solid; font-weight:600; }
.tx-title { font-size:17px; color:#203D30; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.tx-side { text-align:right; flex-shrink:0; }
.tx-date { font-size:12px; color:#6F8074; margin-bottom:6px; }
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
    day = st.date_input("Date", value=date.today())
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
            "All months"
            if m == "All"
            else datetime.strptime(m, "%Y-%m").strftime("%B %Y")
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
        df["Month"] = [datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in df.index]
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
                        range=["#D76560", "#367D58", "#F2B94B"],
                    ),
                    legend=alt.Legend(orient="bottom", title=None),
                ),
                tooltip=["Month", "Series", alt.Tooltip("Amount:Q", format=",.0f")],
            )
            .properties(height=300)
        )
        st.altair_chart(polish_chart(line), width="stretch")
 
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
        st.altair_chart(polish_chart(bars), width="stretch")
 

CORE_CSS = """
<style>
.sec-head { margin:6px 0 14px; }
.sec-title { font-size:22px; font-weight:750; letter-spacing:-.5px; color:#18362A; margin-top:2px; }
.sec-sub { font-size:13px; color:#6F8074; margin-top:4px; }
.bd-row { display:grid; grid-template-columns:1fr auto; gap:7px 16px; padding:12px 4px; border-bottom:1px dashed #E2E9E0; }
.bd-row:last-child { border-bottom:none; }
.bd-name { color:#203D30; font-weight:600; display:flex; align-items:center; gap:9px; }
.bd-name .dot { flex-shrink:0; }
.bd-sub { color:#7B8E80; font-size:12px; font-weight:500; }
.bd-amount { font-weight:750; color:#18362A; text-align:right; }
.bd-track { grid-column:1 / -1; height:6px; border-radius:99px; background:#E8EEE7; overflow:hidden; }
.bd-fill { height:100%; border-radius:99px; }
.chip { font-size:10px; letter-spacing:.6px; text-transform:uppercase; padding:2px 9px; border-radius:999px; border:1px solid; font-weight:700; flex-shrink:0; }
.sc-label { font-size:11px; letter-spacing:1px; text-transform:uppercase; color:#7B8E80; font-weight:700; margin:2px 0 8px; }
.card-head { display:flex; align-items:center; gap:12px; margin-bottom:10px; }
.card-num { width:28px; height:28px; border-radius:9px; background:#2F795522; border:1px solid #2F795555; color:#2F7955; font-weight:800; display:flex; align-items:center; justify-content:center; font-size:13px; }
.card-title { font-size:17px; font-weight:700; color:#18362A; }
.card-sub { font-size:12px; color:#7B8E80; }
.hint { display:flex; align-items:center; gap:10px; background:#FBFCF8; border:1px solid #E2E9E0; border-radius:12px; padding:10px 12px; margin:-4px 0 14px; font-size:12px; color:#6F8074; }
.steps { display:flex; flex-direction:column; gap:10px; margin:6px 0 14px; }
.step { display:flex; gap:14px; align-items:flex-start; padding:14px 16px; border-radius:14px; border:1px solid #E2E9E0; background:#FBFCF8; transition:transform .15s; }
.step-ico { width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:800; flex-shrink:0; font-size:14px; color:#F4F6F0; }
.step-body { min-width:0; flex:1; }
.step-top { display:flex; justify-content:space-between; align-items:center; gap:10px; }
.step-name { font-weight:700; color:#203D30; }
.step-fn { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11.5px; color:#7B8E80; margin-top:2px; }
.step-msg { font-size:13px; margin-top:8px; }
.badge { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11px; font-weight:700; padding:3px 10px; border-radius:999px; border:1px solid; white-space:nowrap; }
.step[data-state="ok"] { border-color:#367D5866; background:#367D5812; }
.step[data-state="ok"] .step-ico { background:#2F7955; }
.step[data-state="ok"] .badge { color:#2F7955; background:#2F79551f; border-color:#2F795555; }
.step[data-state="ok"] .step-msg { color:#4C8964; }
.step[data-state="fail"] { border-color:#D7656077; background:#D7656014; }
.step[data-state="fail"] .step-ico { background:#D76560; }
.step[data-state="fail"] .badge { color:#C95853; background:#D765601f; border-color:#D7656055; }
.step[data-state="fail"] .step-msg { color:#BD514C; }
.step[data-state="skip"] { border-style:dashed; opacity:.55; }
.step[data-state="skip"] .step-ico { background:#E7ECE5; color:#6F8074; }
.step[data-state="skip"] .badge { color:#7B8E80; border-color:#E7ECE5; }
.step[data-state="skip"] .step-msg { color:#7B8E80; }
.verdict { display:flex; align-items:center; gap:16px; padding:16px 18px; border-radius:14px; border:1px solid; margin-bottom:12px; }
.verdict.ok { background:#367D5818; border-color:#367D5877; }
.verdict.fail { background:#D7656018; border-color:#D7656077; }
.v-badge { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-weight:800; font-size:15px; padding:8px 14px; border-radius:10px; color:#F4F6F0; }
.verdict.ok .v-badge { background:#2F7955; }
.verdict.fail .v-badge { background:#D76560; }
.v-title { font-size:17px; font-weight:750; color:#18362A; }
.v-sub { font-size:12.5px; color:#6F8074; margin-top:3px; }
</style>
"""

UNKNOWN_ACCOUNT = Account("acc_999", "⚠ Unknown account (acc_999)", 0, "KZT")
UNKNOWN_CATEGORY = Category("ghost", "⚠ Unknown category (ghost)", None, "expense")

PRESETS = (
    ("✅ Valid expense", "expense"),
    ("💰 Valid income", "income"),
    ("🚫 Unknown account", "account"),
    ("❓ Unknown category", "category"),
    ("± Wrong sign", "sign"),
    ("💸 Over budget", "budget"),
)


def covering_budget(cats, budgets, cat_id):
    found = next(
        (
            b
            for b in budgets
            if cat_id in {c.id for c in flatten_categories(cats, b.cat_id)}
        ),
        None,
    )
    return Some(found) if found else Nothing()


def budget_view(b, cats, trans):
    ids = {c.id for c in flatten_categories(cats, b.cat_id)}
    latest = max((t.ts for t in trans), default="")
    return tuple(
        t._replace(cat_id=b.cat_id)
        for t in trans
        if t.cat_id in ids and in_period(t.ts, b.period, latest)
    )


def budget_step(cats, trans, budgets):

    def step(t):
        if t.amount >= 0:
            return Right(t)
        return (
            covering_budget(cats, budgets, t.cat_id)
            .map(
                lambda b: check_budget(
                    b, budget_view(b, cats, add_transaction(trans, t))
                ).map(lambda _: t)
            )
            .get_or_else(Right(t))
        )

    return step


def budget_note(t, cats, trans, budgets):
    if t.amount >= 0:
        return "Income is not limited by budgets"
    names = {c.id: c.name for c in cats}

    def describe(b):
        spent = sum(-x.amount for x in budget_view(b, cats, add_transaction(trans, t)))
        return f"{names.get(b.cat_id, b.cat_id)}: {money(spent)} of {money(b.limit)}"

    return (
        covering_budget(cats, budgets, t.cat_id)
        .map(describe)
        .get_or_else("No budget covers this category")
    )


def apply_preset(name):
    accounts, cats, _, _ = get_data()
    expense, income = demo_category(cats, "expense"), demo_category(cats, "income")
    values = {
        "expense": (accounts[0], expense, -1000),
        "income": (accounts[0], income, 200000),
        "account": (UNKNOWN_ACCOUNT, expense, -1000),
        "category": (accounts[0], UNKNOWN_CATEGORY, -1000),
        "sign": (accounts[0], expense, 5000),
        "budget": (accounts[0], expense, -900000),
    }[name]
    st.session_state.val_account = values[0]
    st.session_state.val_category = values[1]
    st.session_state.val_amount = values[2]


def demo_category(cats, kind):
    of_kind = tuple(c for c in cats if c.type == kind)
    return next((c for c in of_kind if c.parent_id), of_kind[0] if of_kind else cats[0])


def error_text(error):
    text = error["error"]
    if "spent" in error:
        text += f" ({money(error['spent'])} of {money(error['limit'])})"
    return text


def depth_of(by_id, cat_id):
    cat = by_id.get(cat_id)
    return (
        0
        if cat is None or cat.parent_id is None
        else 1 + depth_of(by_id, cat.parent_id)
    )


def section_head(title, text):
    return (
        '<div class="sec-head">'
        f'<div class="sec-title">{escape(title)}</div>'
        f'<div class="sec-sub">{escape(text)}</div>'
        "</div>"
    )


def card_head(num, title, sub):
    return (
        '<div class="card-head">'
        f'<div class="card-num">{escape(num)}</div>'
        f'<div><div class="card-title">{escape(title)}</div>'
        f'<div class="card-sub">{escape(sub)}</div></div>'
        "</div>"
    )


def breakdown_row(name, depth, own, top, color):
    width = own / top * 100 if top else 0
    pad = depth * 20
    prefix = "└ " if depth else ""
    return (
        '<div class="bd-row">'
        f'<div class="bd-name" style="padding-left:{pad}px">'
        f'<span class="dot" style="background:{color}"></span>'
        f'<span><span class="bd-sub">{prefix}</span>{escape(name)}</span></div>'
        f'<div class="bd-amount">{money(own)}</div>'
        f'<div class="bd-track"><div class="bd-fill" style="width:{width:.0f}%;'
        f'background:{color}"></div></div>'
        "</div>"
    )


def step_html(index, name, fn, state, message):
    icon = {"ok": "✓", "fail": "✕", "skip": "–"}[state]
    badge = {"ok": "Right(t)", "fail": "Left(error)", "skip": "skipped"}[state]
    return (
        f'<div class="step" data-state="{state}">'
        f'<div class="step-ico">{icon}</div>'
        '<div class="step-body">'
        '<div class="step-top">'
        f'<div class="step-name">{index}. {escape(name)}</div>'
        f'<span class="badge">{badge}</span></div>'
        f'<div class="step-fn">{escape(fn)}</div>'
        f'<div class="step-msg">{escape(message)}</div>'
        "</div></div>"
    )


def verdict_html(result, account, category, amount):
    if isinstance(result, Left):
        return (
            '<div class="verdict fail"><div class="v-badge">Left</div><div>'
            '<div class="v-title">Transaction rejected</div>'
            '<div class="v-sub">The first failing step stopped the chain</div>'
            "</div></div>"
        )
    sign = "+" if amount > 0 else "−"
    return (
        '<div class="verdict ok"><div class="v-badge">Right</div><div>'
        '<div class="v-title">Transaction is valid</div>'
        f'<div class="v-sub">{escape(account.name)} · {escape(category.name)} · '
        f"{sign}{money(abs(amount))}</div></div></div>"
    )


def render_category_explorer(cats, trans):
    all_roots = [c for c in cats if c.parent_id is None]
    roots = [c for c in all_roots if c.type == "expense"]

    st.markdown(
        section_head(
            "Category explorer",
            "Expenses summed recursively over the category tree.",
        ),
        unsafe_allow_html=True,
    )
    if not roots:
        st.info("No expense categories found.")
        return

    names = {c.id: c.name for c in cats}
    by_id = {c.id: c for c in cats}

    with st.container(border=True):
        root = st.selectbox(
            "Expense category",
            [c.id for c in roots],
            format_func=lambda x: names[x],
            key="core_root",
        )
        color = PALETTE[[c.id for c in all_roots].index(root) % len(PALETTE)]
        branch = flatten_categories(cats, root)
        own = {
            c.id: sum(-t.amount for t in trans if t.cat_id == c.id and t.amount < 0)
            for c in branch
        }
        total = sum_expenses_recursive(cats, trans, root)
        everything = -sum(t.amount for t in trans if t.amount < 0)
        share = total / everything if everything else 0
        biggest = max(branch, key=lambda c: own[c.id])

        cards = (
            kpi("Branch total", money(total), "recursive sum over the tree"),
            kpi("Share of all expenses", f"{share:.0%}", f"of {money(everything)}"),
            kpi("Categories in branch", str(len(branch)), "including the root"),
            kpi("Largest category", names[biggest.id], money(own[biggest.id])),
        )
        st.markdown(
            '<div class="kpi-grid">' + "".join(cards) + "</div>",
            unsafe_allow_html=True,
        )
        top = max(own.values(), default=0)
        base = depth_of(by_id, root)
        st.caption("Own expenses per category · bar length is relative to the largest")
        rows = (
            breakdown_row(c.name, depth_of(by_id, c.id) - base, own[c.id], top, color)
            for c in branch
        )
        st.markdown("".join(rows), unsafe_allow_html=True)


def render_validation_pipeline():
    accounts, cats, trans, budgets = get_data()

    st.write("")
    st.markdown(
        section_head(
            "Transaction validation pipeline",
            "Every step returns Right(transaction) or Left(error); "
            "bind stops the chain at the first Left.",
        ),
        unsafe_allow_html=True,
    )
    if not accounts:
        st.info("No accounts available.")
        return

    st.session_state.setdefault("val_account", accounts[0])
    st.session_state.setdefault("val_category", demo_category(cats, "expense"))
    st.session_state.setdefault("val_amount", -1000)

    st.markdown('<div class="sc-label">Quick scenarios</div>', unsafe_allow_html=True)
    for col, (label, key) in zip(st.columns(len(PRESETS)), PRESETS, strict=True):
        col.button(
            label,
            key=f"preset_{key}",
            on_click=apply_preset,
            args=(key,),
            use_container_width=True,
        )

    left, right = st.columns([1, 1.3], gap="large")

    with left, st.container(border=True):
        st.markdown(
            card_head("1", "Transaction", "Fill in the fields or pick a scenario"),
            unsafe_allow_html=True,
        )
        account = st.selectbox(
            "Account",
            accounts + (UNKNOWN_ACCOUNT,),
            format_func=lambda a: a.name,
            key="val_account",
        )
        category = st.selectbox(
            "Category",
            cats + (UNKNOWN_CATEGORY,),
            format_func=lambda c: c.name,
            key="val_category",
        )
        if category.id == UNKNOWN_CATEGORY.id:
            hint = chip("unknown", RED) + "This category does not exist"
        elif category.type == "expense":
            hint = chip("expense", RED) + "Use a negative amount, e.g. −1000"
        else:
            hint = chip("income", GREEN) + "Use a positive amount, e.g. +200000"
        st.markdown(f'<div class="hint">{hint}</div>', unsafe_allow_html=True)

        amount = st.number_input(
            "Amount (− expense, + income)", step=500, key="val_amount"
        )
        latest = max(
            (t.ts for t in trans),
            default=datetime.now().astimezone().date().isoformat(),
        )
        day = st.date_input("Date", value=date.fromisoformat(latest), key="val_date")

    t = Transaction(
        id=f"tx_{uuid4().hex[:8]}",
        account_id=account.id,
        cat_id=category.id,
        amount=int(amount),
        ts=day.isoformat(),
        note="",
    )

    pipeline = (
        (
            "Account exists",
            "check_account(t, accounts)",
            lambda x: check_account(x, accounts),
        ),
        (
            "Category exists and matches the sign",
            "check_category(t, cats) · safe_category → Some / Nothing",
            lambda x: check_category(x, cats),
        ),
        (
            "Budget is not exceeded",
            "check_budget(b, trans) · budget lookup → Some / Nothing",
            budget_step(cats, trans, budgets),
        ),
    )
    ok_text = (
        f"{account.name} found",
        f"{category.name} is an {category.type} category and the sign matches",
        budget_note(t, cats, trans, budgets),
    )

    result = Right(t)
    cards = []
    for i, (name, fn, step) in enumerate(pipeline, start=1):
        if isinstance(result, Left):
            cards.append(
                step_html(i, name, fn, "skip", "Not run: an earlier step returned Left")
            )
            continue
        result = result.bind(step)
        if isinstance(result, Left):
            cards.append(step_html(i, name, fn, "fail", error_text(result.error)))
        else:
            cards.append(step_html(i, name, fn, "ok", ok_text[i - 1]))

    with right, st.container(border=True):
        st.markdown(
            card_head("2", "Pipeline", "Checks run top to bottom"),
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="steps">' + "".join(cards) + "</div>", unsafe_allow_html=True
        )
        st.markdown(
            verdict_html(result, account, category, t.amount), unsafe_allow_html=True
        )
        if isinstance(result, Right) and st.button(
            "Add to data", type="primary", key="val_add"
        ):
            st.session_state.data = (accounts, cats, add_transaction(trans, t), budgets)
            st.rerun()


def page_core():
    st.markdown(REPORTS_CSS + CORE_CSS, unsafe_allow_html=True)
    _, cats, trans, _ = get_data()

    st.title("Functional Core")
    st.caption("Pure functions, recursion and Maybe / Either containers in action.")

    render_category_explorer(cats, trans)
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
    st.info("Event-driven updates will appear here as the Async/FRP lab is integrated.")
    st.caption("Planned events: TRANSACTION_ADDED · BUDGET_ALERT · BALANCE_ALERT")


def page_tests():
    st.title("Tests")
    st.info("Run the project checks in your terminal to verify the current build.")
    st.code("pytest -q\nruff check .\nblack --check .", language="bash")


def page_about():
    st.title("About FinManager")
    st.write(
        "A financial management project built with Python and Streamlit."
    )

GREEN = "#367D58"
RED = "#D76560"
AMBER = "#F2B94B"
TRACK = "#E8EEE7"
 
REPORTS_CSS = """
<style>
.kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:18px; }
.kpi { background:#FFFFFF; border:1px solid #E2E9E0; border-radius:16px; padding:18px 20px; }
.kpi-label { font-size:12px; letter-spacing:.6px; text-transform:uppercase; color:#6F8074; }
.kpi-value { font-size:28px; font-weight:750; letter-spacing:-.6px; margin:6px 0 4px; color:#18362A; }
.kpi-sub { font-size:12px; }
.budget-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:14px; }
.b-card { background:#FBFCF8; border:1px solid #E2E9E0; border-radius:14px; padding:14px 16px; }
.b-name { font-weight:650; display:flex; align-items:center; gap:8px; }
.dot { width:9px; height:9px; border-radius:50%; display:inline-block; }
.b-sub { font-size:12px; color:#6F8074; margin-top:6px; }
.b-track { height:8px; border-radius:99px; background:#E8EEE7; margin:10px 0 6px; overflow:hidden; }
.b-fill { height:100%; border-radius:99px; }
.b-pct { font-size:22px; font-weight:750; }
.note-pill { margin-top:14px; background:#EDF4EA; border:1px solid #D7E5D4; border-radius:999px; padding:9px 16px; font-size:12px; color:#45664F; text-align:center; }
@media (max-width: 900px) { .kpi-grid { grid-template-columns:repeat(2,1fr); } }
</style>
"""
 
 
def month_label(m):
    """'2026-09' -> 'Sep 2026'"""
    return datetime.strptime(m, "%Y-%m").strftime("%b %Y")
 
 
def next_month(m):
    year, month = map(int, m.split("-"))
    year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return f"{year}-{month:02d}"
 
 
def status_color(ratio):
    """Зелёный до 80% лимита, жёлтый 80-100%, красный от 100%."""
    return RED if ratio >= 1 else AMBER if ratio >= 0.8 else GREEN
 
 
def in_period(ts, period, latest):
    """Попадает ли дата в текущий период бюджета (месяц или последние 7 дней)."""
    if period == "week":
        return 0 <= (date.fromisoformat(latest) - date.fromisoformat(ts)).days < 7
    return ts[:7] == latest[:7]
 
 
def budget_spent(b, cats, trans, latest):
    """Расходы по категории бюджета И всем её подкатегориям за текущий период."""
    ids = {c.id for c in flatten_categories(cats, b.cat_id)}
    return -sum(
        t.amount
        for t in trans
        if t.cat_id in ids and t.amount < 0 and in_period(t.ts, b.period, latest)
    )
 
 
def kpi(label, value, sub, sub_color="#6F8074"):
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
        sub, sub_color = "first month in the data", "#6F8074"
 
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
 
    with left:
        with st.container(border=True):
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
                        scale=alt.Scale(
                            domain=["Income", "Expenses"], range=[GREEN, RED]
                        ),
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
            st.altair_chart(polish_chart(alt.layer(bars, fc_bar).properties(height=320)), width="stretch")
 
    with right:
        with st.container(border=True):
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
                .mark_text(size=34, fontWeight="bold", color="#203D30")
                .encode(text="t:N")
            )
            st.altair_chart(polish_chart((ring + center).properties(height=250)), width="stretch")
            st.caption(
                f"{money(total_spent)} of {money(total_limit)} budgeted this period"
            )
 
    left, right = st.columns([1, 1.25], gap="large")
 
    with left:
        with st.container(border=True):
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
                    run_forecasts, forecast_expenses, expense_ids, trans, period, repeats
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
                st.caption(
                    f"lru_cache: {bench['hits']} hits, {bench['misses']} misses"
                )
 
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
                    checked = check_budget(b, budget_view(b, cats, trans))
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
