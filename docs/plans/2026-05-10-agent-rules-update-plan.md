# Agent Rules Update Implementation Plan

> **For Antigravity:** REQUIRED WORKFLOW: Use `.agent/workflows/execute-plan.md` to execute this plan in single-flow mode.

**Goal:** Update `AGENTS.md` with project-specific workspace rules to ensure compliance with the Patent Claims Analyzer design.

**Architecture:** Append a new `# Project Workspace Rules: Patent Claims Analyzer` section to the existing `.agent/AGENTS.md` file.

**Tech Stack:** Markdown

---

### Task 1: Update AGENTS.md

**Files:**
- Modify: `.agent/AGENTS.md`

**Step 1: Write the content to append**

```markdown

## Project Workspace Rules: Patent Claims Analyzer

Follow these rules for all development within this project:

1.  **Modular Responsibility**:
    - `epo_client.py`: Handle all EPO OPS API interactions (OAuth, family discovery, raw claims fetch).
    - `file_manager.py`: Handle all file system operations (creating directories, reading/writing `.md` files).
    - `diff_engine.py`: Logic for computing diffs and rendering them as colored HTML.
    - `gemini_client.py`: Handle all AI interactions (translation to English, substantive diff analysis).
    - `app.py`: Main Streamlit entrypoint; orchestration of modules and UI layout only.

2.  **File Naming & Organization**:
    - Patent claims files MUST follow the pattern: `<COUNTRY>_<DOCID>_<KIND>.md` (e.g., `US_20230123456_A1.md`).
    - ALL downloaded or generated claims files MUST be stored in `claims/<PCT_CODE>/`.
    - Use UTF-8 encoding for all Markdown files.

3.  **UI & Aesthetics**:
    - **Accent Color**: Always use `#1B6CA8` for primary actions and accents in Streamlit.
    - **Typography**: Specify `Inter` font in CSS/Streamlit settings.
    - **Style**: Maintain a clean, minimal, "premium" look. Avoid clutter.
    - Use Streamlit `components.html` for rendering complex diffs to ensure a high-fidelity, GitHub-like visual experience.

4.  **Environment & Security**:
    - NEVER hardcode API keys or secrets.
    - Use `python-dotenv` and access keys via `os.getenv()`.
    - Ensure `.env` is listed in `.gitignore`.

5.  **Data Processing Flow**:
    - Translation of non-English claims must be a post-download step using Gemini, resulting in a parallel `<NAME>_EN.md` file.
    - Gemini analysis should return structured JSON for consistent UI display of "Summary", "Motivation", and "Risk Assessment".
```

**Step 2: Append content to .agent/AGENTS.md**

Run: `cat >> .agent/AGENTS.md <<EOF...` (or use `replace_file_content` via the tool)

**Step 3: Verify the file content**

Run: `cat .agent/AGENTS.md`
Expected: The new section is present at the end of the file.

**Step 4: Commit**

```bash
git add .agent/AGENTS.md
git commit -m "feat: add project-specific workspace rules to AGENTS.md"
```
