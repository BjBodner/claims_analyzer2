# Design Document: Agent Rules Update for Patent Claims Analyzer

**Date:** 2026-05-10  
**Status:** Approved  
**Topic:** Adding project-specific workspace rules to `AGENTS.md` to ensure compliance with the design specification.

---

## Goal

The goal is to formalize the technical and stylistic requirements of the Patent Claims Analyzer into a set of executable rules for the Antigravity agent. This will ensure that all future code generation and modifications strictly adhere to the project's architecture, naming conventions, and UI standards.

---

## Proposed Changes

### [MODIFY] [AGENTS.md](file:///Users/benjaminbodner/Documents/%D7%A1%D7%93%D7%A0%D7%90%D7%95%D7%AA/%D7%A8%D7%A9%D7%95%D7%AA_%D7%94%D7%A4%D7%98%D7%A0%D7%98%D7%99%D7%9D/%D7%9E%D7%A4%D7%92%D7%A9_%D7%A8%D7%91%D7%99%D7%A2%D7%99/claims_analyzer2/.agent/AGENTS.md)

Add a new section `# Project Workspace Rules: Patent Claims Analyzer` with the following rules:

1.  **Modular Responsibility**:
    - `epo_client.py`: All EPO OPS API interactions.
    - `file_manager.py`: All file system operations (CRUD for Markdown files).
    - `diff_engine.py`: Logic for computing and rendering claim differences.
    - `gemini_client.py`: All AI interactions (translation and analysis).
    - `app.py`: UI orchestration only.

2.  **File Naming & Organization**:
    - Patent claims MUST be named `<COUNTRY>_<DOCID>_<KIND>.md`.
    - ALL claims files MUST be stored in `claims/<PCT_CODE>/`.
    - Use UTF-8 encoding for all Markdown files.

3.  **UI & Styling**:
    - **Accent Color**: `#1B6CA8`.
    - **Typography**: `Inter` font family.
    - **Theme**: Light theme, clean, minimal, premium aesthetic.
    - Use Streamlit `components.html` for complex diff rendering to maintain GitHub-quality visuals.

4.  **Environment & Security**:
    - NEVER hardcode API keys.
    - Use `python-dotenv` for all environment variable management.
    - Ensure `.env` is in `.gitignore` (if not already).

5.  **Data Processing**:
    - Gemini translation must be handled as a post-download step, creating a parallel `_EN.md` file.
    - AI analysis should return structured JSON for consistent parsing.

---

## Verification Plan

### Manual Verification
- Review the `AGENTS.md` file to ensure the rules are correctly formatted and clear.
- Perform a "dry run" by asking the agent to explain a project rule to verify it has read them.
