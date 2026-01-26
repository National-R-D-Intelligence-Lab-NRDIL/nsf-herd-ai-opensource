import sqlite3
import pandas as pd
from openai import OpenAI

# --- CONFIGURATION ---
# Point to Ollama instead of OpenAI
client = OpenAI(
    base_url='http://localhost:11434/v1',
    api_key='ollama'  # Required but ignored by Ollama
)

# Choose your local model
MODEL_NAME = "qwen2.5-coder" 
DB_PATH = "herd.db"

def get_schema():
    conn = sqlite3.connect(DB_PATH)
    try:
        dd = pd.read_sql("SELECT column_name, description FROM data_dictionary", conn)
        dd_text = dd.to_string(index=False)
    except:
        dd_text = "No data dictionary found."
        
    schema = pd.read_sql("PRAGMA table_info(institutions)", conn)
    columns = schema['name'].tolist()
    conn.close()
    
    return f"""
    Table: 'institutions'
    Columns: {', '.join(columns)}
    
    Data Dictionary:
    {dd_text}
    """

def ask_database(question):
    print(f"\n🦙 Local Llama is thinking about: '{question}'...")
    
    schema_context = get_schema()
    
    # We need a strict prompt for local models to ensure they output ONLY SQL
    prompt = f"""
    You are an expert SQL Data Analyst.
    
    Database Schema:
    {schema_context}
    
    Task: Convert this question into a SQLite query: "{question}"
    
    Rules:
    1. Return ONLY the SQL query. Do not wrap it in markdown. Do not explain.
    2. The table name is 'institutions'.
    3. Important: Money columns are in thousands.
    4. Use 'LIMIT 20' if appropriate.
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        
        # Clean up the response (Local models love to add markdown ```sql ... ```)
        sql_query = response.choices[0].message.content
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        
        print(f"⚡ Executing SQL: {sql_query}")
        
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(sql_query, conn)
        conn.close()
        
        if df.empty:
            print("⚠️ No results found.")
        else:
            print("\n📊 Results:")
            print(df.to_markdown(index=False))

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print(f"✅ Connected to Ollama ({MODEL_NAME})")
    while True:
        user_input = input("\nAsk a question (or 'q' to quit): ")
        if user_input.lower() in ['q', 'quit']: break
        ask_database(user_input)