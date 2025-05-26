# 🏀 HoopQueens Box Score Pipeline (Dev Guide)

Welcome! This project is for **HoopQueens** (a Canadian women's basketball league).  
**Goal:** Build a system to extract box score data from PDFs, save it to a database, and serve it via a FastAPI backend for use by any app, dashboard, or service.

---

## 🚀 High-Level Overview

- **PDFs → Pipeline → Database → FastAPI API**
- **Pipeline logic is already handled:**
  - Upload PDF via Streamlit UI
  - Extract text (OpenAI SDK)
  - Validate data (Pydantic)
  - Save to SQLite (SQLModel)
  - Automatic DB backups
- **Your focus:**
  - Build and test FastAPI endpoints to serve the data from the database

---

## 📝 Project To-Do List

| Task                    | Status   | Notes                                    |
| ----------------------- | -------- | ---------------------------------------- |
| PDF upload & extraction | ✅ Done  | Handled by Streamlit & OpenAI SDK        |
| Data validation         | ✅ Done  | Handled by Pydantic                      |
| Save to SQLite DB       | ✅ Done  | Handled by SQLModel                      |
| Build FastAPI endpoints | ⬜ To Do | Serve data from DB                       |
| Data API design         | ⬜ To Do | Plan endpoints for players, games, stats |
| API response validation | ⬜ To Do | Use Pydantic models                      |
| Testing endpoints       | ⬜ To Do | Use Swagger UI (built into FastAPI)      |
| Deployment              | ⬜ To Do | Prepare for production use               |
| Documentation           | ⬜ To Do | Keep this README updated                 |

---

## 🛠️ Prerequisites

1. **Clone this repo**

   ```bash
   # first clone the repo to your local computer
   git clone https://github.com/ojadeyemi/hoopqueens.git

   # then navigate to the folder
   cd hoopqueens
   ```

2. **Python 3.10+**  
   Check your Python version:

   ```bash
   python --version
   # Should output: Python 3.10.x or higher
   ```

3. **Create & activate a virtual environment**

   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Mac/Linux:
   source .venv/bin/activate
   ```

   Confirm you're using the venv:

   ```bash
   which python  # Should show path inside .venv
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🗄️ Database (SQLite)

- Data is stored in a local `hoopqueens.sqlite` file.
- **SQLModel** is used as an ORM (built on SQLAlchemy).
- You can query data using either **raw SQL** or **SQLModel**.

**Raw SQL Example:**

```python
import sqlite3

conn = sqlite3.connect("hoopqueens.sqlite")
cursor = conn.cursor()
cursor.execute("SELECT name, points FROM player")
players = cursor.fetchall()
print(players)
conn.close()
```

**SQLModel Example:**

```python
from sqlmodel import SQLModel, Session, select, create_engine, Field

engine = create_engine("sqlite:///hoopqueens.sqlite")

class Player(SQLModel, table=True):
      id: int | None = Field(default=None, primary_key=True)
      name: str
      points: int

with Session(engine) as session:
      players = session.exec(select(Player)).all()
      print(players)
```

- [Learn more about SQLModel](https://sqlmodel.tiangolo.com)
- [Learn more about SQLite](https://www.sqlite.org/index.html)

---

## ⚡ FastAPI: Serving the Data

You will build endpoints to serve data from the database.  
**Swagger UI** (auto-generated docs at `/docs`) is used for testing your API—no need for Postman or httpie.

**Basic FastAPI Example:**

```python
from fastapi import FastAPI
from sqlmodel import Session, select

app = FastAPI()

@app.get("/players")
def get_players():
      with Session(engine) as session:
            players = session.exec(select(Player)).all()
            return players
```

- Add more endpoints as needed (e.g., `/games`, `/stats`)
- Use Pydantic models for response validation

- [FastAPI Docs](https://fastapi.tiangolo.com/learn/)
- [Pydantic Docs](https://docs.pydantic.dev/)

---

## 🧩 Key Libraries

- **FastAPI** – Build APIs quickly
- **SQLModel** – Easy database access
- **Pydantic** – Data validation
- **Streamlit** – (Already set up) for PDF upload and pipeline UI
- **OpenAI SDK** – (Already set up) for PDF text extraction

---

## 💡 Tips

- The pipeline and database setup are ready—focus on API logic.
- Use SQLModel or raw SQL to query data, FastAPI to expose endpoints.
- Test endpoints using the built-in Swagger UI (`/docs`).
- Automatic DB backups are handled.
- This API will be used by other apps, dashboards, and anyone needing HoopQueens data.

---

**Next steps:**  
Explore the database, then build and test your FastAPI endpoints to serve the data to a simple website!
Go to [app folder](app/README.md)
