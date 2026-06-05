# HoopQueens Box Score Pipeline

> **Archived.** This repo is preserved as a public reference. The pipeline has since been extended to support multiple leagues with Postgres as the primary database.

---

Data pipeline for **HoopQueens**, a Canadian women's basketball league. Extracts box score statistics from uploaded images/PDFs using OpenAI's vision API, stores them in SQLite, and exposes them via a FastAPI REST API.

## What it does

1. **Upload** — box score image or PDF via Streamlit UI
2. **Parse** — OpenAI `gpt-4.1` extracts structured stats
3. **Review** — editable table to correct before saving
4. **Store** — saves to SQLite via SQLModel
5. **Serve** — FastAPI read-only API over the same DB

## Stack

- Python 3.11+, SQLModel, SQLite
- OpenAI SDK (structured outputs)
- Streamlit (pipeline UI)
- FastAPI (read API)

## Running locally

```bash
pip install -r requirements.txt

# Pipeline UI (from pipeline/ directory)
cd pipeline && streamlit run app.py

# API (from app/ directory)
cd app && fastapi dev main.py

# DB management
python manage_data.py seed      # seed from data/seed_data.json
python manage_data.py stats     # row counts
python manage_data.py reset     # wipe all data
```

**Required env var:** `OPENAI_API_KEY`

## Seasons

- 2025 season: 9 games, full box scores
- 2026 season: 9 games scheduled, box scores TBD
