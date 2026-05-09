# Patent Claims Analyzer Implementation Plan

> **For Antigravity:** REQUIRED WORKFLOW: Use `.agent/workflows/execute-plan.md` to execute this plan in single-flow mode.

**Goal:** Build a 4-phase Streamlit app for EPO patent claims fetching, comparison, and AI analysis.

**Architecture:** Modular — `epo_client.py`, `file_manager.py`, `diff_engine.py`, `gemini_client.py`, `app.py`

**Tech Stack:** Python 3.11, Streamlit, EPO OPS REST API, Google Gemini API, difflib

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `claims/.gitkeep`

**Step 1:** Create `requirements.txt`:
```
streamlit>=1.32
requests>=2.31
python-dotenv>=1.0
google-generativeai>=0.5
```

**Step 2:** Create `.env.example`:
```
EPO_CLIENT_ID=your_epo_client_id
EPO_CLIENT_SECRET=your_epo_client_secret
GEMINI_API_KEY=your_gemini_api_key
```

**Step 3:** Create `.gitignore`:
```
.env
claims/
__pycache__/
*.pyc
.streamlit/
```

**Step 4:** Init git and commit:
```bash
git init
git add .
git commit -m "chore: project scaffold"
```

---

## Task 2: EPO Client

**Files:**
- Create: `epo_client.py`
- Create: `tests/test_epo_client.py`

**Step 1:** Create `epo_client.py`:

```python
import os, requests
from dotenv import load_dotenv

load_dotenv()

EPO_BASE = "https://ops.epo.org/3.2/rest-services"
_token_cache = {"token": None}

def get_access_token():
    resp = requests.post(
        "https://ops.epo.org/3.2/auth/accesstoken",
        data={"grant_type": "client_credentials"},
        auth=(os.getenv("EPO_CLIENT_ID"), os.getenv("EPO_CLIENT_SECRET")),
    )
    resp.raise_for_status()
    _token_cache["token"] = resp.json()["access_token"]
    return _token_cache["token"]

def _headers():
    return {"Authorization": f"Bearer {get_access_token()}", "Accept": "application/json"}

def get_family_members(pct_code: str) -> list[dict]:
    """Returns list of {doc_id, country, kind, title}"""
    # Normalize: WO2020227475A1 -> WO.2020227475.A1
    parts = pct_code.strip().upper()
    url = f"{EPO_BASE}/published-data/publication/epodoc/{parts}/family"
    resp = requests.get(url, headers=_headers())
    resp.raise_for_status()
    data = resp.json()
    members = []
    family_members = (
        data.get("ops:world-patent-data", {})
        .get("ops:patent-family", {})
        .get("ops:family-member", [])
    )
    if isinstance(family_members, dict):
        family_members = [family_members]
    for m in family_members:
        pub_refs = m.get("publication-reference", [])
        if isinstance(pub_refs, dict):
            pub_refs = [pub_refs]
        for ref in pub_refs:
            doc_id = ref.get("document-id", {})
            country = doc_id.get("country", {}).get("$", "")
            number = doc_id.get("doc-number", {}).get("$", "")
            kind = doc_id.get("kind", {}).get("$", "")
            members.append({
                "doc_id": f"{country}{number}{kind}",
                "country": country,
                "number": number,
                "kind": kind,
            })
    return members

def get_claims(doc_id: str, lang: str = "EN") -> str:
    """Fetch claims text for a patent document. Returns plain text."""
    url = f"{EPO_BASE}/published-data/publication/epodoc/{doc_id}/claims"
    resp = requests.get(url, headers={**_headers(), "Accept": "application/xml"})
    if resp.status_code == 404:
        return ""
    resp.raise_for_status()
    # Parse XML to extract claim text
    import xml.etree.ElementTree as ET
    root = ET.fromstring(resp.content)
    ns = {"ops": "http://ops.epo.org/3.2"}
    claims_text = []
    for claim in root.iter():
        if claim.text and claim.text.strip():
            claims_text.append(claim.text.strip())
    return "\n\n".join(claims_text)
```

**Step 2:** Create `tests/test_epo_client.py`:
```python
import pytest
from epo_client import get_access_token, get_family_members, get_claims

def test_get_access_token():
    token = get_access_token()
    assert token and len(token) > 10

def test_get_family_members():
    members = get_family_members("WO2020227475A1")
    assert len(members) > 0
    assert all("doc_id" in m for m in members)

def test_get_claims_for_wo():
    members = get_family_members("WO2020227475A1")
    claims = get_claims(members[0]["doc_id"])
    assert isinstance(claims, str)
```

**Step 3:** Run tests:
```bash
pytest tests/test_epo_client.py -v
```

**Step 4:** Commit:
```bash
git add epo_client.py tests/test_epo_client.py
git commit -m "feat: EPO OPS API client with family and claims fetching"
```

---

## Task 3: File Manager

**Files:**
- Create: `file_manager.py`
- Create: `tests/test_file_manager.py`

**Step 1:** Create `file_manager.py`:

```python
import os, re

CLAIMS_DIR = os.path.join(os.path.dirname(__file__), "claims")

def _sanitize(name: str) -> str:
    return re.sub(r"[^\w\-.]", "_", name)

def ensure_directory(pct_code: str) -> str:
    path = os.path.join(CLAIMS_DIR, _sanitize(pct_code))
    os.makedirs(path, exist_ok=True)
    return path

def write_claims_file(pct_code: str, filename: str, content: str) -> str:
    directory = ensure_directory(pct_code)
    if not filename.endswith(".md"):
        filename += ".md"
    filepath = os.path.join(directory, _sanitize(filename))
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath

def list_claims_files(pct_code: str) -> list[str]:
    directory = ensure_directory(pct_code)
    return sorted([
        f for f in os.listdir(directory) if f.endswith(".md")
    ])

def read_claims_file(pct_code: str, filename: str) -> str:
    directory = ensure_directory(pct_code)
    filepath = os.path.join(directory, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()
```

**Step 2:** Create `tests/test_file_manager.py`:
```python
import os, pytest
from file_manager import ensure_directory, write_claims_file, list_claims_files, read_claims_file

TEST_PCT = "WO_TEST_123"

def test_ensure_directory():
    path = ensure_directory(TEST_PCT)
    assert os.path.isdir(path)

def test_write_and_read():
    content = "# Claim 1\nA widget comprising..."
    filepath = write_claims_file(TEST_PCT, "US1234A1", content)
    assert os.path.exists(filepath)
    result = read_claims_file(TEST_PCT, "US1234A1.md")
    assert result == content

def test_list_files():
    files = list_claims_files(TEST_PCT)
    assert "US1234A1.md" in files
```

**Step 3:** Run tests:
```bash
pytest tests/test_file_manager.py -v
```

**Step 4:** Commit:
```bash
git add file_manager.py tests/test_file_manager.py
git commit -m "feat: file manager for claims directory"
```

---

## Task 4: Phase 1 CLI Validation Script

**Files:**
- Create: `test_phase1.py`

**Step 1:** Create `test_phase1.py`:
```python
"""CLI script to validate full Phase 1 pipeline with WO2020227475A1"""
from epo_client import get_family_members, get_claims
from file_manager import write_claims_file, list_claims_files

PCT = "WO2020227475A1"

print(f"Fetching family members for {PCT}...")
members = get_family_members(PCT)
print(f"Found {len(members)} family members:")
for m in members:
    print(f"  - {m['doc_id']} ({m['country']})")

print("\nDownloading claims...")
for m in members:
    doc_id = m["doc_id"]
    claims = get_claims(doc_id)
    if claims:
        content = f"# Claims: {doc_id}\n\n{claims}"
        path = write_claims_file(PCT, doc_id, content)
        print(f"  ✓ Saved: {path}")
    else:
        print(f"  ✗ No claims found for {doc_id}")

print(f"\nFiles in claims/{PCT}/:")
for f in list_claims_files(PCT):
    print(f"  - {f}")
print("Phase 1 complete!")
```

**Step 2:** Run validation:
```bash
python test_phase1.py
```
Expected: prints family members, downloads claims, lists `.md` files.

**Step 3:** Commit:
```bash
git add test_phase1.py
git commit -m "test: phase 1 CLI validation script"
```

---

## Task 5: Streamlit UI — Fetch & Download (Phase 2)

**Files:**
- Create: `app.py`

**Step 1:** Create `app.py` with full Streamlit UI.

Key layout:
- `st.tabs(["🔍 Fetch & Download", "📊 Compare", "🤖 AI Analysis"])`
- Tab 1: PCT input, search button, family table with checkboxes, "Download Selected" + "Select All", custom MD upload form
- Tab 2-3: placeholders for Phase 3 and 4
- CSS: clean white, Inter font, blue accent `#1B6CA8`

```python
import streamlit as st
from epo_client import get_family_members, get_claims
from file_manager import write_claims_file, list_claims_files, ensure_directory
import os

st.set_page_config(page_title="Patent Claims Analyzer", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stButton > button { background: #1B6CA8; color: white; border-radius: 8px; border: none; padding: 0.5rem 1.5rem; }
.stButton > button:hover { background: #154f80; }
</style>
""", unsafe_allow_html=True)

st.title("📜 Patent Claims Analyzer")
tab1, tab2, tab3 = st.tabs(["🔍 Fetch & Download", "📊 Compare", "🤖 AI Analysis"])

with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        pct_input = st.text_input("PCT Code", placeholder="e.g. WO2020227475A1", key="pct_input")
    with col2:
        st.write("")
        search = st.button("🔍 Search", key="search_btn")

    if search and pct_input:
        with st.spinner("Fetching family members from EPO..."):
            try:
                members = get_family_members(pct_input.strip())
                st.session_state["members"] = members
                st.session_state["pct_code"] = pct_input.strip()
                st.success(f"Found {len(members)} family members")
            except Exception as e:
                st.error(f"Error: {e}")

    if "members" in st.session_state:
        members = st.session_state["members"]
        pct_code = st.session_state["pct_code"]

        select_all = st.checkbox("Select All", key="select_all")
        selected = []
        for m in members:
            checked = st.checkbox(
                f"**{m['doc_id']}** — {m['country']}",
                value=select_all,
                key=f"chk_{m['doc_id']}"
            )
            if checked:
                selected.append(m)

        if st.button("⬇️ Download Selected", key="download_btn") and selected:
            progress = st.progress(0)
            for i, m in enumerate(selected):
                claims = get_claims(m["doc_id"])
                content = f"# Claims: {m['doc_id']}\n\n{claims or '_No claims available_'}"
                write_claims_file(pct_code, m["doc_id"], content)
                progress.progress((i + 1) / len(selected))
            st.success(f"Downloaded {len(selected)} files to claims/{pct_code}/")

        st.divider()
        st.subheader("➕ Add Custom MD File")
        custom_name = st.text_input("File name", placeholder="MyCustomClaims")
        custom_text = st.text_area("Claims text (Markdown)", height=200)
        if st.button("💾 Save Custom File", key="save_custom"):
            if custom_name and custom_text:
                write_claims_file(pct_code, custom_name, custom_text)
                st.success(f"Saved {custom_name}.md")

with tab2:
    st.info("Complete Phase 2 first to enable comparison.")

with tab3:
    st.info("Complete Phase 3 first to enable AI analysis.")
```

**Step 2:** Run app:
```bash
streamlit run app.py
```

**Step 3:** Test manually: enter `WO2020227475A1`, search, select all, download.

**Step 4:** Commit:
```bash
git add app.py
git commit -m "feat: Streamlit UI phase 2 - fetch and download"
```

---

## Task 6: Diff Engine (Phase 3)

**Files:**
- Create: `diff_engine.py`
- Create: `tests/test_diff_engine.py`

**Step 1:** Create `diff_engine.py`:

```python
import difflib
from typing import Optional

def compute_diff(text_a: str, text_b: str) -> list[dict]:
    """Returns list of {type: 'add'|'remove'|'equal', lines: [...]}"""
    lines_a = text_a.splitlines(keepends=True)
    lines_b = text_b.splitlines(keepends=True)
    matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
    result = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            result.append({"type": "equal", "a_lines": lines_a[i1:i2], "b_lines": lines_b[j1:j2]})
        elif tag == "replace":
            result.append({"type": "remove", "a_lines": lines_a[i1:i2], "b_lines": []})
            result.append({"type": "add", "a_lines": [], "b_lines": lines_b[j1:j2]})
        elif tag == "delete":
            result.append({"type": "remove", "a_lines": lines_a[i1:i2], "b_lines": []})
        elif tag == "insert":
            result.append({"type": "add", "a_lines": [], "b_lines": lines_b[j1:j2]})
    return result

def render_diff_html(diff: list[dict], mode: str = "split") -> str:
    """Render diff as HTML. mode: 'split' or 'unified'"""
    colors = {"add": "#e6ffed", "remove": "#ffeef0", "equal": "#ffffff"}
    border = {"add": "#34d058", "remove": "#d73a49", "equal": "#e1e4e8"}
    
    if mode == "unified":
        rows = []
        for block in diff:
            for line in block["a_lines"]:
                rows.append(f'<tr style="background:{colors["remove"]}"><td style="color:#d73a49;padding:2px 8px;font-family:monospace;border-left:3px solid {border["remove"]}">- {line.rstrip()}</td></tr>')
            for line in block["b_lines"]:
                rows.append(f'<tr style="background:{colors["add"]}"><td style="color:#22863a;padding:2px 8px;font-family:monospace;border-left:3px solid {border["add"]}">+ {line.rstrip()}</td></tr>')
            if block["type"] == "equal":
                for line in block["a_lines"][:3]:
                    rows.append(f'<tr style="background:{colors["equal"]}"><td style="padding:2px 8px;font-family:monospace;color:#666">  {line.rstrip()}</td></tr>')
        return f'<table style="width:100%;border-collapse:collapse;font-size:13px">{"".join(rows)}</table>'
    else:
        # Split view
        left_rows, right_rows = [], []
        for block in diff:
            t = block["type"]
            a_lines = block.get("a_lines", [])
            b_lines = block.get("b_lines", [])
            max_len = max(len(a_lines), len(b_lines), 1)
            for i in range(max_len):
                la = a_lines[i].rstrip() if i < len(a_lines) else ""
                lb = b_lines[i].rstrip() if i < len(b_lines) else ""
                bg_l = colors["remove"] if t == "remove" else (colors["equal"] if t == "equal" else "#fff")
                bg_r = colors["add"] if t == "add" else (colors["equal"] if t == "equal" else "#fff")
                left_rows.append(f'<tr style="background:{bg_l}"><td style="padding:2px 8px;font-family:monospace;font-size:13px">{la}</td></tr>')
                right_rows.append(f'<tr style="background:{bg_r}"><td style="padding:2px 8px;font-family:monospace;font-size:13px">{lb}</td></tr>')
        left = f'<table style="width:100%;border-collapse:collapse">{"".join(left_rows)}</table>'
        right = f'<table style="width:100%;border-collapse:collapse">{"".join(right_rows)}</table>'
        return left, right
```

**Step 2:** Create `tests/test_diff_engine.py`:
```python
from diff_engine import compute_diff, render_diff_html

def test_compute_diff_detects_changes():
    a = "Claim 1\nA widget\nwith a part"
    b = "Claim 1\nA widget\nwith two parts"
    diff = compute_diff(a, b)
    types = [d["type"] for d in diff]
    assert "add" in types or "remove" in types

def test_render_unified():
    diff = [{"type": "add", "a_lines": [], "b_lines": ["new line\n"]}]
    html = render_diff_html(diff, mode="unified")
    assert "new line" in html
```

**Step 3:** Run tests:
```bash
pytest tests/test_diff_engine.py -v
```

**Step 4:** Update `app.py` Tab 2 to use diff engine — add file selectors and diff display.

**Step 5:** Commit:
```bash
git add diff_engine.py tests/test_diff_engine.py app.py
git commit -m "feat: diff engine and compare tab (phase 3)"
```

---

## Task 7: Gemini AI Client (Phase 4)

**Files:**
- Create: `gemini_client.py`

**Step 1:** Create `gemini_client.py`:

```python
import os, google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash-exp")

def translate_claims(claims_text: str, target_lang: str = "English") -> str:
    prompt = f"""Translate the following patent claims to {target_lang}. 
Keep the claim numbering and structure intact. Output only the translated claims.

Claims:
{claims_text}"""
    response = model.generate_content(prompt)
    return response.text

def analyze_diff(text_a: str, text_b: str, label_a: str = "Version A", label_b: str = "Version B") -> dict:
    prompt = f"""You are a patent attorney. Analyze the differences between these two patent claim versions.

{label_a}:
{text_a}

{label_b}:
{text_b}

Provide a JSON response with:
- "summary": brief summary of what changed (2-3 sentences)
- "motivation": likely legal/strategic motivation behind the changes
- "scope_change": "narrowed", "broadened", or "neutral"
- "risk_assessment": any risks or implications of the changes

Respond ONLY with valid JSON."""
    response = model.generate_content(prompt)
    import json
    try:
        return json.loads(response.text.strip().strip("```json").strip("```"))
    except:
        return {"summary": response.text, "motivation": "", "scope_change": "unknown", "risk_assessment": ""}
```

**Step 2:** Update `app.py` Tab 3 to add:
- "Analyze with AI" button (sends selected diff to Gemini)
- "Translate to English" button on any non-EN file
- Display AI response in cards

**Step 3:** Commit:
```bash
git add gemini_client.py app.py
git commit -m "feat: Gemini AI client for translation and diff analysis (phase 4)"
```

---

## Task 8: Final Integration & Polish

**Step 1:** After download completes in Tab 1, auto-switch to Tab 2 using `st.session_state`

**Step 2:** Add multi-version comparison (N-way) in Tab 2 — sequential diffs rendered as a timeline

**Step 3:** Add file listing sidebar showing current PCT directory contents

**Step 4:** Final run and smoke test with `WO2020227475A1`

**Step 5:** Final commit:
```bash
git add -A
git commit -m "feat: complete patent claims analyzer v1.0"
```
