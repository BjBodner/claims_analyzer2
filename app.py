import streamlit as st
import os
from epo_client import get_family_members, get_claims
from file_manager import write_claims_file, list_claims_files

st.set_page_config(
    page_title="Patent Claims Analyzer | Mission Control",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Design System (Glassmorphism & Dark Mode)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap');

    :root {
        --primary: #00D4FF;
        --secondary: #0056B3;
        --bg-dark: #0A0E14;
        --card-bg: rgba(255, 255, 255, 0.05);
        --glass-border: rgba(255, 255, 255, 0.1);
    }

    .stApp {
        background-color: var(--bg-dark);
        color: #E0E0E0;
        font-family: 'Outfit', sans-serif;
    }

    /* Glassmorphism Cards */
    div.stButton > button {
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        color: white !important;
        border-radius: 12px;
        border: none;
        padding: 0.6rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
    }

    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 212, 255, 0.5);
    }

    .stTextInput > div > div > input {
        background: var(--card-bg) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 10px !important;
        color: white !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: transparent;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        color: #888;
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        color: var(--primary) !important;
        border-bottom-color: var(--primary) !important;
    }
    
    /* Title and Dividers */
    h1 {
        color: var(--primary);
        font-weight: 600;
        letter-spacing: -1px;
    }
    
    hr {
        border-color: var(--glass-border);
    }
</style>
""", unsafe_allow_html=True)

st.title("🛸 Patent Claims Analyzer")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🔍 Fetch & Download", "📊 Compare", "🤖 AI Analysis"])

with tab1:
    st.subheader("📡 System Initialization")
    st.info("Awaiting mission parameters. Please enter a PCT or Publication number to scan.")

with tab2:
    st.info("📊 Data required. Scan and download family members in the Fetch tab first.")

with tab3:
    st.info("🤖 AI Core offline. Complete data archival and comparison to initialize analysis.")
