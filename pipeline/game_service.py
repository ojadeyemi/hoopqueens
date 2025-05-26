"""
Game data service - handles all game-related database operations.
Separate from web framework concerns.
Uses modern SQLModel patterns with select() and session.exec().
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from sqlalchemy import func
from sqlmodel import Session, SQLModel, create_engine, inspect, select

from db.models import Game, GameData, PlayerBoxScore, TeamBoxScore


class GameService:
    """Service for managing game data and database operations."""

    def __init__(self, database_url: str = "sqlite:///hoopqueens.sqlite"):
        self.database_url = database_url
        self.database_path = database_url.replace("sqlite:///", "")
        self.snapshot_dir = "snapshots"
        self.engine = create_engine(database_url)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create required directories."""
        Path("db").mkdir(exist_ok=True)
        Path(self.snapshot_dir).mkdir(exist_ok=True)

    def create_db_snapshot(self) -> None:
        """Create database backup before modifications."""
        if not os.path.exists(self.database_path):
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        snapshot_path = f"{self.snapshot_dir}/hoopqueens_{timestamp}.sqlite"

        try:
            shutil.copy2(self.database_path, snapshot_path)
            print(f"Database snapshot created: {snapshot_path}")
        except Exception as e:
            print(f"Failed to create snapshot: {str(e)}")

    def create_tables(self) -> None:
        """Initialize database tables."""
        try:
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()

            if not existing_tables:
                SQLModel.metadata.create_all(self.engine)
                print("Database tables created")
        except Exception as e:
            raise RuntimeError(f"Failed to create tables: {str(e)}")

    def get_all_games(self) -> Sequence[Game]:
        """Retrieve all games ordered by date."""
        with Session(self.engine) as session:
            statement = select(Game).order_by(Game.date)  # type: ignore
            return session.exec(statement).all()

    def get_game_by_id(self, game_id: int) -> Optional[Game]:
        """Get a specific game by ID."""
        with Session(self.engine) as session:
            statement = select(Game).where(Game.id == game_id)
            return session.exec(statement).first()

    def game_has_stats(self, game_id: int) -> bool:
        """Check if game already has box score data."""
        with Session(self.engine) as session:
            statement = select(TeamBoxScore).where(TeamBoxScore.game_id == game_id)
            existing_scores = session.exec(statement).first()
            return existing_scores is not None

    def get_team_box_scores(self, game_id: int) -> Sequence[TeamBoxScore]:
        """Get team box scores for a game."""
        with Session(self.engine) as session:
            statement = select(TeamBoxScore).where(TeamBoxScore.game_id == game_id)
            return session.exec(statement).all()

    def get_player_box_scores(self, game_id: int) -> Sequence[PlayerBoxScore]:
        """Get player box scores for a game."""
        with Session(self.engine) as session:
            statement = select(PlayerBoxScore).where(PlayerBoxScore.game_id == game_id)
            return session.exec(statement).all()

    def get_player_box_scores_by_team(self, game_id: int, team_id: int) -> Sequence[PlayerBoxScore]:
        """Get player box scores for a specific team in a game."""
        with Session(self.engine) as session:
            statement = (
                select(PlayerBoxScore)
                .where(PlayerBoxScore.game_id == game_id, PlayerBoxScore.team_id == team_id)
                .order_by(PlayerBoxScore.minutes)
            )
            return session.exec(statement).all()

    def get_game_count(self) -> int:
        """Get total number of games in database."""
        with Session(self.engine) as session:
            statement = select(func.count(Game.id))
            return session.exec(statement).one()

    def get_games_with_stats_count(self) -> int:
        """Get number of games that have box score data."""
        with Session(self.engine) as session:
            statement = select(func.count(func.distinct(TeamBoxScore.game_id)))
            return session.exec(statement).one()

    def validate_box_score_data(self, box_score_data: GameData) -> None:
        """Validate box score data structure."""
        if not box_score_data.team_box_scores or len(box_score_data.team_box_scores) < 2:
            raise ValueError("Team box scores missing or incomplete")
        if not box_score_data.player_box_scores:
            raise ValueError("Player box scores missing")

    def save_game_stats(self, game_id: int, box_score_data: GameData) -> str:
        """
        Save box score data for an existing game.
        Returns status message.
        """
        # Validate input data
        self.validate_box_score_data(box_score_data)

        # Check if game exists
        game = self.get_game_by_id(game_id)
        if not game:
            raise ValueError(f"Game with ID {game_id} not found")

        # Check if stats already exist
        if self.game_has_stats(game_id):
            return "Game already has statistics. No changes made."

        # Create backup
        self.create_db_snapshot()

        try:
            with Session(self.engine) as session:
                # Save team box scores
                for team_data in box_score_data.team_box_scores:
                    team_dict = team_data.model_dump()
                    team_dict["game_id"] = game_id

                    try:
                        team_dict["team_id"] = int(team_dict["team_id"])
                    except (ValueError, TypeError):
                        raise ValueError(f"Invalid team_id: {team_dict['team_id']}")

                    session.add(TeamBoxScore(**team_dict))

                # Save player box scores
                for player_data in box_score_data.player_box_scores:
                    player_dict = player_data.model_dump()
                    player_dict["game_id"] = game_id

                    try:
                        player_dict["team_id"] = int(player_dict["team_id"])
                        player_dict["player_id"] = int(player_dict["player_id"])
                    except (ValueError, TypeError):
                        raise ValueError(
                            f"Invalid ID: team={player_dict['team_id']}, player={player_dict['player_id']}"
                        )

                    session.add(PlayerBoxScore(**player_dict))

                session.commit()
                message = f"Box score data saved for Game ID: {game_id}"
                print(message)
                return message

        except Exception as e:
            raise RuntimeError(f"Failed to save game data: {str(e)}")

    def delete_game_stats(self, game_id: int) -> str:
        """Delete all box score data for a game."""
        with Session(self.engine) as session:
            # Delete player box scores
            statement = select(PlayerBoxScore).where(PlayerBoxScore.game_id == game_id)
            player_scores = session.exec(statement).all()
            for score in player_scores:
                session.delete(score)

            # Delete team box scores
            statement = select(TeamBoxScore).where(TeamBoxScore.game_id == game_id)
            team_scores = session.exec(statement).all()
            for score in team_scores:
                session.delete(score)

            session.commit()
            return f"Deleted stats for game {game_id}"

    def get_recent_games(self, limit: int = 10) -> Sequence[Game]:
        """Get most recent games."""
        with Session(self.engine) as session:
            statement = select(Game).order_by(Game.date).limit(limit)
            return session.exec(statement).all()


# Factory function for dependency injection
def create_game_service(database_url: str = "sqlite:///hoopqueens.sqlite") -> GameService:
    """Create and return a GameService instance."""
    service = GameService(database_url)
    service.create_tables()  # Ensure tables exist
    return service


# Default instance for simple usage
game_service = create_game_service()


# Example usage
"""
# Basic usage
service = create_game_service()

# Get all games
games = service.get_all_games()
for game in games:
    print(f"Game {game.game_number}: {game.date}")

# Get specific game
game = service.get_game_by_id(1)
if game:
    print(f"Found game: {game.location}")

# Check if game has stats
has_stats = service.game_has_stats(1)
print(f"Game has stats: {has_stats}")

# Get box scores
team_scores = service.get_team_box_scores(1)
player_scores = service.get_player_box_scores(1)

# Get counts
total_games = service.get_game_count()
games_with_stats = service.get_games_with_stats_count()
print(f"Total games: {total_games}, With stats: {games_with_stats}")

# Search games
recent_games = service.get_recent_games(5)
"""
