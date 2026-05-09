# Patent Claims Analyzer — Design Document

**Date:** 2026-05-09  
**Chosen Stack:** Python + Streamlit + EPO OPS API + Google Gemini  
**Architecture:** Modular Engine (Approach 1)

---

## Project Goal

Build a Streamlit web application that allows a user to input a PCT patent code, fetch all family members via the EPO OPS API, download their claims as organized Markdown files, compare claims across versions using a Git-like diff view, and get AI-powered analysis of the changes using Google Gemini.

---

## Architecture Overview

```
claims_analyzer2/
├── app.py                  # Main Streamlit entrypoint — multi-page app
├── epo_client.py           # EPO OPS API interactions
├── gemini_client.py        # Google Gemini AI interactions
├── file_manager.py         # File system operations for claims/ directory
├── diff_engine.py          # Diff computation and HTML rendering
├── .env                    # API keys (not committed)
├── .env.example            # Template for required keys
├── requirements.txt        # Python dependencies
└── claims/                 # Output directory
    └── <PCT_CODE>/         # One subdirectory per searched PCT code
        └── <MEMBER>.md     # One Markdown file per patent family member
```

### Module Responsibilities

| Module | Responsibility |
|---|---|
| `epo_client.py` | OAuth2 authentication with EPO OPS; resolve PCT → family members; fetch claims in English |
| `file_manager.py` | Create/manage `claims/<PCT>/` directories; write/read `.md` files; list existing files |
| `diff_engine.py` | Compute unified diff between two or more claim texts; render diff as colored HTML |
| `gemini_client.py` | Translate non-English claims to English (create parallel file); analyze diff for legal/strategic meaning |
| `app.py` | Streamlit multi-tab UI orchestrating all modules |

---

## Phase Breakdown

### Phase 1 — API Infrastructure & CLI Validation

**Goal:** Prove the EPO OPS API integration works end-to-end. No UI.

**Steps:**
1. Set up project structure, `requirements.txt`, `.env`, `.env.example`
2. Implement `epo_client.py`:
   - `get_access_token()` → OAuth2 Bearer token
   - `get_family_members(pct_code)` → list of `{doc_id, country, kind, title}` dicts
   - `get_claims(doc_id, lang='EN')` → raw claims text string
3. Implement `file_manager.py`:
   - `ensure_directory(pct_code)` → create `claims/<PCT_CODE>/` if missing
   - `write_claims_file(pct_code, doc_id, content)` → write `.md` file
   - `list_claims_files(pct_code)` → list existing `.md` files
4. Write a `test_phase1.py` CLI script to validate with `WO2020227475A1`
5. Verify: all family members discovered, claims downloaded, `.md` files created

---

### Phase 2 — Streamlit UI (Fetch & Download)

**Goal:** Visual interface for Phase 1 capabilities.

**UI Tabs:**
- **Tab 1: Fetch & Download**
  - Text input: PCT code
  - "Search" button → show family members table (country, doc_id, title, language)
  - Checkboxes per row to select which members to download
  - "Select All" toggle
  - "Download Selected" button → downloads claims → auto-navigate to Compare tab
  - Expandable form: "Add custom MD file" (name + text area) → saves to same directory
- **Style:** Clean, minimal, modern. White background, light grays, accent color `#1B6CA8`. Inter font.

---

### Phase 3 — Claims Comparison (Diff Viewer)

**Goal:** Side-by-side and inline diff between 2+ patent versions.

**Features:**
- **Two-version mode:** Standard left/right side-by-side diff (like GitHub PR)
- **Multi-version mode:** Sequential comparison of N versions rendered as a cascading diff
- Select versions from a dropdown of downloaded `.md` files
- Inline view toggle (unified diff) vs. side-by-side
- Color coding: red = removed, green = added, gray = unchanged
- Diff rendered using custom HTML (Streamlit `components.html`) to achieve GitHub-quality look

---

### Phase 4 — AI Analysis (Gemini)

**Goal:** Add AI-powered translation and substantive analysis.

**Features:**
- **Translation:** If a `.md` file contains non-English claims, a "Translate" button creates a new parallel `_EN.md` file using Gemini
- **Diff Analysis:** After viewing a diff, an "Analyze with AI" button sends the diff to Gemini and returns:
  - Summary of what changed (in legal plain language)
  - Hypothesized motivation behind the change
  - Risk assessment (scope narrowed/broadened)
- Gemini model: `gemini-2.0-flash-exp` (free tier)

---

## Environment Variables Required

```
EPO_CLIENT_ID=your_epo_client_id
EPO_CLIENT_SECRET=your_epo_client_secret
GEMINI_API_KEY=your_gemini_api_key
```

---

## Key Technical Decisions

1. **EPO OPS API:** Uses the published REST API at `https://ops.epo.org/3.2/rest-services/`. OAuth2 client credentials flow for auth. Family members retrieved via `published-data/publication/epodoc/family` endpoint.
2. **Claims retrieval:** Use `/claims` endpoint. Request `lang=EN` first; fall back to original if not available. Gemini handles translation post-download.
3. **Diff Engine:** Python's built-in `difflib.unified_diff` for computation; custom HTML template for rendering (red/green/gray highlighting, line numbers).
4. **Gemini API:** `google-generativeai` Python SDK. Structured prompts for analysis; returns JSON with `summary`, `motivation`, `risk_assessment` fields.
5. **File naming convention:** `<COUNTRY>_<DOCID>_<KIND>.md`, e.g., `US_20230123456_A1.md`

---

## Dependencies

```
streamlit>=1.32
requests>=2.31
python-dotenv>=1.0
google-generativeai>=0.5
```
