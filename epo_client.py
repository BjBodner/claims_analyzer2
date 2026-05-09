import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

EPO_BASE = "https://ops.epo.org/3.2/rest-services"
_token_cache = {"token": None}


def get_access_token() -> str:
    """Fetch a Bearer token using client credentials from env vars."""
    resp = requests.post(
        "https://ops.epo.org/3.2/auth/accesstoken",
        data={"grant_type": "client_credentials"},
        auth=(os.getenv("EPO_CLIENT_ID"), os.getenv("EPO_CLIENT_SECRET")),
        timeout=15,
    )
    resp.raise_for_status()
    _token_cache["token"] = resp.json()["access_token"]
    return _token_cache["token"]


def _headers(accept: str = "application/json") -> dict:
    """Return auth headers, fetching a fresh token each call."""
    return {
        "Authorization": f"Bearer {get_access_token()}",
        "Accept": accept,
    }


def get_family_members(pct_code: str) -> list[dict]:
    """Return list of family members for a given PCT/publication code.
    Uses the /biblio endpoint for richer data as suggested in lessons.
    """
    parts = pct_code.strip().upper()
    
    # Family Service REQUIRES docdb format: CC.number.KC
    import re
    match = re.match(r"^([A-Z]{2})(\d+)([A-Z]\d+)?$", parts)
    if match:
        cc, num, kc = match.groups()
        normalized = f"{cc}.{num}.{kc}" if kc else f"{cc}.{num}"
        print(f"  🔍 Normalizing for DOCDB: {parts} -> {normalized}")
        parts = normalized

    # Use /biblio at the end for the full family experience
    url = f"{EPO_BASE}/family/publication/docdb/{parts}/biblio"
    resp = requests.get(url, headers=_headers("application/json"), timeout=15)
    resp.raise_for_status()
    data = resp.json()
    
    # Safe navigation
    def safe_get(d, key):
        if isinstance(d, dict): return d.get(key, {})
        if isinstance(d, list) and len(d) > 0: 
            if isinstance(d[0], dict): return d[0].get(key, {})
        return {}

    world_data = safe_get(data, "ops:world-patent-data")
    patent_family = safe_get(world_data, "ops:patent-family")
    family_members = patent_family.get("ops:family-member", [])
    
    if isinstance(family_members, dict):
        family_members = [family_members]

    members = []
    for m in family_members:
        if not isinstance(m, dict): continue
        
        pub_ref = m.get("publication-reference", {})
        doc_ids = pub_ref.get("document-id", [])
        if isinstance(doc_ids, dict):
            doc_ids = [doc_ids]
            
        # Prioritize docdb entry as per lessons
        best_did = None
        for did in doc_ids:
            if not isinstance(did, dict): continue
            if did.get("@document-id-type") == "docdb":
                best_did = did
                break
        
        # Fallback to any dict if docdb not found
        if not best_did and doc_ids:
            best_did = doc_ids[0]

        if best_did and isinstance(best_did, dict):
            country = best_did.get("country", {}).get("$", "")
            number = best_did.get("doc-number", {}).get("$", "")
            kind = best_did.get("kind", {}).get("$", "")
            
            if country and number:
                doc_id = f"{country}.{number}.{kind}" if kind else f"{country}.{number}"
                if not any(x["doc_id"] == doc_id for x in members):
                    members.append({
                        "doc_id": doc_id,
                        "country": country,
                        "number": number,
                        "kind": kind,
                    })
    return members


def get_claims(doc_id: str) -> str:
    """Fetch and clean claims text using 'deep walker' and 'regex splitter' lessons."""
    # Claims also work best with docdb format in the published-data endpoint
    url = f"{EPO_BASE}/published-data/publication/docdb/{doc_id}/claims"
    resp = requests.get(url, headers=_headers("application/xml"), timeout=15)
    
    if resp.status_code == 404:
        return ""
    resp.raise_for_status()

    try:
        root = ET.fromstring(resp.content)
        
        # 1. Deep Text Extraction (itertext captures all nested content)
        raw_text = "".join(root.itertext()).strip()
        
        # 2. Header Stripping
        headers_to_strip = [
            "CLAIMS", "REVENDICATIONS", "ANSPRÜCHE", "PATENTANSPRÜCHE", 
            "WHAT IS CLAIMED IS:", "THE INVENTION CLAIMED IS:"
        ]
        clean_text = raw_text
        for h in headers_to_strip:
            if clean_text.upper().startswith(h):
                clean_text = clean_text[len(h):].strip()
                break

        # 3. Robust Re-splitting (Regex from lessons)
        # We look for "1. ", "2. " etc. at start of line or after newline
        import re
        claims = re.split(r"(?:^|\n)\s*(\d{1,4})\.\s+", clean_text)
        
        if len(claims) > 1:
            # re.split with groups returns [prefix, num1, text1, num2, text2, ...]
            formatted_claims = []
            for i in range(1, len(claims), 2):
                num = claims[i]
                text = claims[i+1].strip()
                if text:
                    formatted_claims.append(f"{num}. {text}")
            return "\n\n".join(formatted_claims)
        
        return clean_text
    except Exception as e:
        print(f"  ❌ Error processing claims for {doc_id}: {e}")
        return ""
