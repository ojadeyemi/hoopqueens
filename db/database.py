import os
import shutil
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, inspect

from .models import Game, GameData, PlayerBoxScore, TeamBoxScore

# Database settings
DATABASE_URL = "sqlite:///db/basketball_stats.db"
DATABASE_PATH = "db/basketball_stats.db"
SNAPSHOT_DIR = "snapshots"
engine = create_engine(DATABASE_URL)


def ensure_directories():
    """Create needed directories if they don't exist"""
    Path("db").mkdir(exist_ok=True)
    Path(SNAPSHOT_DIR).mkdir(exist_ok=True)


def create_db_snapshot():
    """Save current database state before changes"""
    if not os.path.exists(DATABASE_PATH):
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_path = f"{SNAPSHOT_DIR}/basketball_stats_{timestamp}.db"

    try:
        shutil.copy2(DATABASE_PATH, snapshot_path)
        print(f"Database snapshot created: {snapshot_path}")
    except Exception as e:
        print(f"Failed to create snapshot: {str(e)}")


def create_tables():
    """Create database tables if they don't exist"""
    ensure_directories()

    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if not existing_tables:
            SQLModel.metadata.create_all(engine)
            print("Database tables created")
        else:
            print(f"Tables exist: {', '.join(existing_tables)}")
    except Exception as e:
        raise RuntimeError(f"Failed to create tables: {str(e)}")


def validate_game_data(game_data: GameData):
    """Validate data before saving"""
    if not game_data.game:
        raise ValueError("Game information missing")

    if not game_data.team_box_scores or len(game_data.team_box_scores) < 2:
        raise ValueError("Team box scores missing or incomplete")

    if not game_data.player_box_scores:
        raise ValueError("Player box scores missing")


def save_game_data(game_data: GameData):
    """Save game data to database with validation"""
    validate_game_data(game_data)
    create_db_snapshot()

    try:
        with Session(engine) as session:
            # Add game
            game = Game(**game_data.game.model_dump())
            session.add(game)
            session.flush()
            game_id = game.id

            # Add team box scores
            for team_data in game_data.team_box_scores:
                team_data_dict = team_data.model_dump()
                team_data_dict["game_id"] = game_id
                try:
                    team_data_dict["team_id"] = int(team_data_dict["team_id"])
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid team_id: {team_data_dict['team_id']}")

                team_box_score = TeamBoxScore(**team_data_dict)
                session.add(team_box_score)

            # Add player box scores
            for player_data in game_data.player_box_scores:
                player_data_dict = player_data.model_dump()
                player_data_dict["game_id"] = game_id
                try:
                    player_data_dict["team_id"] = int(player_data_dict["team_id"])
                    player_data_dict["player_id"] = int(player_data_dict["player_id"])
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Invalid ID: team_id={player_data_dict['team_id']}, player_id={player_data_dict['player_id']}"
                    )

                player_box_score = PlayerBoxScore(**player_data_dict)
                session.add(player_box_score)

            session.commit()
            print(f"Game data saved (Game ID: {game_id})")
    except Exception as e:
        raise RuntimeError(f"Failed to save game data: {str(e)}")
