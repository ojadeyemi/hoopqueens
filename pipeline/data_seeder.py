"""
Data seeding service for initial database population.
Supports JSON files, Python dicts, and environment-specific data.
Uses modern SQLModel with select() and session.exec() patterns.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from db.models import Game, Player, PlayerBoxScore, Team, TeamBoxScore

from .game_service import GameService


class DataSeeder:
    """Service for seeding initial data into the database."""

    def __init__(self, game_service: GameService):
        self.game_service = game_service
        self.engine = game_service.engine

    def seed_from_file(self, file_path: str) -> str:
        """Load and seed data from JSON file."""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"Data file not found: {file_path}")

            with open(file_path_obj, "r", encoding="utf-8") as f:
                data = json.load(f)

            return self.seed_from_dict(data)

        except json.JSONDecodeError as e:
            return f"Invalid JSON format: {str(e)}"
        except Exception as e:
            return f"Error loading file: {str(e)}"

    def seed_from_dict(self, data_dict: Dict[str, Any]) -> str:
        """Seed database from dictionary data."""
        try:
            with Session(self.engine) as session:
                stats = {"teams_added": 0, "players_added": 0, "games_added": 0, "teams_skipped": 0, "games_skipped": 0}

                # Process teams first
                if "teams" in data_dict:
                    stats.update(self._process_teams(session, data_dict["teams"]))

                # Process games
                if "games" in data_dict:
                    stats.update(self._process_games(session, data_dict["games"]))

                session.commit()
                return self._format_result_message(stats)

        except IntegrityError as e:
            session.rollback()
            return f"Database integrity error: {str(e)}"
        except Exception as e:
            session.rollback()
            return f"Seeding failed: {str(e)}"

    def _process_teams(self, session: Session, teams_data: List[Dict]) -> Dict[str, int]:
        """Process team and player data."""
        teams_added = 0
        players_added = 0
        teams_skipped = 0

        for team_data in teams_data:
            # Check if team already exists using modern SQLModel
            statement = select(Team).where(Team.name == team_data["name"])
            existing_team = session.exec(statement).first()

            if existing_team:
                teams_skipped += 1
                continue

            # Create new team
            team = Team(
                name=team_data["name"],
                abbreviation=team_data["abbreviation"],
                bio=team_data.get("bio", ""),
                coach=team_data.get("coach", ""),
                general_manager=team_data.get("general_manager", ""),
            )
            session.add(team)
            session.flush()  # Get team ID
            teams_added += 1

            # Add players for this team
            if "players" in team_data:
                for player_data in team_data["players"]:
                    # Check if player already exists using modern SQLModel
                    statement = select(Player).where(Player.name == player_data["name"], Player.team_id == team.id)
                    existing_player = session.exec(statement).first()

                    if existing_player:
                        continue

                    player = Player(
                        team_id=team.id,  # type: ignore
                        name=player_data["name"],
                        jersey_number=player_data["jersey_number"],
                        position=player_data["position"],
                        school=player_data.get("school", ""),
                        birth_date=self._parse_date(player_data["birth_date"]),  # type: ignore
                        nationality=player_data.get("nationality", ""),
                    )
                    session.add(player)
                    players_added += 1

        return {"teams_added": teams_added, "players_added": players_added, "teams_skipped": teams_skipped}

    def _process_games(self, session: Session, games_data: List[Dict]) -> Dict[str, int]:
        """Process game data."""
        games_added = 0
        games_skipped = 0

        for game_data in games_data:
            # Check if game already exists using modern SQLModel
            statement = select(Game).where(Game.game_number == game_data["game_number"])
            existing_game = session.exec(statement).first()

            if existing_game:
                games_skipped += 1
                continue

            game = Game(
                game_number=game_data["game_number"],
                date=self._parse_date(game_data["date"]),
                start_time=self._parse_datetime(game_data["start_time"]),
                location=game_data["location"],
                attendance=game_data.get("attendance", 0),
            )
            session.add(game)
            games_added += 1

        return {"games_added": games_added, "games_skipped": games_skipped}

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object."""
        if isinstance(date_str, datetime):
            return date_str

        # Try common date formats
        formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        raise ValueError(f"Unable to parse date: {date_str}")

    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Parse datetime string to datetime object."""
        if isinstance(datetime_str, datetime):
            return datetime_str

        # Try common datetime formats
        formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"]

        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue

        # Fallback: try to parse as date and set time to noon
        try:
            date_part = self._parse_date(datetime_str.split()[0])
            return date_part.replace(hour=12)
        except Exception as e:
            print(f"Warning: {str(e)} - using noon as default time for date {datetime_str}")
            pass

        raise ValueError(f"Unable to parse datetime: {datetime_str}")

    def _format_result_message(self, stats: Dict[str, int]) -> str:
        """Format seeding result message."""
        parts = []

        if stats["teams_added"]:
            parts.append(f"{stats['teams_added']} teams")
        if stats["players_added"]:
            parts.append(f"{stats['players_added']} players")
        if stats["games_added"]:
            parts.append(f"{stats['games_added']} games")

        message = f"Added: {', '.join(parts)}" if parts else "No new data added"

        skipped = []
        if stats.get("teams_skipped"):
            skipped.append(f"{stats['teams_skipped']} teams")
        if stats.get("games_skipped"):
            skipped.append(f"{stats['games_skipped']} games")

        if skipped:
            message += f" | Skipped (already exist): {', '.join(skipped)}"

        return message

    def reset_database(self) -> str:
        """Clear all data from database (use with caution!)."""
        try:
            with Session(self.engine) as session:
                # Delete in order to respect foreign keys
                # Using modern SQLModel delete pattern
                session.exec(select(PlayerBoxScore)).all()
                for obj in session.exec(select(PlayerBoxScore)).all():
                    session.delete(obj)

                for obj in session.exec(select(TeamBoxScore)).all():
                    session.delete(obj)

                for obj in session.exec(select(Player)).all():
                    session.delete(obj)

                for obj in session.exec(select(Game)).all():
                    session.delete(obj)

                for obj in session.exec(select(Team)).all():
                    session.delete(obj)

                session.commit()

            return "Database reset successfully"
        except Exception as e:
            return f"Reset failed: {str(e)}"

    def get_database_stats(self) -> Dict[str, int]:
        """Get current database statistics using modern SQLModel."""
        with Session(self.engine) as session:
            # Count using modern SQLModel pattern
            teams_count = len(session.exec(select(Team)).all())
            players_count = len(session.exec(select(Player)).all())
            games_count = len(session.exec(select(Game)).all())

            # Handle optional models
            team_box_scores_count = 0
            player_box_scores_count = 0

            if "TeamBoxScore" in globals():
                team_box_scores_count = len(session.exec(select(TeamBoxScore)).all())

            if "PlayerBoxScore" in globals():
                player_box_scores_count = len(session.exec(select(PlayerBoxScore)).all())

            return {
                "teams": teams_count,
                "players": players_count,
                "games": games_count,
                "team_box_scores": team_box_scores_count,
                "player_box_scores": player_box_scores_count,
            }


def create_data_seeder(game_service: GameService) -> DataSeeder:
    """Create and return a DataSeeder instance."""
    return DataSeeder(game_service)


# CLI interface for seeding
def main():
    """Command line interface for data seeding."""
    import argparse

    from .game_service import create_game_service

    parser = argparse.ArgumentParser(description="Seed database with initial data")
    parser.add_argument("--file", help="JSON file with seed data")
    parser.add_argument("--reset", action="store_true", help="Reset database before seeding")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")

    args = parser.parse_args()

    game_service = create_game_service()
    seeder = create_data_seeder(game_service)

    if args.stats:
        stats = seeder.get_database_stats()
        print("Database Statistics:")
        for table, count in stats.items():
            print(f"  {table}: {count}")
        return

    if args.reset:
        result = seeder.reset_database()
        print(result)

    if args.file:
        result = seeder.seed_from_file(args.file)
        print(result)
    else:
        print("No action specified. Use --help for options.")


if __name__ == "__main__":
    main()


# Example usage:
"""
# Create a game service and seeder
from services.game_service import create_game_service
from services.data_seeder import create_data_seeder

game_service = create_game_service()
seeder = create_data_seeder(game_service)

# Example 1: Seed from dictionary
data = {
    "teams": [
        {
            "name": "Lakers",
            "abbreviation": "LAL",
            "coach": "Coach Smith",
            "players": [
                {
                    "name": "Player One",
                    "jersey_number": 23,
                    "position": "PG",
                    "birth_date": "1990-01-01"
                }
            ]
        }
    ],
    "games": [
        {
            "game_number": 1,
            "date": "2024-01-01",
            "start_time": "2024-01-01 19:00",
            "location": "Arena Name",
            "attendance": 15000
        }
    ]
}

result = seeder.seed_from_dict(data)
print(result)

# Example 2: Seed from JSON file
result = seeder.seed_from_file("path/to/seed_data.json")
print(result)

# Example 3: Get database statistics
stats = seeder.get_database_stats()
print(stats)

# Example 4: Reset database (careful!)
# result = seeder.reset_database()
# print(result)
"""
