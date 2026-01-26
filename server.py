from fastmcp import FastMCP
import sqlite3
import pandas as pd
from pathlib import Path

# Initialize the MCP Server
mcp = FastMCP("HERD-Data-Server")

# Path to the database we built in step 2
DB_PATH = Path(__file__).parent / "herd.db"

@mcp.tool()
def query_herd_data(sql_query: str) -> str:
    """
    Executes a SQL query on the NSF HERD Higher Education R&D Survey database.
    
    The table name is 'institutions'.
    Schema:
    - inst_id (TEXT): Unique ID of the school
    - name (TEXT): School name (e.g., 'University of North Texas')
    - city (TEXT), state (TEXT), year (INTEGER)
    - federal (INTEGER): Federal R&D expenditures (in dollars)
    - total_rd (INTEGER): Total R&D expenditures (in dollars)
    """
    # Security: Prevent modification
    if any(cmd in sql_query.upper() for cmd in ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER"]):
        return "Error: Read-only access. Only SELECT queries are allowed."

    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(sql_query, conn)
        conn.close()
        return df.to_markdown(index=False)
    except Exception as e:
        return f"SQL Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()