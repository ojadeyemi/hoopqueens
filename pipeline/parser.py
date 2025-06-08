import base64
import os

from openai import APIError, AuthenticationError, OpenAI, RateLimitError
from sqlmodel import Session, select

from db.database import engine
from db.models import GameData, Player, Team


def get_openai_api_key() -> str:
    """Get OpenAI API key from environment"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
    return api_key


def encode_pdf(file_path: str) -> str:
    """Encode PDF file to base64 string"""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode("utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to encode PDF: {str(e)}")


def get_team_mappings() -> dict[str, int]:
    """Get mapping of team names to IDs from database"""
    mapping = {}
    try:
        with Session(engine) as session:
            teams = session.exec(select(Team)).all()
            for team in teams:
                if team.name:
                    mapping[team.name.lower()] = team.id
                if team.abbreviation:
                    mapping[team.abbreviation.lower()] = team.id
    except Exception as e:
        print(f"Warning: Failed to get team mappings: {str(e)}")
    return mapping


def get_player_mappings() -> dict[str, dict]:
    """Get mapping of player names to IDs from database"""
    mapping = {}
    try:
        with Session(engine) as session:
            players = session.exec(select(Player)).all()
            for player in players:
                if player.media_name:
                    mapping[player.media_name.lower()] = {"id": player.id, "team_id": player.team_id}

    except Exception as e:
        print(f"Warning: Failed to get player mappings: {str(e)}")
    return mapping


team_ids = get_team_mappings()
player_ids = get_player_mappings()


def parse_game_pdf(pdf_file_path: str) -> GameData:
    """Extract box score statistics from basketball PDF"""
    # Encode PDF
    try:
        base64_string = encode_pdf(pdf_file_path)
    except Exception as e:
        raise RuntimeError(f"Failed to process PDF: {str(e)}")

    # Initialize OpenAI client
    try:
        api_key = get_openai_api_key()
        client = OpenAI(api_key=api_key)
    except ValueError as e:
        raise ValueError(str(e))

    # Parse box scores with OpenAI
    try:
        system_prompt = f"""
        Extract ONLY the box score statistics from the basketball PDF.
        Focus on team statistics and player statistics ONLY.
        Do NOT extract or include game information (game number, date, time, etc.).
        Be precise with all statistical data and follow the provided schema exactly.

        IMPORTANT FORMAT REQUIREMENTS:
        - Team IDs must use these specific values: {team_ids}
        - Player IDs must use these specific values: {player_ids}
        - For player_name field, use the media_name format (LastInitial. FirstName) when possible
        - All percentages must be between 0 and 1 (e.g., 0.545 for 54.5%)
        - Ensure all numerical fields have appropriate values (no strings in number fields)
        - For missing statistics, use 0 for numerical values and null for optional text fields

        The output must strictly follow the GameData schema with ONLY team_box_scores and player_box_scores.
        """
        print(system_prompt)  # Debugging: print the system prompt

        completion = client.beta.chat.completions.parse(
            model="gpt-4.1-mini-2025-04-14",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "file",
                            "file": {
                                "filename": "game_stats.pdf",
                                "file_data": f"data:application/pdf;base64,{base64_string}",
                            },
                        },
                        {"type": "text", "text": "Extract team and player statistics only."},
                    ],
                },
            ],
            response_format=GameData,
        )

        data = completion.choices[0].message.parsed

        if data:
            return data
        else:
            raise ValueError("Failed to parse box score data from PDF.")

    except AuthenticationError:
        raise ValueError("Invalid OpenAI API key.")
    except RateLimitError:
        raise RuntimeError("OpenAI API rate limit exceeded. Try again later.")
    except APIError as e:
        raise RuntimeError(f"OpenAI API error: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Failed to extract data: {str(e)}")
