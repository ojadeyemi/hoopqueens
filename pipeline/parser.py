"""
Game statistics parser using OpenAI structured outputs.
Extracts box score data from uploaded files with deterministic formatting.
"""

import base64
import os
from pathlib import Path

from openai import AuthenticationError, OpenAI, OpenAIError, RateLimitError
from sqlmodel import Session, col, select

from db.database import engine
from db.models import GameData, Player, Team

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MODEL_NAME = "gpt-4.1-2025-04-14"


def get_openai_api_key() -> str:
    """Get API key from environment."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")
    return api_key


def encode_file(file_path: str | Path) -> tuple[str, str]:
    """Encode file as base64 with MIME type."""
    file_path = Path(file_path)
    ext = file_path.suffix.lower()

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


def get_all_teams(team_ids: list[int]) -> list[dict[str, str | int]]:
    """Get all teams with their details, filtered by team_ids."""
    teams = []
    with Session(engine) as session:
        all_teams = session.exec(select(Team).where(col(Team.id).in_(team_ids))).all()
        for team in all_teams:
            teams.append(
                {
                    "id": team.id,
                    "name": team.name,
                    "abbreviation": team.abbreviation,
                }
            )
    return teams


def get_all_players(team_ids: list[int]) -> list[dict[str, str | int | None]]:
    """Get all players with their details, filtered by team_ids."""
    players = []
    with Session(engine) as session:
        all_players = session.exec(select(Player).where(col(Player.team_id).in_(team_ids)).join(Team)).all()
        for player in all_players:
            players.append(
                {
                    "id": player.id,
                    "team_id": player.team_id,
                    "team_name": player.team.name if player.team else "Unknown",
                    "media_name": player.media_name,
                    "first_name": player.first_name,
                    "last_name": player.last_name,
                }
            )
    return players


def create_comprehensive_system_prompt() -> str:
    """Create system prompt with ALL teams and players."""
    teams = get_all_teams([1, 2, 3, 4])
    players = get_all_players([1, 2, 3, 4])

    # Format team list
    team_list = []
    for team in teams:
        team_list.append(f"\n- Team ID {team['id']}: {team['name']} (abbreviation: {team['abbreviation']})")

    # Format player list grouped by team
    player_list = []
    current_team_id = None
    for player in players:
        if player["team_id"] != current_team_id:
            current_team_id = player["team_id"]
            player_list.append(f"\n  Team {player['team_name']} (ID: {current_team_id}):")

        player_list.append(f"\n- Player ID: {player['id']}, media name: {player['media_name']}")

    system_prompt = f"""You are a basketball statistics parser. Extract ONLY team and player statistics from the uploaded game file.

                        CRITICAL INSTRUCTIONS:
                        1. Use ONLY the teams and players listed below. DO NOT create new IDs.
                        2. Match player names EXACTLY as shown in their media_name format.
                        3. The media_name format is ALWAYS: "LastInitial. FirstName" (e.g., "J. LeBron")

                        ALL TEAMS IN DATABASE:
                        {chr(10).join(team_list)}

                        ALL PLAYERS IN DATABASE:
                        {"".join(player_list)}

                        Note not all players may be present in the game file, but you must use the IDs and media names provided above.

                
                        MATCHING RULES:
                        - Use the EXACT player_id and team_id from the lists above
                        - The media_name must match EXACTLY as shown above
                        - If you see a player name in the image, find the matching player from the list above
                        - Jersey numbers should help confirm the correct player

                        NUMERIC RULES:
                        - All percentages must be decimal values between 0 and 1 (e.g., 45.5% = 0.455) Make sure they are correct based on what they are derived from
                        - Minutes should be in decimal format (e.g., 35:42 = 35.7)
                        - Plus/minus can be negative

                        VALIDATION:
                        - ONLY use player_ids from the list above (no made-up IDs)
                        - ONLY use team_ids from the list above (no made-up IDs)
                        - Each team should have exactly the players shown in the box score
                        - Total team stats should roughly match sum of player stats

                        in the image the jersey number of the player is under the 'No" column .
                        in the image the teams data are in the totals row under each team tables and also the extra two tables which additonal stats

                        Return ONLY the data matching the GameData schema structure.
                        # Basketball Game Statistics


                        """

    return system_prompt


def parse_game_file(file_path: str | Path) -> GameData:
    """Extract and validate game stats from file using structured outputs."""
    try:
        base64_data, mime_type = encode_file(file_path)
    except Exception as e:
        raise RuntimeError(f"File encoding failed: {e}")

    try:
        client = OpenAI(api_key=get_openai_api_key())
        system_prompt = create_comprehensive_system_prompt()

        completion = client.beta.chat.completions.parse(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{base64_data}"},
                        },
                        {
                            "type": "text",
                            "text": (
                                "Extract team and player statistics from this box score. "
                                "Use ONLY the player and team IDs from your system prompt. "
                                "Match media_name format EXACTLY as shown in the player list."
                            ),
                        },
                    ],
                },
            ],
            response_format=GameData,
            temperature=0.1,  # Lower temperature for more deterministic output
        )

        msg = completion.choices[0].message
        if msg.parsed:
            return validate_parsed_data(msg.parsed)
        elif msg.refusal:
            raise RuntimeError(f"Model refused to comply: {msg.refusal}")
        else:
            raise RuntimeError("Received no data or refusal.")

    except AuthenticationError:
        raise ValueError("Invalid OpenAI API key.")
    except RateLimitError:
        raise RuntimeError("OpenAI API rate limit exceeded. Please try again later.")
    except OpenAIError as e:
        raise RuntimeError(f"OpenAI API error: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error during parsing: {e}")


def validate_parsed_data(game_data: GameData) -> GameData:
    """Validate parsed data against database records."""
    # Get valid IDs from database
    with Session(engine) as session:
        valid_team_ids = {team.id for team in session.exec(select(Team)).all()}
        valid_players = {
            player.id: {"media_name": player.media_name, "team_id": player.team_id}
            for player in session.exec(select(Player)).all()
        }

    # Validate teams
    for team_score in game_data.team_box_scores:
        if team_score.team_id not in valid_team_ids:
            raise ValueError(f"Invalid team_id: {team_score.team_id}")

    # Validate players
    for player_score in game_data.player_box_scores:
        if player_score.player_id not in valid_players:
            raise ValueError(f"Invalid player_id: {player_score.player_id}")

        # Verify media_name matches database
        expected_media_name = valid_players[player_score.player_id]["media_name"]
        if player_score.media_name != expected_media_name:
            print(f"Warning: Correcting media_name from '{player_score.media_name}' to '{expected_media_name}'")
            player_score.media_name = expected_media_name

        # Verify team_id matches
        expected_team_id = valid_players[player_score.player_id]["team_id"]
        if player_score.team_id != expected_team_id:
            print(f"Warning: Correcting team_id for player {player_score.media_name}")
            player_score.team_id = expected_team_id

    return game_data


def validate_game_data(game_data: GameData) -> list[str]:
    """Validate parsed game data and return list of issues."""
    issues = []

    # Check team box scores
    if len(game_data.team_box_scores) != 2:
        issues.append(f"Expected 2 team box scores, got {len(game_data.team_box_scores)}")

    # Check player counts per team
    team_player_counts = {}
    for player in game_data.player_box_scores:
        team_player_counts[player.team_id] = team_player_counts.get(player.team_id, 0) + 1

    for team_id, count in team_player_counts.items():
        if count < 5:
            issues.append(f"Team {team_id} has only {count} players (minimum 5 expected)")

    # Validate percentages
    for team in game_data.team_box_scores:
        if not 0 <= team.field_goal_percentage <= 1:
            issues.append(f"Team {team.team_name}: Invalid FG% {team.field_goal_percentage}")
        if not 0 <= team.three_pointer_percentage <= 1:
            issues.append(f"Team {team.team_name}: Invalid 3P% {team.three_pointer_percentage}")
        if not 0 <= team.free_throw_percentage <= 1:
            issues.append(f"Team {team.team_name}: Invalid FT% {team.free_throw_percentage}")

    # Validate player percentages
    for player in game_data.player_box_scores:
        if not 0 <= player.field_goal_percentage <= 1:
            issues.append(f"Player {player.media_name}: Invalid FG% {player.field_goal_percentage}")
        if not 0 <= player.three_pointer_percentage <= 1:
            issues.append(f"Player {player.media_name}: Invalid 3P% {player.three_pointer_percentage}")
        if not 0 <= player.free_throw_percentage <= 1:
            issues.append(f"Player {player.media_name}: Invalid FT% {player.free_throw_percentage}")

    return issues
