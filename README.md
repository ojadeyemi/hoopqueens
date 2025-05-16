# 🏀 Project Overview

## 🎯 Goal

Build a fully automated pipeline for HoopQueens box‑score data:

1. **Ingest** raw PDF box scores
   - Upload or drop your game PDF into a designated folder or UI
2. **Extract & Validate** with an LLM
   - Use OpenAI to parse the PDF text into a well‑typed JSON schema
   - Validate against a Pydantic model to ensure data quality
3. **Persist** in SQLite
   - Store games, team and player box‑score tables, plus static team/player metadata
4. **Aggregate & Serve**
   - Auto‑generate views for standings, leaderboards and cumulative stats
   - Expose a FastAPI‑powered RESTful API so other apps or dashboards can consume the data
5. **(Optional) UI**
   - Provide a lightweight Streamlit front‑end for one‑click PDF uploads and status feedback

## Preqrequisites

- Install Python version >=3.10 . Go to their website [Download Python](https://www.python.org/downloads/)
- Create a virtual environment by running this command

  ```bash
  python -m venv .venv #Windows
  python3 -m venv .venv #Linux/Mac

  #Then activate it
  source .venv/Scripts/activate #Windows
  source .venv/bin/activate #Linux/Mac


  #verify it worked
  which python  #this should result to be inside the .venv folder
  ```
