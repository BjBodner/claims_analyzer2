import os
import re

# Base directory for storing claims
CLAIMS_DIR = os.path.join(os.path.dirname(__file__), "claims")

def _sanitize(name: str) -> str:
    """Sanitize filename to prevent directory traversal or invalid characters."""
    return re.sub(r"[^\w\-.]", "_", name)

def ensure_directory(pct_code: str) -> str:
    """Ensure a directory exists for a specific patent family."""
    path = os.path.join(CLAIMS_DIR, _sanitize(pct_code))
    os.makedirs(path, exist_ok=True)
    return path

def write_claims_file(pct_code: str, filename: str, content: str) -> str:
    """Write claims content to a Markdown file in the appropriate directory."""
    directory = ensure_directory(pct_code)
    if not filename.endswith(".md"):
        filename += ".md"
    filepath = os.path.join(directory, _sanitize(filename))
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath

def list_claims_files(pct_code: str) -> list[str]:
    """List all Markdown claim files for a given patent family."""
    directory = ensure_directory(pct_code)
    if not os.path.exists(directory):
        return []
    return sorted([
        f for f in os.listdir(directory) if f.endswith(".md")
    ])

def read_claims_file(pct_code: str, filename: str) -> str:
    """Read content of a specific claims file."""
    directory = ensure_directory(pct_code)
    filepath = os.path.join(directory, _sanitize(filename))
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Claims file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()
