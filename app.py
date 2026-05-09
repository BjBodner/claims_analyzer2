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
        text-shadow: 0 0 20px rgba(0, 212, 255, 0.4);
    }
    
    hr {
        border-color: var(--glass-border);
    }

    /* Fade-in Animation */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .stApp {
        animation: fadeIn 0.8s ease-out;
    }

    /* Custom Info Box */
    .stAlert {
        background: var(--card-bg) !important;
        border: 1px solid var(--glass-border) !important;
        color: #E0E0E0 !important;
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛸 Patent Claims Analyzer")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🔍 Fetch & Download", "📊 Compare", "🤖 AI Analysis"])

with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        pct_input = st.text_input("Enter PCT / Publication Number", placeholder="e.g. WO2020227475A1")
    with col2:
        st.write("##")
        search_btn = st.button("🚀 SCAN FAMILY")

    if search_btn and pct_input:
        with st.status("📡 Connecting to EPO OPS API...", expanded=True) as status:
            try:
                members = get_family_members(pct_input.strip())
                st.session_state["members"] = members
                st.session_state["pct_code"] = pct_input.strip()
                status.update(label=f"✅ Scan Complete: {len(members)} members identified.", state="complete")
            except Exception as e:
                st.error(f"⚠️ Scan Interrupted: {str(e)}")

    if "members" in st.session_state:
        members = st.session_state["members"]
        pct_code = st.session_state["pct_code"]
        
        st.markdown(f"### 📋 Family Members for `{pct_code}`")
        
        # Selection logic
        col_sel, col_act = st.columns([1, 1])
        with col_sel:
            select_all = st.checkbox("Select All Members", value=True)
        
        selected_ids = []
        for m in members:
            is_selected = st.checkbox(
                f"**{m['doc_id']}** ({m['country']})", 
                value=select_all, 
                key=f"sel_{m['doc_id']}"
            )
            if is_selected:
                selected_ids.append(m['doc_id'])
                
        if st.button("⏬ DOWNLOAD SELECTED CLAIMS"):
            if not selected_ids:
                st.warning("No members selected for download.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, doc_id in enumerate(selected_ids):
                    status_text.text(f"Downloading {doc_id}...")
                    claims = get_claims(doc_id)
                    content = f"# Claims: {doc_id}\n\n{claims if claims else '_[NO CLAIMS FOUND]_'}"
                    write_claims_file(pct_code, doc_id, content)
                    progress_bar.progress((i + 1) / len(selected_ids))
                
                status_text.text("✨ Download Sequence Complete!")
                st.success(f"Successfully archived {len(selected_ids)} documents to `claims/{pct_code}/`")

        st.markdown("---")
        st.subheader("➕ Manual Data Injection")
        with st.expander("Manually add claims document"):
            custom_name = st.text_input("Filename (e.g., MyCustomDraft)", key="custom_name")
            custom_text = st.text_area("Claims Content (Markdown/Text)", height=300, key="custom_text")
            if st.button("💾 SAVE TO ARCHIVE"):
                if custom_name and custom_text:
                    write_claims_file(pct_code, custom_name, custom_text)
                    st.success(f"Archived `{custom_name}.md` successfully.")
                else:
                    st.error("Both filename and content are required.")

with tab2:
    st.info("📊 Data required. Scan and download family members in the Fetch tab first.")

with tab3:
    st.info("🤖 AI Core offline. Complete data archival and comparison to initialize analysis.")
