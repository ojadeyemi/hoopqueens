# 📊 Game Stats Database Overview

This SQL database is a SQLite file. [SQLite](https://builtin.com/data-science/sqlite) is a type of database that is lightweight and doesn’t require you to download or configure separate database software. It stores all the data in a single file.

The database powers the stats backend for hoopqueens and is organized around five core tables:

## 🔹 Core Tables

- **Game**
  - Stores metadata for each game (e.g. date, teams, final score, location).
- **TeamBoxScore**
  - Stores per-game team statistics (e.g. points from turnovers, paint points, shooting %, etc.).
- **PlayerBoxScore**

  - Stores individual player stats for each game (e.g. minutes, field goals, rebounds, assists, etc.).

- **Team**

  - Contains information about each team (e.g team name, coach_name, etc).

- **Players**
  - Contains information about each player (e.g player_name, jersey no, nationality, position,etc).

## 🔸 Views / Aggregated Tables

These are tables calulated and generated based on the above tables

- **Standings**
  - Aggregated from `Game` and `TeamBoxScore` tables to show team W-L records and rankings.
- **Leaderboard**
  - Highlights top-performing players across games (e.g. top scorers, rebounders).
- **CumulativeTeamStats**
  - Aggregates `TeamBoxScore` data across all games to show total and average team performance metrics.
- **CumulativePlayerStats**
  - Aggregates `PlayerBoxScore` stats across games to generate season totals and averages for each player.
