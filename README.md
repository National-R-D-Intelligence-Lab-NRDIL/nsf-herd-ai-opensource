# NSF HERD Survey - MCP Analysis Tools

This project provides a set of tools to download, process, and analyze the **National Science Foundation (NSF) Higher Education Research and Development (HERD)** survey data (2010–2024).

It uses the **Model Context Protocol (MCP)** to allow AI agents to query this data using natural language.

## 📋 Overview

The HERD survey collects data on R&D expenditures at U.S. colleges and universities. This project:
- Downloads raw survey data from the NSF website
- Processes and normalizes the data across multiple years
- Builds a SQLite database for efficient querying
- Provides an MCP server interface for AI-powered data analysis

## 🚀 Quick Start

### Prerequisites

1. **Install `uv`** (The modern Python package manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source $HOME/.local/bin/env
   ```

2. **Clone this repository**:
   ```bash
   git clone <your-repo-url>
   cd herd_ai
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

### Setup & Execution

1. **Generate the mapping file** (maps survey fields to database columns):
   ```bash
   uv run generate_mapping.py
   ```

2. **Build the database** (downloads data, processes it, and creates SQLite DB):
   ```bash
   uv run etl.py
   ```

3. **Run the MCP server** (for testing / tool access):
   ```bash
   uv run server.py
   ```

4. **Run the local natural-language agent** (uses Ollama by default):
   ```bash
   uv run local_agent.py
   ```

## 📁 Project Structure

- **`downloader.py`** - Handles fetching the raw CSV zip files from the NSF website
- **`generate_mapping.py`** - Scans raw data to map thousands of sub-fields (e.g., "Aerospace Engineering") to database keys
- **`etl.py`** - The core engine. Downloads data → Maps it → Builds the SQL Database
- **`server.py`** - The MCP Interface. Connects AI to the Database
- **`local_agent.py`** - Local agent using Ollama for natural language queries
- **`analyze_schema.py`** - Optional utility to debug if specific fields are missing

## 🗄️ Database Schema

The main table is `institutions` with the following schema:
- `inst_id` (TEXT): Unique ID of the school
- `name` (TEXT): School name (e.g., 'University of North Texas')
- `city` (TEXT): City location
- `state` (TEXT): State location
- `year` (INTEGER): Survey year
- `federal` (INTEGER): Federal R&D expenditures (in dollars)
- `total_rd` (INTEGER): Total R&D expenditures (in dollars)

## 🔧 Usage

### MCP Server

The MCP server provides a `query_herd_data` tool that accepts SQL queries:

```python
# Example query
SELECT name, state, year, total_rd
FROM institutions
WHERE state = 'CA' AND year = 2023
ORDER BY total_rd DESC
LIMIT 10
```

**Note**: The server enforces read-only access - only SELECT queries are allowed.

### Local Agent

For local development with Ollama:

```bash
uv run local_agent.py
```

Then ask questions in natural language, and the agent will convert them to SQL queries.

## 🧪 Open Source R&D Goal

Replicate the functionality of a Gemini-based MVP using open source models (Llama, Mistral, etc.) to evaluate performance and privacy trade-offs. This repo already includes a local agent path (`local_agent.py`) and can evolve to support additional runtimes (e.g., vLLM / HuggingFace).

## 📝 Notes

- Money columns are stored in **thousands** of dollars
- The database is read-only through the MCP interface
- Raw CSV files are stored in `data/raw/` but are excluded from git (see `.gitignore`)

## 🤝 Contributing

1. **Local setup**
   - Ensure `.streamlit/secrets.toml` is ignored (it is in `.gitignore`).
   - Use your own API keys / local model endpoints for testing.
2. **Development**
   - Always create a new branch for work: `git checkout -b feature-name`
   - Do NOT push directly to `main`.
3. **Review process**
   - Push your branch to GitHub.
   - Open a Pull Request (PR).
   - Tag @Kalyan8358 for review.
   - Do NOT merge the PR until it has been reviewed and discussed.

## 📄 License

[Add your license here]
