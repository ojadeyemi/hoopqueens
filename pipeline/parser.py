import base64
import os
from typing import Tuple

from openai import AuthenticationError, OpenAI, OpenAIError, RateLimitError
from sqlmodel import Session, select

from db.database import engine
from db.models import GameData, Player, Team

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def get_openai_api_key() -> str:
    """Get API key from environment."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")
    return api_key


def encode_file(file_path: str) -> Tuple[str, str]:
    """Encode file as base64 with MIME type."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")
    mime_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("utf-8"), mime_types[ext]


def get_team_mappings() -> dict[str, int]:
    """Get team name/abbr to ID mapping."""
    mapping = {}
    with Session(engine) as session:
        for team in session.exec(select(Team)).all():
            if team.name:
                mapping[team.name.lower()] = team.id
            if team.abbreviation:
                mapping[team.abbreviation.lower()] = team.id
    return mapping


def get_player_mappings() -> dict[str, dict]:
    """Get player media_name to ID and team ID mapping."""
    mapping = {}
    with Session(engine) as session:
        for player in session.exec(select(Player)).all():
            if player.media_name:
                mapping[player.media_name.lower()] = {
                    "id": player.id,
                    "team_id": player.team_id,
                }
    return mapping


team_ids = get_team_mappings()
player_ids = get_player_mappings()


def parse_game_file(file_path: str) -> GameData:
    """Extract and validate game stats from file using structured outputs."""
    try:
        base64_data, mime_type = encode_file(file_path)
    except Exception as e:
        raise RuntimeError(f"File encoding failed: {e}")

    try:
        client = OpenAI(api_key=get_openai_api_key())
        system_prompt = (
            f"Extract ONLY team and player statistics from the uploaded file.\n"
            f"- Use these team IDs: {team_ids}\n"
            f"- Use these player IDs: {player_ids}\n"
            "- Percentages must be between 0 and 1\n"
            "- Use 0 for missing numeric fields, null for missing optional text\n"
            "- Return exactly the GameData schema (no extra fields)\n"
        )

        completion = client.beta.chat.completions.parse(
            model="gpt-4.1-mini-2025-04-14",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{base64_data}"},
                        },
                        {"type": "text", "text": "Extract only team and player statistics."},
                    ],
                },
            ],
            response_format=GameData,
        )

        msg = completion.choices[0].message
        if msg.parsed:
            return msg.parsed
        elif msg.refusal:
            raise RuntimeError(f"Model refused to comply: {msg.refusal}")
        else:
            raise RuntimeError("Received no data or refusal.")

    except AuthenticationError:
        raise ValueError("Invalid OpenAI API key.")
    except RateLimitError:
        raise RuntimeError("OpenAI API rate limit exceeded.")
    except OpenAIError as e:
        raise RuntimeError(f"OpenAI API error: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {e}")
