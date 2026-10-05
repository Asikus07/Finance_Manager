import streamlit as st 

st.set_page_config(page_title="Финансовый Менеджер", page_icon="💰", layout="wide")

MENU = ["Overview", "Data", "Functional Core", "Pipelines",
        "Async/FRP", "Reports", "Tests", "About"]

def page_overview():
    st.title("Overview")

def page_data():
    st.title("Data")

def page_core():
    st.title("Functional Core")

def page_pipelines():
    st.title("Pipelines")

def page_async():
    st.title("Async/FRP")

def page_reports():
    st.title("Reports")

def page_tests():
    st.title("Tests")

def page_about():
    st.title("About")

PAGES = {
    "Overview": page_overview,
    "Datat": page_data,
    "Functional Core": page_core,
    "Pipelines": page_pipelines,
    "Asunc/FRP": page_async, 
    "Reports": page_reports,
    "Tests": page_tests,
    "About": page_about,
}

with st.sidebar:
    st.title("Finance Manager ASML")
    choice = st.radio("Меню", MENU, label_visibility="collapsed")






