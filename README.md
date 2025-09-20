# 🏀 HoopQueens Box Score Pipeline

This project is for **HoopQueens** (a Canadian women's basketball league).
**Goal:** A data pipeline system that extracts box score data from PDFs and stores it in a database for analysis and reporting.

---

## 🚀 High-Level Overview

```
📄 PDF Files → 🔄 Processing Pipeline → 🗄️ SQLite Database
```

**Process Steps:**

1. **📤 Upload** - PDF files via Streamlit UI
2. **🤖 Extract** - Text extraction using OpenAI SDK
3. **✅ Validate** - Data validation with Pydantic
4. **💾 Store** - Save to SQLite using SQLModel
5. **🔄 Backup** - Automatic database backups

---

## 🗄️ Database Structure

Data is stored in a local `hoopqueens.db` SQLite file with the following structure:

- **Players** - Individual player information and statistics
- **Games** - Game metadata and results
- **Stats** - Detailed performance metrics

---

## 🧩 Key Libraries

- **Streamlit** – PDF upload and pipeline UI
- **OpenAI SDK** – PDF text extraction and processing
- **SQLModel** – Database ORM and data modeling
- **Pydantic** – Data validation and parsing
- **SQLite** – Local database storage
