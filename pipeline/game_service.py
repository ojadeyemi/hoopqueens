"""
Game data service - handles all game-related database operations.
Separate from web framework concerns.
Uses modern SQLModel patterns with select() and session.exec().
"""

import os
import shutil
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from sqlalchemy import func
from sqlmodel import Session, SQLModel, col, create_engine, inspect, select

from db.models import Game, GameData, PlayerBoxScore, TeamBoxScore


class GameService:
    """Service for managing game data and database operations."""

    def __init__(self, database_url: str = "sqlite:///hoopqueens.db"):
        self.database_url = database_url
        self.database_path = database_url.replace("sqlite:///", "")
        self.snapshot_dir = Path("snapshots")
        self.engine = create_engine(database_url)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create required directories."""
        Path("db").mkdir(exist_ok=True)
        self.snapshot_dir.mkdir(exist_ok=True)

    def create_db_snapshot(self) -> str | None:
        """Create database backup before modifications."""
        if not os.path.exists(self.database_path):
            return None

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        snapshot_path = self.snapshot_dir / f"hoopqueens_{timestamp}.db"

        try:
            shutil.copy2(self.database_path, snapshot_path)
            print(f"Database snapshot created: {snapshot_path}")
            return str(snapshot_path)
        except Exception as e:
            print(f"Failed to create snapshot: {str(e)}")
            return None

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
            statement = select(Game).order_by(col(Game.date))
            return session.exec(statement).all()

    def get_game_by_id(self, game_id: int) -> Game | None:
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
        """Get player box scores for a game ordered by minutes played."""
        with Session(self.engine) as session:
            statement = select(PlayerBoxScore).where(PlayerBoxScore.game_id == game_id)
            return session.exec(statement).all()

    def get_player_box_scores_by_team(self, game_id: int, team_id: int) -> Sequence[PlayerBoxScore]:
        """Get player box scores for a specific team in a game."""
        with Session(self.engine) as session:
            statement = (
                select(PlayerBoxScore)
                .where(PlayerBoxScore.game_id == game_id, PlayerBoxScore.team_id == team_id)
                .order_by(col(PlayerBoxScore.minutes))
            )
            return session.exec(statement).all()

    def get_game_count(self) -> int:
        """Get total number of games in database."""
        with Session(self.engine) as session:
            statement = select(func.count(col(Game.id)))
            return session.exec(statement).one()

    def get_games_with_stats_count(self) -> int:
        """Get number of games that have box score data."""
        with Session(self.engine) as session:
            statement = select(func.count(func.distinct(TeamBoxScore.game_id)))
            return session.exec(statement).one()

    def validate_box_score_data(self, box_score_data: GameData) -> None:
        """Validate box score data structure."""
        if not box_score_data.team_box_scores or len(box_score_data.team_box_scores) != 2:
            raise ValueError("Must have exactly 2 team box scores")

        if not box_score_data.player_box_scores:
            raise ValueError("Player box scores missing")

        # Validate team IDs
        team_ids = {ts.team_id for ts in box_score_data.team_box_scores}
        player_team_ids = {ps.team_id for ps in box_score_data.player_box_scores}

        if not player_team_ids.issubset(team_ids):
            raise ValueError("Player team IDs don't match team box score IDs")

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
        snapshot_path = self.create_db_snapshot()

        try:
            with Session(self.engine) as session:
                # Save team box scores
                for team_data in box_score_data.team_box_scores:
                    team_dict = team_data.model_dump()
                    team_dict["game_id"] = game_id

                    # Validate team_id
                    try:
                        team_dict["team_id"] = int(team_dict["team_id"])
                    except (ValueError, TypeError):
                        raise ValueError(f"Invalid team_id: {team_dict['team_id']}")

                    session.add(TeamBoxScore(**team_dict))

                # Save player box scores
                for player_data in box_score_data.player_box_scores:
                    player_dict = player_data.model_dump()
                    player_dict["game_id"] = game_id

                    # Validate IDs
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
            # Log snapshot path for recovery
            if snapshot_path:
                print(f"Error occurred. Database snapshot available at: {snapshot_path}")
            raise RuntimeError(f"Failed to save game data: {str(e)}")

    def update_game_stats(self, game_id: int, box_score_data: GameData) -> str:
        """Update existing game statistics."""
        # First delete existing stats
        self.delete_game_stats(game_id)
        # Then save new stats
        return self.save_game_stats(game_id, box_score_data)

    def delete_game_stats(self, game_id: int) -> str:
        """Delete all box score data for a game."""
        snapshot_path = self.create_db_snapshot()

        try:
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

        except Exception as e:
            if snapshot_path:
                print(f"Error occurred. Database snapshot available at: {snapshot_path}")
            raise RuntimeError(f"Failed to delete game stats: {str(e)}")

    def get_recent_games(self, limit: int = 10) -> Sequence[Game]:
        """Get most recent games."""
        with Session(self.engine) as session:
            statement = select(Game).order_by(col(Game.date).desc()).limit(limit)
            return session.exec(statement).all()

    def get_games_without_stats(self) -> Sequence[Game]:
        """Get all games that don't have statistics yet."""
        with Session(self.engine) as session:
            # Subquery to get game IDs that have stats
            subquery = select(TeamBoxScore.game_id).distinct()

            # Main query to get games NOT in the subquery
            statement = select(Game).where(col(Game.id).notin_(subquery)).order_by(col(Game.date))
            return session.exec(statement).all()


# Factory function for dependency injection
def create_game_service(database_url: str = "sqlite:///hoopqueens.db") -> GameService:
    """Create and return a GameService instance."""
    service = GameService(database_url)
    service.create_tables()  # Ensure tables exist
    return service
