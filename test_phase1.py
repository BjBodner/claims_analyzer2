"""CLI script to validate full Phase 1 pipeline with WO2020227475A1"""
import os
from epo_client import get_family_members, get_claims
from file_manager import write_claims_file, list_claims_files

def validate_phase1():
    PCT = "US12145846B2"
    
    print(f"🚀 Starting Phase 1 Validation for: {PCT}")
    
    try:
        # 1. Fetch Family
        print(f"📡 Fetching family members from EPO...")
        members = get_family_members(PCT)
        print(f"✅ Found {len(members)} family members.")
        
        # 2. Download and Save
        print("\n📥 Downloading and saving claims...")
        downloaded_count = 0
        for m in members:
            doc_id = m["doc_id"]
            try:
                claims = get_claims(doc_id)
                if claims:
                    content = f"# Claims: {doc_id}\n\n{claims}"
                    path = write_claims_file(PCT, doc_id, content)
                    print(f"  ✓ Saved: {doc_id} to {os.path.basename(path)}")
                    downloaded_count += 1
                else:
                    print(f"  ⚠ No claims text found for {doc_id} (Skipping)")
            except Exception as e:
                print(f"  ❌ Error downloading {doc_id}: {e}")

        # 3. Verify Files
        print(f"\n📁 Verifying local files in claims/{PCT}/:")
        saved_files = list_claims_files(PCT)
        for f in saved_files:
            print(f"  - {f}")
        
        if downloaded_count > 0:
            print(f"\n✨ Phase 1 Validation SUCCESSFUL! ({downloaded_count} files saved)")
        else:
            print("\n❌ Phase 1 Validation FAILED: No files were downloaded.")

    except Exception as e:
        print(f"\n💥 CRITICAL ERROR during validation: {e}")

if __name__ == "__main__":
    validate_phase1()
