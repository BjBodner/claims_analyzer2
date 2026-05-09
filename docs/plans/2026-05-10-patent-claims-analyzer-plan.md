# Patent Claims Analyzer — Implementation Plan

> **For Antigravity:** REQUIRED WORKFLOW: Use `.agent/workflows/execute-plan.md` to execute this plan in single-flow mode.

**Goal:** Build a Streamlit app that fetches PCT patent family claims via EPO OPS API, displays diffs between versions, and provides Gemini AI analysis.

**Architecture:** Modular Python — `epo_client.py`, `file_manager.py`, `diff_engine.py`, `gemini_client.py`, orchestrated by `app.py`.

**Tech Stack:** Python 3.11+, Streamlit ≥1.32, EPO OPS REST API, Google Gemini (`gemini-2.0-flash-exp`), `difflib`, `python-dotenv`, `requests`

---

## Phase 1 — API Infrastructure & CLI Validation

**Goal:** Prove EPO OPS integration works end-to-end. No UI. Test with `WO2020227475A1`.

---

### Task 1.1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `claims/.gitkeep`

**Step 1: Create `requirements.txt`**

```
streamlit>=1.32
requests>=2.31
python-dotenv>=1.0
google-generativeai>=0.5
pytest>=8.0
```

**Step 2: Create `.env.example`**

```
EPO_CLIENT_ID=your_epo_client_id
EPO_CLIENT_SECRET=your_epo_client_secret
GEMINI_API_KEY=your_gemini_api_key
```

**Step 3: Install deps**

```bash
pip install -r requirements.txt
```

**Step 4: Commit**

```bash
git add requirements.txt .env.example claims/.gitkeep
git commit -m "chore: project scaffold"
```

---

### Task 1.2: EPO Client — Auth

**Files:**
- Create: `epo_client.py`
- Create: `tests/test_epo_client.py`

**Step 1: Write failing test**

```python
# tests/test_epo_client.py
from epo_client import get_access_token

def test_get_access_token_returns_string():
    token = get_access_token()
    assert isinstance(token, str)
    assert len(token) > 10
```

**Step 2: Run to verify it fails**

```bash
pytest tests/test_epo_client.py::test_get_access_token_returns_string -v
```

**Step 3: Implement `get_access_token()`**

```python
# epo_client.py
import os, requests
from dotenv import load_dotenv

load_dotenv()

EPO_AUTH_URL = "https://ops.epo.org/3.2/auth/accesstoken"
EPO_BASE_URL = "https://ops.epo.org/3.2/rest-services"

def get_access_token() -> str:
    resp = requests.post(
        EPO_AUTH_URL,
        data={"grant_type": "client_credentials"},
        auth=(os.getenv("EPO_CLIENT_ID"), os.getenv("EPO_CLIENT_SECRET")),
    )
    resp.raise_for_status()
    return resp.json()["access_token"]
```

**Step 4: Run test — expect PASS**

```bash
pytest tests/test_epo_client.py::test_get_access_token_returns_string -v
```

**Step 5: Commit**

```bash
git add epo_client.py tests/test_epo_client.py
git commit -m "feat: EPO OAuth2 token retrieval"
```

---

### Task 1.3: EPO Client — Family Members

**Files:**
- Modify: `epo_client.py`
- Modify: `tests/test_epo_client.py`

**Step 1: Write failing test**

```python
def test_get_family_members_returns_list():
    members = get_family_members("WO2020227475A1")
    assert isinstance(members, list)
    assert len(members) > 0
    assert "doc_id" in members[0]
    assert "country" in members[0]
```

**Step 2: Implement `get_family_members()`**

```python
def get_family_members(pct_code: str) -> list[dict]:
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    epodoc = pct_code.replace("/", "")
    url = f"{EPO_BASE_URL}/published-data/publication/epodoc/{epodoc}/family"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    family_members = (
        data.get("ops:world-patent-data", {})
            .get("ops:patent-family", {})
            .get("ops:family-member", [])
    )
    if isinstance(family_members, dict):
        family_members = [family_members]
    members = []
    for m in family_members:
        pub_ref = m.get("publication-reference", {})
        doc_id_node = pub_ref.get("document-id", {})
        if isinstance(doc_id_node, list):
            doc_id_node = doc_id_node[0]
        country = doc_id_node.get("country", {}).get("$", "")
        doc_num = doc_id_node.get("doc-number", {}).get("$", "")
        kind = doc_id_node.get("kind", {}).get("$", "")
        members.append({
            "doc_id": f"{country}{doc_num}{kind}",
            "country": country,
            "doc_number": doc_num,
            "kind": kind,
        })
    return members
```

**Step 3: Run all tests — expect PASS**

```bash
pytest tests/test_epo_client.py -v
```

**Step 4: Commit**

```bash
git add epo_client.py tests/test_epo_client.py
git commit -m "feat: fetch patent family members"
```

---

### Task 1.4: EPO Client — Claims Download

**Files:**
- Modify: `epo_client.py`
- Modify: `tests/test_epo_client.py`

**Step 1: Write failing test**

```python
import pytest

def test_get_claims_returns_text():
    members = get_family_members("WO2020227475A1")
    us_members = [m for m in members if m["country"] == "US"]
    if not us_members:
        pytest.skip("No US members found")
    claims = get_claims(us_members[0]["doc_id"])
    assert isinstance(claims, str)
    assert len(claims) > 50
```

**Step 2: Implement `get_claims()`**

```python
def get_claims(doc_id: str, lang: str = "EN") -> str:
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    url = f"{EPO_BASE_URL}/published-data/publication/epodoc/{doc_id}/claims"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    claims_node = (
        data.get("ops:world-patent-data", {})
            .get("ftxt:fulltext-documents", {})
            .get("ftxt:fulltext-document", {})
            .get("claims", {})
    )
    if isinstance(claims_node, list):
        claims_node = claims_node[0]
    paragraphs = claims_node.get("claim", [])
    if isinstance(paragraphs, dict):
        paragraphs = [paragraphs]
    lines = []
    for i, p in enumerate(paragraphs, 1):
        text = p.get("claim-text", {})
        if isinstance(text, dict):
            text = text.get("$", "")
        lines.append(f"{i}. {text}")
    return "\n\n".join(lines)
```

**Step 3: Run tests — expect PASS**

```bash
pytest tests/test_epo_client.py -v
```

**Step 4: Commit**

```bash
git add epo_client.py tests/test_epo_client.py
git commit -m "feat: download patent claims text"
```

---

### Task 1.5: File Manager

**Files:**
- Create: `file_manager.py`
- Create: `tests/test_file_manager.py`

**Step 1: Write failing tests**

```python
# tests/test_file_manager.py
import os, pytest
from file_manager import ensure_directory, write_claims_file, list_claims_files, read_claims_file

PCT = "WO2020227475A1"

def test_ensure_directory_creates_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = ensure_directory(PCT)
    assert os.path.isdir(path)

def test_write_and_list_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ensure_directory(PCT)
    write_claims_file(PCT, "US1234567A1", "# Claims\n1. A widget.")
    files = list_claims_files(PCT)
    assert len(files) == 1
    assert files[0].endswith(".md")

def test_read_file_returns_content(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ensure_directory(PCT)
    write_claims_file(PCT, "US9999999A1", "# Test\n1. Claim.")
    files = list_claims_files(PCT)
    content = read_claims_file(files[0])
    assert "Claim." in content
```

**Step 2: Implement `file_manager.py`**

```python
# file_manager.py
import os

CLAIMS_DIR = "claims"

def ensure_directory(pct_code: str) -> str:
    path = os.path.join(CLAIMS_DIR, pct_code)
    os.makedirs(path, exist_ok=True)
    return path

def write_claims_file(pct_code: str, doc_id: str, content: str) -> str:
    directory = ensure_directory(pct_code)
    filepath = os.path.join(directory, f"{doc_id}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath

def list_claims_files(pct_code: str) -> list[str]:
    directory = os.path.join(CLAIMS_DIR, pct_code)
    if not os.path.isdir(directory):
        return []
    return [
        os.path.join(directory, f)
        for f in sorted(os.listdir(directory))
        if f.endswith(".md")
    ]

def read_claims_file(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()
```

**Step 3: Run tests — expect PASS**

```bash
pytest tests/test_file_manager.py -v
```

**Step 4: Commit**

```bash
git add file_manager.py tests/test_file_manager.py
git commit -m "feat: file manager for claims/ directory"
```

---

### Task 1.6: CLI Validation Script

**Files:**
- Create: `test_phase1.py`

**Step 1: Create script**

```python
# test_phase1.py
from epo_client import get_family_members, get_claims
from file_manager import ensure_directory, write_claims_file, list_claims_files

PCT = "WO2020227475A1"
print(f"\n=== Testing Phase 1 with {PCT} ===\n")

members = get_family_members(PCT)
print(f"Found {len(members)} family members:")
for m in members:
    print(f"  {m['country']} | {m['doc_id']}")

ensure_directory(PCT)
downloaded = 0
for m in members[:5]:
    try:
        claims = get_claims(m["doc_id"])
        content = f"# Claims — {m['doc_id']}\n\n{claims}"
        fp = write_claims_file(PCT, m["doc_id"], content)
        print(f"  ✓ Saved: {fp}")
        downloaded += 1
    except Exception as e:
        print(f"  ✗ {m['doc_id']}: {e}")

files = list_claims_files(PCT)
print(f"\nDownloaded {downloaded} files. MD files in claims/{PCT}/:")
for f in files:
    print(f"  {f}")
```

**Step 2: Run it**

```bash
python test_phase1.py
```

Expected output: list of family members, download confirmations, `.md` file paths.

**Step 3: Commit**

```bash
git add test_phase1.py
git commit -m "feat: phase 1 CLI validation script"
```

---

## Phase 2 — Streamlit UI (Fetch & Download)

**Goal:** Visual interface. Clean, minimal, modern. White bg, Inter font, accent `#1B6CA8`.

---

### Task 2.1: Diff Engine

**Files:**
- Create: `diff_engine.py`
- Create: `tests/test_diff_engine.py`

**Step 1: Write failing tests**

```python
# tests/test_diff_engine.py
from diff_engine import compute_diff, render_diff_html

def test_compute_diff_detects_changes():
    old = "1. A widget.\n2. A gadget."
    new = "1. A widget.\n2. An improved gadget."
    diff = compute_diff(old, new)
    assert any(line.startswith("-") for line in diff)
    assert any(line.startswith("+") for line in diff)

def test_render_diff_html_returns_html():
    diff = ["- old line", "+ new line", "  same line"]
    html = render_diff_html(diff)
    assert "<" in html and ">" in html
    assert "diff-added" in html
    assert "diff-removed" in html
```

**Step 2: Implement `diff_engine.py`**

```python
# diff_engine.py
import difflib

def compute_diff(old_text: str, new_text: str) -> list[str]:
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    return list(difflib.unified_diff(old_lines, new_lines, lineterm=""))

def render_diff_html(diff_lines: list[str]) -> str:
    rows = []
    for line in diff_lines:
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            cls, text = "diff-added", line[1:]
        elif line.startswith("-"):
            cls, text = "diff-removed", line[1:]
        elif line.startswith("@@"):
            cls, text = "diff-hunk", line
        else:
            cls, text = "diff-unchanged", line[1:] if line.startswith(" ") else line
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rows.append(f'<div class="diff-line {cls}">{escaped}</div>')
    return f"""<style>
  .diff-line {{ font-family: monospace; padding: 2px 8px; white-space: pre-wrap; line-height: 1.5; }}
  .diff-added {{ background: #e6ffed; color: #24292e; }}
  .diff-removed {{ background: #ffeef0; color: #24292e; }}
  .diff-hunk {{ background: #f1f8ff; color: #586069; }}
  .diff-unchanged {{ background: #fff; color: #24292e; }}
</style>{"".join(rows)}"""
```

**Step 3: Run tests**

```bash
pytest tests/test_diff_engine.py -v
```

**Step 4: Commit**

```bash
git add diff_engine.py tests/test_diff_engine.py
git commit -m "feat: diff engine with GitHub-style HTML rendering"
```

---

### Task 2.2: Streamlit App — Tab 1

**Files:**
- Create: `app.py`

**Step 1: Create `app.py`**

```python
# app.py
import os
import streamlit as st
from epo_client import get_family_members, get_claims
from file_manager import ensure_directory, write_claims_file, list_claims_files, read_claims_file
from diff_engine import compute_diff, render_diff_html

st.set_page_config(page_title="Patent Claims Analyzer", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stButton > button {
    background-color: #1B6CA8; color: white; border-radius: 6px;
    border: none; padding: 0.5rem 1.2rem; font-weight: 500;
}
.stButton > button:hover { background-color: #155a8a; }
</style>""", unsafe_allow_html=True)

st.title("📋 Patent Claims Analyzer")

tab1, tab2, tab3 = st.tabs(["📥 Fetch & Download", "🔍 Compare", "🤖 AI Analysis"])

with tab1:
    pct_input = st.text_input("PCT Code", placeholder="e.g. WO2020227475A1")
    if st.button("Search", key="search_btn"):
        if not pct_input.strip():
            st.error("Please enter a PCT code.")
        else:
            with st.spinner("Fetching family members..."):
                try:
                    members = get_family_members(pct_input.strip())
                    st.session_state["members"] = members
                    st.session_state["pct"] = pct_input.strip()
                    st.success(f"Found {len(members)} family members.")
                except Exception as e:
                    st.error(f"Error: {e}")

    if "members" in st.session_state:
        members = st.session_state["members"]
        pct = st.session_state["pct"]
        select_all = st.checkbox("Select All", key="select_all")
        selected = []
        for i, m in enumerate(members):
            checked = st.checkbox(f"{m['country']} — {m['doc_id']}", value=select_all, key=f"member_{i}")
            if checked:
                selected.append(m)

        if st.button("Download Selected", key="download_btn"):
            if not selected:
                st.warning("Select at least one member.")
            else:
                ensure_directory(pct)
                progress = st.progress(0)
                for idx, m in enumerate(selected):
                    try:
                        claims = get_claims(m["doc_id"])
                        write_claims_file(pct, m["doc_id"], f"# Claims — {m['doc_id']}\n\n{claims}")
                    except Exception as e:
                        st.warning(f"Could not download {m['doc_id']}: {e}")
                    progress.progress((idx + 1) / len(selected))
                st.success("Download complete!")

        st.divider()
        with st.expander("➕ Add Custom MD File"):
            custom_name = st.text_input("File name (without .md)", key="custom_name")
            custom_text = st.text_area("Claims content (Markdown)", key="custom_text", height=200)
            if st.button("Save Custom File", key="save_custom_btn"):
                if "pct" not in st.session_state:
                    st.error("Search a PCT code first.")
                elif not custom_name.strip():
                    st.error("Enter a file name.")
                else:
                    write_claims_file(st.session_state["pct"], custom_name.strip(), custom_text)
                    st.success(f"Saved {custom_name}.md")

with tab2:
    st.header("🔍 Compare Claims")
    pct_compare = st.text_input("PCT Code to compare", key="pct_compare")
    if pct_compare:
        files = list_claims_files(pct_compare.strip())
        if not files:
            st.warning("No downloaded files found for this PCT code.")
        else:
            file_names = [os.path.basename(f) for f in files]
            col1, col2 = st.columns(2)
            with col1:
                left_choice = st.selectbox("Version A (older)", file_names, key="left_file")
            with col2:
                right_choice = st.selectbox("Version B (newer)", file_names, key="right_file")
            if st.button("Compare", key="compare_btn"):
                left_path = files[file_names.index(left_choice)]
                right_path = files[file_names.index(right_choice)]
                diff = compute_diff(read_claims_file(left_path), read_claims_file(right_path))
                st.session_state["last_diff"] = diff
                st.session_state["diff_html"] = render_diff_html(diff)
    if "diff_html" in st.session_state:
        st.components.v1.html(st.session_state["diff_html"], height=600, scrolling=True)

with tab3:
    st.info("AI Analysis — available in Phase 4")
```

**Step 2: Run app**

```bash
streamlit run app.py
```

Manually verify: search PCT, select members, download, add custom file.

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat: streamlit UI - tabs 1 and 2 live"
```

---

## Phase 3 — Claims Comparison (Diff Viewer)

**Goal:** The Compare tab is already wired in `app.py` from Phase 2. This phase verifies and polishes the diff rendering.

---

### Task 3.1: Verify Diff Rendering End-to-End

**Step 1:** Download at least 2 family members from Tab 1 using `WO2020227475A1`.

**Step 2:** Go to Tab 2, enter PCT code, select two files, click Compare.

**Step 3:** Verify colored diff renders in the component frame (green = added, red = removed).

**Step 4:** If diff is empty (identical files), edit one file manually to introduce a change and retest.

**Step 5: Commit any polish fixes**

```bash
git add app.py diff_engine.py
git commit -m "feat: phase 3 - diff viewer verified and polished"
```

---

## Phase 4 — AI Analysis (Gemini)

**Goal:** Translate non-English claims to a new `_EN.md` file; analyze diffs for legal meaning.

---

### Task 4.1: Gemini Client

**Files:**
- Create: `gemini_client.py`
- Create: `tests/test_gemini_client.py`

**Step 1: Write failing tests**

```python
# tests/test_gemini_client.py
from gemini_client import translate_claims, analyze_diff

def test_translate_claims_returns_string():
    result = translate_claims("1. Eine Vorrichtung.", source_lang="DE")
    assert isinstance(result, str)
    assert len(result) > 5

def test_analyze_diff_returns_dict():
    diff = ["- 1. A widget.", "+ 1. An improved widget with sensor."]
    result = analyze_diff(diff)
    assert "summary" in result
    assert "motivation" in result
    assert "risk_assessment" in result
```

**Step 2: Implement `gemini_client.py`**

```python
# gemini_client.py
import os, json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.0-flash-exp"

def translate_claims(text: str, source_lang: str = "auto") -> str:
    model = genai.GenerativeModel(MODEL)
    prompt = (
        f"Translate the following patent claims from {source_lang} to English. "
        f"Preserve claim numbering and legal formatting.\n\n{text}"
    )
    return model.generate_content(prompt).text

def analyze_diff(diff_lines: list[str]) -> dict:
    model = genai.GenerativeModel(MODEL)
    diff_text = "\n".join(diff_lines)
    prompt = f"""You are a patent attorney analyzing claim amendments.
Given this unified diff of patent claims, respond with a JSON object with keys:
- "summary": plain-language summary of what changed
- "motivation": likely legal/strategic motivation behind the change
- "risk_assessment": whether scope was broadened or narrowed and why

Diff:
{diff_text}

Respond ONLY with valid JSON, no markdown fences."""
    raw = model.generate_content(prompt).text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
```

**Step 3: Run tests (requires GEMINI_API_KEY in `.env`)**

```bash
pytest tests/test_gemini_client.py -v
```

**Step 4: Commit**

```bash
git add gemini_client.py tests/test_gemini_client.py
git commit -m "feat: gemini client - translate and analyze diff"
```

---

### Task 4.2: AI Tab in `app.py`

**Files:**
- Modify: `app.py`

**Step 1: Add import at top of `app.py`**

```python
from gemini_client import translate_claims, analyze_diff
```

**Step 2: Replace Tab 3 block**

```python
with tab3:
    st.header("🤖 AI Analysis")

    st.subheader("Translate Claims")
    pct_ai = st.text_input("PCT Code", key="pct_ai")
    if pct_ai:
        ai_files = list_claims_files(pct_ai.strip())
        if ai_files:
            ai_file_names = [os.path.basename(f) for f in ai_files]
            selected_ai_file = st.selectbox("Select file to translate", ai_file_names, key="ai_file_select")
            source_lang = st.text_input("Source language (e.g. DE, FR, JA)", value="auto", key="src_lang")
            if st.button("Translate to English", key="translate_btn"):
                idx = ai_file_names.index(selected_ai_file)
                content = read_claims_file(ai_files[idx])
                with st.spinner("Translating with Gemini..."):
                    translated = translate_claims(content, source_lang)
                base = selected_ai_file.replace(".md", "")
                write_claims_file(pct_ai.strip(), f"{base}_EN", translated)
                st.success(f"Saved {base}_EN.md")
                st.text_area("Translated Claims", translated, height=300)
        else:
            st.info("No files found for this PCT code.")

    st.divider()
    st.subheader("Analyze Diff with AI")
    if st.session_state.get("last_diff"):
        if st.button("Analyze Changes with Gemini", key="analyze_btn"):
            with st.spinner("Analyzing with Gemini..."):
                result = analyze_diff(st.session_state["last_diff"])
            st.markdown(f"**📝 Summary:** {result.get('summary', 'N/A')}")
            st.markdown(f"**💡 Motivation:** {result.get('motivation', 'N/A')}")
            st.markdown(f"**⚖️ Risk Assessment:** {result.get('risk_assessment', 'N/A')}")
    else:
        st.info("Run a comparison in the Compare tab first, then return here.")
```

**Step 3: Run and manually test**

```bash
streamlit run app.py
```

- Translate a non-English `.md` → verify new `_EN.md` created
- Compare two files in Tab 2 → switch to Tab 3 → click "Analyze Changes with Gemini" → verify JSON response renders

**Step 4: Final commit**

```bash
git add app.py
git commit -m "feat: phase 4 - AI translation and diff analysis tab"
```

---

## Summary

| Phase | Key Files | Deliverable |
|-------|-----------|-------------|
| 1 | `epo_client.py`, `file_manager.py`, `test_phase1.py` | CLI: fetch + download all claims for `WO2020227475A1` |
| 2 | `diff_engine.py`, `app.py` | Streamlit UI with Fetch & Compare tabs |
| 3 | `app.py` (Tab 2 verified) | GitHub-style colored diff viewer |
| 4 | `gemini_client.py`, `app.py` (Tab 3) | AI translation + diff analysis |

## Quick Start

```bash
cp .env.example .env          # fill in credentials
pip install -r requirements.txt
python test_phase1.py         # validate Phase 1
streamlit run app.py          # run full app
```
