import pandas as pd
import glob
import os
from pathlib import Path
from downloader import HERDDownloader

# Setup paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "raw"

def get_label_val(row, potential_cols):
    """Helper to extract text from the first existing column found."""
    for col in potential_cols:
        if col in row and pd.notna(row[col]):
            return str(row[col]).strip()
    return ""

def analyze_schema_changes():
    # 1. Ensure Data is Present
    print("🔄 Verifying data availability...")
    downloader = HERDDownloader(DATA_DIR)
    downloader.run(start_year=2010)

    csv_files = glob.glob(str(DATA_DIR / "*.csv"))
    csv_files.sort()
    
    if not csv_files:
        print("❌ No files found.")
        return

    print(f"\n🔍 Analyzing Detailed Schema (ID + Row + Column) across {len(csv_files)} years...")
    
    # Master storage: { unique_key : { year: description } }
    # unique_key = (questionnaire_no, row_label, column_label)
    schema_history = {}
    all_years = []

    # 2. Scan every file
    for file_path in csv_files:
        try:
            filename = os.path.basename(file_path)
            year_str = "".join(filter(str.isdigit, filename))
            year = int(year_str) if year_str else 0
            all_years.append(year)
            
            # Read file (read all cols to ensure we catch row/col labels)
            # Using low_memory=False to prevent mixed-type warnings
            df = pd.read_csv(file_path, encoding='latin-1', low_memory=False, dtype=str)
            
            # Normalize column names to lowercase for easier detection
            df.columns = [c.lower() for c in df.columns]
            
            # Identify which columns hold the labels
            row_cols = [c for c in df.columns if c in ['row', 'row_label', 'question_label']]
            col_cols = [c for c in df.columns if c in ['column', 'column_label', 'col']]
            
            # Extract unique schema definitions
            # We want unique combinations of: No, Question, Row, Column
            cols_to_use = ['questionnaire_no', 'question'] + row_cols + col_cols
            unique_rows = df[cols_to_use].drop_duplicates().to_dict('records')
            
            for item in unique_rows:
                qid = str(item.get('questionnaire_no', '')).strip()
                desc = str(item.get('question', '')).strip()
                
                # Get Row/Col labels safely
                row_lbl = get_label_val(item, row_cols)
                col_lbl = get_label_val(item, col_cols)
                
                if not qid or qid.lower() == 'nan': continue

                # Create a composite key to track this specific data point
                # e.g. ("09B01", "Aerospace Engineering", "")
                unique_key = (qid, row_lbl, col_lbl)
                
                if unique_key not in schema_history:
                    schema_history[unique_key] = {}
                
                schema_history[unique_key][year] = desc
                
        except Exception as e:
            print(f"   ❌ Error reading {filename}: {e}")

    # 3. Generate Analysis Report
    print("\n📊 Generating Report...")
    report_data = []
    
    for (qid, row_lbl, col_lbl), history in schema_history.items():
        years_active = sorted(history.keys())
        first_year = years_active[0]
        last_year = years_active[-1]
        latest_desc = history[last_year]
        
        # Status Logic
        if first_year == all_years[0] and last_year == all_years[-1]:
            status = "Consistent"
        elif first_year == all_years[0]:
            status = "Removed"
        elif last_year == all_years[-1]:
            status = "New / Added"
        else:
            status = "Intermittent"

        report_data.append({
            "Question ID": qid,
            "Row Label": row_lbl,
            "Column Label": col_lbl,
            "Question Text": latest_desc,
            "Status": status,
            "First Year": first_year,
            "Last Year": last_year,
            "Description Count": len(set(history.values()))
        })

    if not report_data:
        print("⚠️ No schema found.")
        return

    report_df = pd.DataFrame(report_data)
    
    # Sort for readability: ID -> Row Label
    report_df = report_df.sort_values(["Question ID", "Row Label"])
    
    # 4. Save & Summary
    output_csv = "schema_changes_detailed.csv"
    report_df.to_csv(output_csv, index=False)
    
    print("\n" + "="*60)
    print("SUMMARY OF DETAILED SCHEMA (ID + ROW + COL)")
    print("="*60)
    print(f"Total Unique Data Points: {len(report_df)}")
    print(f"Consistent: {len(report_df[report_df['Status'] == 'Consistent'])}")
    print(f"New/Added:  {len(report_df[report_df['Status'] == 'New / Added'])}")
    print("-" * 60)
    
    # Peek at Question 9 to verify it worked
    print("\nSAMPLE: FIELD OF STUDY BREAKDOWN (Q9)")
    q9_sample = report_df[report_df['Question ID'].astype(str).str.startswith(('09', '9'))].head(5)
    print(q9_sample[['Question ID', 'Row Label', 'First Year', 'Last Year']].to_string(index=False))

    print(f"\n📄 Full report saved to '{output_csv}'")

if __name__ == "__main__":
    analyze_schema_changes()