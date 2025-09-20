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
from db.models import GameData, Player, PlayerBoxScoreModel, Team, TeamBoxScoreModel

# ============================================================================
# CONFIGURATION
# ============================================================================

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MODEL_NAME = "gpt-4.1-2025-04-14"
TEAM_IDS = [1, 2, 3, 4]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def get_openai_api_key() -> str:
    """Get API key from environment."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")
    return api_key


# ============================================================================
# FILE HANDLING
# ============================================================================


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


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================


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


def get_valid_database_ids() -> tuple[set[int], dict[int, dict[str, str | int]]]:
    """Get valid team and player IDs from database for validation."""
    with Session(engine) as session:
        valid_team_ids = {team.id for team in session.exec(select(Team)).all()}
        if not valid_team_ids:
            raise ValueError("No valid team IDs found in database")
        valid_players = {
            player.id: {"media_name": player.media_name, "team_id": player.team_id}
            for player in session.exec(select(Player)).all()
        }
    return valid_team_ids, valid_players  # type: ignore


# ============================================================================
# PROMPT GENERATION
# ============================================================================


def _format_team_list(teams: list[dict[str, str | int]]) -> list[str]:
    """Format team list for system prompt."""
    return [f"\n- Team ID {team['id']}: {team['name']} (abbreviation: {team['abbreviation']})" for team in teams]


def _format_player_list(players: list[dict[str, str | int | None]]) -> list[str]:
    """Format player list grouped by team for system prompt."""
    player_list = []
    current_team_id = None

    for player in players:
        if player["team_id"] != current_team_id:
            current_team_id = player["team_id"]
            player_list.append(f"\n  Team {player['team_name']} (ID: {current_team_id}):")
        player_list.append(f"\n- Player ID: {player['id']}, media name: {player['media_name']}")

    return player_list


def create_comprehensive_system_prompt() -> str:
    """Create system prompt with ALL teams and players."""
    teams = get_all_teams(TEAM_IDS)
    players = get_all_players(TEAM_IDS)

    team_list = _format_team_list(teams)
    player_list = _format_player_list(players)

    return _build_system_prompt(team_list, player_list)


def _build_system_prompt(team_list: list[str], player_list: list[str]) -> str:
    """Build the complete system prompt from formatted lists."""
    return f"""You are a basketball statistics parser. Extract ONLY team and player statistics from the uploaded game file.

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


# ============================================================================
# DATA VALIDATION
# ============================================================================


def _validate_team_data(game_data: GameData, valid_team_ids: set[int]) -> None:
    """Validate team data in parsed game data."""
    for team_score in game_data.team_box_scores:
        if team_score.team_id not in valid_team_ids:
            raise ValueError(f"Invalid team_id: {team_score.team_id}")


def _validate_and_correct_player_data(game_data: GameData, valid_players: dict[int, dict[str, str | int]]) -> None:
    """Validate and correct player data in parsed game data."""
    for player_score in game_data.player_box_scores:
        if player_score.player_id not in valid_players:
            raise ValueError(f"Invalid player_id: {player_score.player_id}")

        # Verify media_name matches database
        expected_media_name = valid_players[player_score.player_id]["media_name"]
        if not isinstance(expected_media_name, str):
            raise TypeError(f"Expected media_name to be string, got {type(expected_media_name)}")
        if player_score.media_name != expected_media_name:
            print(f"Warning: Correcting media_name from '{player_score.media_name}' to '{expected_media_name}'")
            player_score.media_name = expected_media_name

        # Verify team_id matches
        expected_team_id = valid_players[player_score.player_id]["team_id"]
        if not isinstance(expected_team_id, int):
            raise TypeError(f"Expected team_id to be int, got {type(expected_team_id)}")
        if player_score.team_id != expected_team_id:
            print(f"Warning: Correcting team_id for player {player_score.media_name}")
            player_score.team_id = expected_team_id


def validate_parsed_data(game_data: GameData) -> GameData:
    """Validate parsed data against database records."""
    valid_team_ids, valid_players = get_valid_database_ids()

    _validate_team_data(game_data, valid_team_ids)
    _validate_and_correct_player_data(game_data, valid_players)

    return game_data


def _validate_percentage_range(value: float, name: str, entity_name: str) -> None:
    """Validate that a percentage is in the correct range (0-1)."""
    if not 0 <= value <= 1:
        raise ValueError(f"{entity_name}: Invalid {name} {value}")


def _validate_team_percentages(team: TeamBoxScoreModel) -> list[str]:
    """Validate team percentage statistics."""
    issues = []
    try:
        _validate_percentage_range(team.field_goal_percentage, "FG%", f"Team {team.team_name}")
        _validate_percentage_range(team.three_pointer_percentage, "3P%", f"Team {team.team_name}")
        _validate_percentage_range(team.free_throw_percentage, "FT%", f"Team {team.team_name}")
    except ValueError as e:
        issues.append(str(e))
    return issues


def _validate_player_percentages(player: PlayerBoxScoreModel) -> list[str]:
    """Validate player percentage statistics."""
    issues = []
    try:
        _validate_percentage_range(player.field_goal_percentage, "FG%", f"Player {player.media_name}")
        _validate_percentage_range(player.three_pointer_percentage, "3P%", f"Player {player.media_name}")
        _validate_percentage_range(player.free_throw_percentage, "FT%", f"Player {player.media_name}")
    except ValueError as e:
        issues.append(str(e))
    return issues


def validate_game_data(game_data: GameData) -> list[str]:
    """Validate parsed game data and return list of issues."""
    issues = []

    # Check team box scores count
    if len(game_data.team_box_scores) != 2:
        issues.append(f"Expected 2 team box scores, got {len(game_data.team_box_scores)}")

    # Check player counts per team
    team_player_counts = {}
    for player in game_data.player_box_scores:
        team_player_counts[player.team_id] = team_player_counts.get(player.team_id, 0) + 1

    for team_id, count in team_player_counts.items():
        if count < 5:
            issues.append(f"Team {team_id} has only {count} players (minimum 5 expected)")

    # Validate percentages for teams and players
    for team in game_data.team_box_scores:
        issues.extend(_validate_team_percentages(team))

    for player in game_data.player_box_scores:
        issues.extend(_validate_player_percentages(player))

    return issues


# ============================================================================
# MAIN PARSING FUNCTIONS
# ============================================================================


def _create_openai_client() -> OpenAI:
    """Create and return configured OpenAI client."""
    return OpenAI(api_key=get_openai_api_key())


def _create_user_content(base64_data: str, mime_type: str) -> list[dict]:
    """Create user content for OpenAI API request."""
    return [
        {
            "type": "input_text",
            "text": (
                "Extract team and player statistics from this box score. "
                "Use ONLY the player and team IDs from your system prompt. "
                "Match media_name format EXACTLY as shown in the player list."
            ),
        },
        {"type": "input_image", "image_url": f"data:{mime_type};base64,{base64_data}"},
    ]


def _handle_api_response(completion) -> GameData:
    """Handle and validate OpenAI API response."""
    message = completion.output_parsed
    if not message:
        raise RuntimeError("Model refused to comply")
    elif message:
        return validate_parsed_data(message)
    else:
        raise RuntimeError("No content received in response")


def parse_game_file(file_path: str | Path) -> GameData:
    """Extract and validate game stats from file using structured outputs."""
    try:
        base64_data, mime_type = encode_file(file_path)
    except Exception as e:
        raise RuntimeError(f"File encoding failed: {e}")

    try:
        client = _create_openai_client()
        system_prompt = create_comprehensive_system_prompt()
        user_content = _create_user_content(base64_data, mime_type)

        completion = client.responses.parse(
            model=MODEL_NAME,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},  # type: ignore
            ],
            text_format=GameData,
            temperature=0.1,
        )

        return _handle_api_response(completion)

    except AuthenticationError:
        raise ValueError("Invalid OpenAI API key.")
    except RateLimitError:
        raise RuntimeError("OpenAI API rate limit exceeded. Please try again later.")
    except OpenAIError as e:
        raise RuntimeError(f"OpenAI API error: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error during parsing: {e}")
