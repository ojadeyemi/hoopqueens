from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from db.database import create_tables, engine
from db.models import Game, Player, Team

# This is fake for now
INIT_DATA = {
    "teams": [
        {
            "name": "York",
            "abbreviation": "YKN",
            "bio": "York university basketball team established in 2020",
            "coach": "Coach York",
            "general_manager": "York GM",
            "players": [
                {
                    "name": "Bill Bill",
                    "jersey_number": 1,
                    "position": "G",
                    "school": "York University",
                    "birth_date": "1998-05-15",
                    "nationality": "Canada",
                },
                {
                    "name": "John Man",
                    "jersey_number": 3,
                    "position": "F",
                    "school": "York University",
                    "birth_date": "1999-03-22",
                    "nationality": "Canada",
                },
                {
                    "name": "F F",
                    "jersey_number": 9,
                    "position": "F",
                    "school": "York University",
                    "birth_date": "2000-08-10",
                    "nationality": "Canada",
                },
                {
                    "name": "C C",
                    "jersey_number": 10,
                    "position": "C",
                    "school": "York University",
                    "birth_date": "1997-11-30",
                    "nationality": "Canada",
                },
                {
                    "name": "VV",
                    "jersey_number": 11,
                    "position": "G",
                    "school": "York University",
                    "birth_date": "2001-01-05",
                    "nationality": "Canada",
                },
            ],
        },
        {
            "name": "Union",
            "abbreviation": "UNN",
            "bio": "Union university basketball team established in 2019",
            "coach": "Coaches Union",
            "general_manager": "Union GM",
            "players": [
                {
                    "name": "UK Joey",
                    "jersey_number": 4,
                    "position": "G",
                    "school": "Union College",
                    "birth_date": "1998-07-12",
                    "nationality": "Canada",
                },
                {
                    "name": "UK Juh",
                    "jersey_number": 5,
                    "position": "F",
                    "school": "Union College",
                    "birth_date": "1999-09-08",
                    "nationality": "Canada",
                },
                {
                    "name": "B B",
                    "jersey_number": 6,
                    "position": "F",
                    "school": "Union College",
                    "birth_date": "2000-04-17",
                    "nationality": "Canada",
                },
                {
                    "name": "N N",
                    "jersey_number": 7,
                    "position": "C",
                    "school": "Union College",
                    "birth_date": "1997-12-03",
                    "nationality": "Canada",
                },
                {
                    "name": "R R",
                    "jersey_number": 8,
                    "position": "G",
                    "school": "Union College",
                    "birth_date": "2001-02-28",
                    "nationality": "Canada",
                },
            ],
        },
    ],
    "games": [
        {
            "game_number": 1,
            "date": "2025-05-03",
            "start_time": "2025-05-03 14:30:00",
            "location": "UofT Gymnasium",
            "attendance": 1200,
        },
        {
            "game_number": 2,
            "date": "2025-05-10",
            "start_time": "2025-05-10 19:00:00",
            "location": "Mattamy Athletic Centre",
            "attendance": 950,
        },
        {
            "game_number": 3,
            "date": "2025-05-17",
            "start_time": "2025-05-17 16:15:00",
            "location": "UofT Gymnasium",
            "attendance": 1100,
        },
        {
            "game_number": 4,
            "date": "2025-05-24",
            "start_time": "2025-05-24 14:00:00",
            "location": "Mattamy Athletic Centre",
            "attendance": 1050,
        },
        {
            "game_number": 5,
            "date": "2025-05-31",
            "start_time": "2025-05-31 19:30:00",
            "location": "UofT Gymnasium",
            "attendance": 1300,
        },
    ],
}
# Create tables first
create_tables()


def setup_data_from_dict(data_dict):
    """
    Add teams, players, and games from a dictionary

    Args:
        data_dict: Dictionary with teams and games data

    Returns:
        str: Result message
    """
    try:
        with Session(engine) as session:
            # Track stats
            teams_added = 0
            players_added = 0
            games_added = 0

            # Process teams and their players
            if "teams" in data_dict:
                for team_data in data_dict["teams"]:
                    # Create team
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
                            player = Player(
                                team_id=team.id,  # type: ignore
                                name=player_data["name"],
                                jersey_number=player_data["jersey_number"],
                                position=player_data["position"],
                                school=player_data.get("school", ""),
                                birth_date=player_data["birth_date"],
                                nationality=player_data.get("nationality", ""),
                            )
                            session.add(player)
                            players_added += 1

            # Process games
            if "games" in data_dict:
                for game_data in data_dict["games"]:
                    # Convert string dates to datetime objects if needed
                    date = game_data["date"]
                    if isinstance(date, str):
                        date = datetime.fromisoformat(date.replace(" ", "T"))

                    start_time = game_data["start_time"]
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(start_time.replace(" ", "T"))

                    game = Game(
                        game_number=game_data["game_number"],
                        date=date,
                        start_time=start_time,
                        location=game_data["location"],
                        attendance=game_data["attendance"],
                    )
                    session.add(game)
                    games_added += 1

            # Commit all changes
            session.commit()

            return f"Added {teams_added} teams, {players_added} players, and {games_added} games to the database"

    except IntegrityError as e:
        # Handle database integrity errors (duplicates, etc.)
        session.rollback()
        error_details = str(e)
        print(f"Database integrity error: {error_details}")
        return "No data updated: integrity error"

    except Exception as e:
        # Handle other errors
        session.rollback()
        print(f"Error adding data: {str(e)}")
        return "No data updated: unexpected error"


if __name__ == "__main__":
    # Example dictionary - replace with your own
    sample_data = INIT_DATA

    # Call the function with your dictionary
    result = setup_data_from_dict(sample_data)
    print(result)
