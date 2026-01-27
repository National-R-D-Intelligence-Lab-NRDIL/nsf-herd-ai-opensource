import pandas as pd
import json
import sqlite3
import glob
import os
from pathlib import Path
from downloader import HERDDownloader

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "raw"
DB_PATH = BASE_DIR / "herd.db"
MAPPING_PATH = BASE_DIR / "mapping.json"

def run_etl():
    # 1. DOWNLOAD
    print("🔄 Checking for data...")
    downloader = HERDDownloader(DATA_DIR)
    downloader.run(start_year=2010)

    print(f"🔌 Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    
    # 2. LOAD MAPPING
    if not MAPPING_PATH.exists():
        print("❌ mapping.json missing. Run 'generate_mapping.py' first!")
        return

    with open(MAPPING_PATH, 'r') as f:
        full_config = json.load(f)

    # Flatten mapping into a "Lookup Dictionary"
    # Keys = (Question ID, Row Label, Col Label) -> Standard Name
    lookup_map = {}
    metadata_rows = []

    print("📚 Building Lookup Table...")
    for category, items in full_config.items():
        for key, info in items.items():
            # Create a tuple key for fast matching
            # We treat None/NaN as empty strings for consistent matching
            qid = str(info['question_id'])
            r_lbl = str(info['row_match']) if info['row_match'] else ""
            c_lbl = str(info['col_match']) if info['col_match'] else ""
            
            # Key: "09A|Computer Science|DOD"
            lookup_key = f"{qid}|{r_lbl}|{c_lbl}".lower()
            lookup_map[lookup_key] = key
            
            # Add to metadata
            metadata_rows.append({
                "category": category,
                "column_name": key,
                "description": info['description'],
                "start_year": info['start_year'],
                "end_year": info['end_year']
            })

    # Save Metadata
    pd.DataFrame(metadata_rows).to_sql('data_dictionary', conn, if_exists='replace', index=False)

    # 3. PROCESS FILES
    csv_files = glob.glob(str(DATA_DIR / "*.csv"))
    csv_files.sort()
    
    # Name Normalization Map
    master_names = {}
    if csv_files:
        df_latest = pd.read_csv(csv_files[-1], encoding='latin-1', dtype={'inst_id': str}, low_memory=False)
        for _, row in df_latest[['inst_id', 'inst_name_long']].drop_duplicates().iterrows():
            master_names[row['inst_id']] = row['inst_name_long']

    all_years_data = []
    print(f"📦 Processing {len(csv_files)} files using detailed mapping...")

    for file_path in csv_files:
        try:
            df = pd.read_csv(file_path, encoding='latin-1', dtype={'inst_id': str}, low_memory=False)
            
            # --- THE MATCHING LOGIC ---
            # 1. Normalize Raw Data columns to string & lowercase
            df['qid_str'] = df['questionnaire_no'].astype(str)
            
            # Find the row/col label columns dynamically
            df.columns = [c.lower() for c in df.columns]
            
            # Helper to find existing columns
            def get_col(df, candidates):
                for c in candidates:
                    if c in df.columns: return df[c].fillna("").astype(str)
                return pd.Series([""] * len(df), index=df.index)

            row_series = get_col(df, ['row', 'row_label', 'question_label'])
            col_series = get_col(df, ['column', 'column_label', 'col'])

            # 2. Create the "Fingerprint" for every row in the CSV
            # Format: "id|row|col"
            df['lookup_key'] = (df['qid_str'] + "|" + row_series + "|" + col_series).str.lower()
            
            # 3. Map to Standard Name
            df['standard_name'] = df['lookup_key'].map(lookup_map)
            
            # 4. Filter: Keep only rows that matched our mapping
            df_filtered = df.dropna(subset=['standard_name']).copy()

            if df_filtered.empty:
                print(f"   ⚠️  No matching data found in {os.path.basename(file_path)}")
                continue

            # 5. Normalization & Pivot
            # (Restore original camelCase ID/Name columns if lowercase conversion messed them up)
            # Actually, standardizing is safer:
            pivot_index = ['inst_id', 'inst_name_long', 'inst_city', 'inst_state_code', 'year']
            # Map index cols to available lowercase cols
            actual_index = [c for c in pivot_index if c in df_filtered.columns]
            
            if 'inst_id' in df_filtered.columns:
                df_filtered['inst_name_long'] = df_filtered['inst_id'].map(master_names).fillna(df_filtered['inst_name_long'])

            wide_df = df_filtered.pivot_table(
                index=actual_index,
                columns='standard_name',
                values='data',
                aggfunc='first'
            ).reset_index()

            all_years_data.append(wide_df)
            
        except Exception as e:
            print(f"   ❌ Error {os.path.basename(file_path)}: {e}")

    # 4. SAVE
    if all_years_data:
        final_df = pd.concat(all_years_data, ignore_index=True)
        
        # Rename for standard DB schema
        rename_map = {'inst_name_long': 'name', 'inst_city': 'city', 'inst_state_code': 'state'}
        final_df = final_df.rename(columns=rename_map)
        
        # Cleanup Numbers (Multiply by 1000)
        # Identify numeric columns (the ones from our mapping)
        mapped_cols = [m['column_name'] for m in metadata_rows]
        for col in mapped_cols:
            if col in final_df.columns:
                final_df[col] = final_df[col].fillna(0) * 1000

        final_df.to_sql('institutions', conn, if_exists='replace', index=False)
        print(f"\n✅ Success! Loaded {len(final_df)} rows with {len(final_df.columns)} columns.")
        
        conn.execute("CREATE INDEX IF NOT EXISTS idx_inst_id ON institutions(inst_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON institutions(name)")
    
    conn.close()

if __name__ == "__main__":
    run_etl()