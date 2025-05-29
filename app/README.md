# Project Overview

This project contains both the API and web UI logic for HoopQueens.

- The API is built with **FastAPI** and lives in the `api` folder.
- The web UI (HTML, CSS, JS) is in the `web` folder.

The database is a SQLite file:  
[`../hoopqueens.sqlite`](../hoopqueens.sqlite)

## Folder Structure

```
/api   # FastAPI backend code
/web   # Simple frontend (HTML, CSS, JS)
```

## How It Works

- The backend API handles data and business logic.
- The frontend lets users interact with the app in their browser.

## Example FastAPI Endpoint

A simple example endpoint in FastAPI (`api/main.py`):

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
def read_hello():
    return {"message": "Hello, world!"}
```

## API Documentation

When you run the FastAPI server, you can view and test the API docs at:

- [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
- [http://localhost:8000/redoc](http://localhost:8000/redoc) (ReDoc)

Just open one of these links in your browser after starting the server.

## TODO: Create FastAPI endpoints for the following

- [ ] **Standings**

  - Team wins, losses, win percentage
  - Points for/against
  - Streaks, games played

- [ ] **Leaderboards**

  - Top scorers (players by total/average points)
  - Top rebounders, assist leaders, steals, blocks, efficiency, etc.
  - Team leaders in various stats

- [ ] **Team Stats**

  - Per-game and season totals/averages (from `TeamBoxScore`)
  - Shooting percentages, rebounds, assists, turnovers, etc.
  - Advanced stats: points in paint, fast break points, bench points, etc.

- [ ] **Player Stats**

  - Per-game and season totals/averages (from `PlayerBoxScore`)
  - Shooting, rebounds, assists, turnovers, steals, blocks, fouls, efficiency, points

- [ ] **Team Info**

  - Name, abbreviation, bio/history, coach, general manager
  - Roster (list of players)

- [ ] **Player Info**
  - Name, jersey number, position, school, birth date, nationality
  - Team affiliation

## Viewing the Database

To view the data in `hoopqueens.sqlite`, install the [SQLite Viewer extension for VS Code](https://marketplace.visualstudio.com/items?itemName=alexcvzz.vscode-sqlite). After installing, open VS Code, find the `hoopqueens.sqlite` file in your project, and click on it to browse and inspect the database tables and data.
