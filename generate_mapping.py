import pandas as pd
import json
import re
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "schema_changes_detailed.csv"
MAPPING_PATH = BASE_DIR / "mapping.json"

def clean_slug(text):
    """Turns 'Computer & Info Sciences' into 'computer_info_sciences'"""
    if pd.isna(text): return "total"
    text = str(text).lower()
    text = re.sub(r'\(.*?\)', '', text) # Remove (parentheses)
    text = re.sub(r'[^a-z0-9]', '_', text) # Special chars to _
    text = re.sub(r'_+', '_', text) # Dedupe _
    return text.strip('_')

def generate_mapping():
    print(f"📖 Reading {CSV_PATH}...")
    try:
        df = pd.read_csv(CSV_PATH)
    except FileNotFoundError:
        print("❌ Error: schema_changes_detailed.csv not found. Please upload it.")
        return

    mapping = {
        "funding_sources": {},
        "federal_detailed": {},    # Q9
        "federal_agencies": {},    # Q10
        "nonfed_detailed": {},     # Q11
        "other_questions": {}
    }

    count = 0
    
    for _, row in df.iterrows():
        qid = str(row['Question ID'])
        row_lbl = row['Row Label']
        col_lbl = row['Column Label']
        desc = row['Question Text']
        start_year = row['First Year']
        end_year = row['Last Year']

        # Skip rows with no ID
        if qid == 'nan': continue

        # --- 1. Funding Sources (Q1) ---
        if qid.startswith('01'):
            # Key uses Row Label (e.g. "Federal government")
            slug = clean_slug(row_lbl)
            key = f"src_{slug}"
            category = "funding_sources"

        # --- 2. Federal Fields & Agencies (Q9) ---
        elif qid.startswith(('09', '9')):
            # Key uses Row (Field) + Col (Agency)
            # e.g. "fed_aerospace_eng_dod"
            field_slug = clean_slug(row_lbl)
            agency_slug = clean_slug(col_lbl)
            key = f"fed_{field_slug}_{agency_slug}"
            category = "federal_detailed"

        # --- 3. Federal Agency Totals (Q10) ---
        elif qid.startswith('10'):
            # Usually Row Label is the Agency
            slug = clean_slug(row_lbl)
            key = f"agency_{slug}"
            category = "federal_agencies"

        # --- 4. Non-Federal Fields & Sources (Q11) ---
        elif qid.startswith('11'):
            # Key uses Row (Field) + Col (Source)
            # e.g. "nonfed_biology_business"
            field_slug = clean_slug(row_lbl)
            source_slug = clean_slug(col_lbl)
            key = f"nonfed_{field_slug}_{source_slug}"
            category = "nonfed_detailed"

        # --- 5. Catch-All ---
        else:
            category = "other_questions"
            key = f"q{clean_slug(qid)}_{clean_slug(row_lbl)}"

        # Construct the mapping entry
        # We store the "match_criteria" to allow exact lookup later
        entry = {
            "key": key,
            "question_id": qid,
            "row_match": row_lbl if pd.notna(row_lbl) else None,
            "col_match": col_lbl if pd.notna(col_lbl) else None,
            "description": f"{desc}: {row_lbl} - {col_lbl}",
            "start_year": int(start_year),
            "end_year": int(end_year)
        }
        
        # Add to the dictionary (Handle duplicates if schema drifted slightly)
        # If key exists, we might overwrite, but usually latest year wins in this logic
        mapping[category][key] = entry
        count += 1

    # Save
    with open(MAPPING_PATH, 'w') as f:
        json.dump(mapping, f, indent=2)

    print(f"✅ Generated mapping.json with {count} fields based on your CSV report.")

if __name__ == "__main__":
    generate_mapping()