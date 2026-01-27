import sqlite3
import pandas as pd
import yaml
from openai import OpenAI
import re

# --- CONFIGURATION ---
# client = OpenAI(
#     base_url='http://localhost:11434/v1',
#     api_key='ollama'
# )
# MODEL_NAME = "qwen2.5-coder" 

client = OpenAI(
    base_url='http://10.146.11.55:8001/v1', # Server IP
    api_key='EMPTY'
)

# MUST match the --model flag used on the server exactly
MODEL_NAME = "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"

DB_PATH = "herd.db"
CONFIG_PATH = "config.yml"

class LocalAgent:
    def __init__(self):
        self.config = self._load_config()
        self.all_columns = self._get_all_columns()
        
    def _load_config(self):
        """Loads the Institution Configuration."""
        try:
            with open(CONFIG_PATH, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ Config Error: {e}")
            return {}

    def _get_all_columns(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(institutions)")
            cols = [row[1] for row in cursor.fetchall()]
            conn.close()
            return cols
        except: return []

    def _find_relevant_columns(self, question):
        """Smart Column Search (Same as before)"""
        question = question.lower()
        relevant = ["name", "inst_id", "year"] # Always include ID
        
        keywords = {
            "computer": "computer", "cs": "computer", "engineer": "engineer",
            "business": "business", "federal": "fed", "institution": "institution",
            "math": "math", "bio": "bio", "life": "life", "psych": "psych"
        }
        for word, key in keywords.items():
            if word in question:
                matches = [c for c in self.all_columns if key in c]
                relevant.extend(matches)
        
        # Add totals if nothing specific is found
        if len(relevant) == 3:
            relevant.append("src_total")
            
        return list(set(relevant))[:50]

    def _clean_sql(self, text):
        """
        DeepSeek Specific Cleaner:
        It aggressively extracts SQL from markdown blocks or messy text.
        """
        print(f"   (Raw Model Output: {text[:60]}...)") # Debug print
        
        # Strategy 1: Look for Markdown Code Blocks (```sql ... ```)
        # DeepSeek almost always uses these.
        match = re.search(r'```sql\s*(.*?)\s*```', text, re.IGNORECASE | re.DOTALL)
        if match:
            clean = match.group(1).strip()
            return clean

        # Strategy 2: Look for standard SQL start/end if markdown is missing
        match = re.search(r'(SELECT.*?;)', text, re.IGNORECASE | re.DOTALL)
        if match:
            clean = match.group(1).replace('\n', ' ').strip()
            return clean
            
        # Strategy 3: Panic cleanup - remove common conversational starters
        # If it starts with "Here is", "Sure", etc., try to strip them.
        lines = text.split('\n')
        sql_lines = [l for l in lines if l.strip().upper().startswith(('SELECT', 'FROM', 'WHERE', 'AND', 'ORDER', 'LIMIT', 'UNION', '--'))]
        if sql_lines:
            return " ".join(sql_lines)

        return text.strip()

    def generate_sql(self, question):
        # 1. Build Peer Lists from Config
        inst = self.config['institution']
        my_id = inst['inst_id']
        my_name = inst['short_name']
        
        tx_peers = self.config['peers']['texas']
        tx_ids = ", ".join([f"'{p['id']}'" for p in tx_peers])
        
        nat_peers = self.config['peers']['national']
        nat_ids = ", ".join([f"'{p['id']}'" for p in nat_peers])
        
        # 2. Get Relevant Columns
        relevant_cols = self._find_relevant_columns(question)
        col_list_str = ", ".join(relevant_cols)
        
        prompt = f"""
        You are a SQL Expert for the {inst['name']}.
        
        ### CONTEXT & IDs (Use these for accuracy)
        - Current Institution ({my_name}): inst_id = '{my_id}'
        - Texas Peers List: ({tx_ids})
        - National Peers List: ({nat_ids})
        
        ### DATABASE SCHEMA
        Table: institutions
        Relevant Columns: {col_list_str}
        
        ### REQUEST
        "{question}"
        
        ### RULES
        1. **CRITICAL:** Use `inst_id` for specific schools. 
           - If user asks for "{my_name}" or "UNT", use: WHERE inst_id = '{my_id}'
           - If user asks for "Texas Peers", use: WHERE inst_id IN ({tx_ids})
        2. Always SELECT `name` to verify results.
        3. If no year is specified, default to: WHERE year = 2024.
        4. Return ONLY valid SQL ending in ;
        5. Output ONLY the SQL code. No explanation.
        """
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return self._clean_sql(response.choices[0].message.content)

    def summarize(self, question, df):
        if df.empty: return "No data found."
        data_text = df.to_string(index=False, max_rows=10)
        prompt = f"Summarize this data for: '{question}'.\nData:\n{data_text}\nKeep it to 2 sentences."
        response = client.chat.completions.create(
            model=MODEL_NAME, messages=[{"role": "user", "content": prompt}], temperature=0.3
        )
        return response.choices[0].message.content

    def run(self):
        print(f"✅ Config-Aware Agent Ready ({MODEL_NAME})")
        print(f"   🏛️  Identity: {self.config['institution']['name']} ({self.config['institution']['inst_id']})")
        
        while True:
            q = input("\nAsk (or 'q'): ")
            if q.lower() in ['q', 'quit']: break
            
            print("   Thinking...", end="\r")
            sql = self.generate_sql(q)
            print(f"⚡ SQL: {sql}")
            
            try:
                conn = sqlite3.connect(DB_PATH)
                df = pd.read_sql(sql, conn)
                conn.close()
                
                if df.empty:
                    print("⚠️ No results.")
                else:
                    print("\n📊 Result:")
                    print(df.to_markdown(index=False))
                    print("\n📝 Insight:")
                    print(self.summarize(q, df))
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    LocalAgent().run()