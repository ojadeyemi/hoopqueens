import os
import shutil
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, inspect, select

from .models import Game, GameData, PlayerBoxScore, TeamBoxScore

DATABASE_URL = "sqlite:///hoopqueens.sqlite"
DATABASE_PATH = "hoopqueens.sqlite"
SNAPSHOT_DIR = "snapshots"
engine = create_engine(DATABASE_URL)


def ensure_directories():
    """Create needed directories"""
    Path("db").mkdir(exist_ok=True)
    Path(SNAPSHOT_DIR).mkdir(exist_ok=True)


def create_db_snapshot():
    """Save database state before changes"""
    if not os.path.exists(DATABASE_PATH):
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    snapshot_path = f"{SNAPSHOT_DIR}/hoopqueens_{timestamp}.sqlite"

    try:
        shutil.copy2(DATABASE_PATH, snapshot_path)
        print(f"Database snapshot created: {snapshot_path}")
    except Exception as e:
        print(f"Failed to create snapshot: {str(e)}")


def create_tables():
    """Create database tables"""
    ensure_directories()

    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if not existing_tables:
            SQLModel.metadata.create_all(engine)
            print("Database tables created")
    except Exception as e:
        raise RuntimeError(f"Failed to create tables: {str(e)}")


def validate_box_score_data(box_score_data: GameData):
    """Validate box score data before saving"""
    if not box_score_data.team_box_scores or len(box_score_data.team_box_scores) < 2:
        raise ValueError("Team box scores missing or incomplete")
    if not box_score_data.player_box_scores:
        raise ValueError("Player box scores missing")


def parse_date(date_str):
    """Parse date in multiple formats"""
    formats = [
        "%Y-%m-%d",
        "%a %d %b %Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse date: {date_str}")


def save_game_data(sql_engine, game_id: int, box_score_data: GameData):
    """Save box score data to an existing game in the database"""
    validate_box_score_data(box_score_data)
    create_db_snapshot()

    try:
        with Session(sql_engine) as session:
            # Get existing game or raise error
            game = session.exec(select(Game).where(Game.id == game_id)).first()
            if not game:
                raise ValueError(f"Game with ID {game_id} not found")

            # Check if box scores already exist
            existing_team_scores = session.exec(select(TeamBoxScore).where(TeamBoxScore.game_id == game_id)).first()

            if existing_team_scores:
                return "Game already has statistics. No changes made."

            # Add new team box scores
            for team_data in box_score_data.team_box_scores:
                team_data_dict = team_data.model_dump()
                team_data_dict["game_id"] = game_id
                try:
                    team_data_dict["team_id"] = int(team_data_dict["team_id"])
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid team_id: {team_data_dict['team_id']}")
                session.add(TeamBoxScore(**team_data_dict))

            # Add new player box scores
            for player_data in box_score_data.player_box_scores:
                player_data_dict = player_data.model_dump()
                player_data_dict["game_id"] = game_id
                try:
                    player_data_dict["team_id"] = int(player_data_dict["team_id"])
                    player_data_dict["player_id"] = int(player_data_dict["player_id"])
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Invalid ID: team={player_data_dict['team_id']}, player={player_data_dict['player_id']}"
                    )
                session.add(PlayerBoxScore(**player_data_dict))

            session.commit()
            print(f"Box score data saved for Game ID: {game_id}")
            return f"Box score data saved for Game ID: {game_id}"
    except Exception as e:
        raise RuntimeError(f"Failed to save game data: {str(e)}")
