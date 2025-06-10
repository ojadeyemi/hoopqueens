"""
Basketball Statistics Management App
Streamlit app for uploading, parsing, editing, and managing game statistics.
"""

from parser import ALLOWED_EXTENSIONS, parse_game_file, validate_game_data
from pathlib import Path

import pandas as pd
import streamlit as st
from game_service import GameService, create_game_service
from stats_service import StatsService, create_stats_service

from db.models import GameData

# Page config
st.set_page_config(
    page_title="HoopQueens Stats Manager", page_icon="🏀", layout="wide", initial_sidebar_state="expanded"
)


# Initialize services
@st.cache_resource
def init_services():
    """Initialize and cache service instances."""
    game_service = create_game_service()
    stats_service = create_stats_service(game_service)
    return game_service, stats_service


def display_header():
    """Display app header."""
    st.title("🏀 HoopQueens Statistics Manager")
    st.markdown("---")


def display_sidebar_stats(game_service):
    """Display database statistics in sidebar."""
    st.sidebar.header("📊 Database Status")

    total_games = game_service.get_game_count()
    games_with_stats = game_service.get_games_with_stats_count()

    col1, col2 = st.sidebar.columns(2)
    col1.metric("Total Games", total_games)
    col2.metric("With Stats", games_with_stats)

    if total_games > 0:
        progress = games_with_stats / total_games
        st.sidebar.progress(progress, text=f"{progress:.0%} Complete")


def upload_section():
    """Handle file upload section."""
    st.header("📤 Upload Game Statistics")

    uploaded_file = st.file_uploader(
        "Choose a game statistics file",
        type=[ext.replace(".", "") for ext in ALLOWED_EXTENSIONS],
        help="Upload PDF, JPG, JPEG, or PNG files containing game box scores",
    )

    if uploaded_file:
        # Save uploaded file temporarily
        temp_path = Path(f"temp_{uploaded_file.name}")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        return temp_path

    return None


def parse_and_preview_section(file_path: Path, game_service: GameService):
    """Parse file and show editable preview."""
    st.header("🔍 Parse and Preview")

    # Game selection
    games = game_service.get_all_games()
    game_options = {
        f"Game {g.game_number} - {g.date.strftime('%Y-%m-%d')} - {g.start_time}": g.id
        for g in games
        if not game_service.game_has_stats(g.id)  # type: ignore
    }

    if not game_options:
        st.warning("No games available without statistics.")
        return None, None

    selected_game = st.selectbox("Select game to add statistics:", options=list(game_options.keys()))
    game_id = game_options[selected_game]

    # Parse button
    if st.button("🚀 Parse File", type="primary"):
        with st.spinner("Parsing game statistics..."):
            try:
                game_data = parse_game_file(file_path)
                st.session_state["parsed_data"] = game_data
                st.session_state["game_id"] = game_id

                # Validate data
                issues = validate_game_data(game_data)
                if issues:
                    st.warning("⚠️ Validation issues found:")
                    for issue in issues:
                        st.write(f"- {issue}")
                else:
                    st.success("✅ File parsed successfully!")

            except Exception as e:
                st.error(f"❌ Error parsing file: {e}")
                return None, None

    return st.session_state.get("parsed_data"), st.session_state.get("game_id")


def edit_team_stats(game_data: GameData) -> GameData:
    """Edit team statistics with data editor."""
    st.subheader("🏀 Team Statistics")

    # Convert to DataFrame for editing
    team_df = pd.DataFrame([team.model_dump() for team in game_data.team_box_scores])

    # Configure columns
    column_config = {
        "team_id": st.column_config.NumberColumn("Team ID", disabled=True),
        "team_name": st.column_config.TextColumn("Team Name", disabled=True),
        "team_abbreviation": st.column_config.TextColumn("Abbr", disabled=True),
        "final_score": st.column_config.NumberColumn("Final Score", min_value=0, max_value=200),
        "field_goal_percentage": st.column_config.NumberColumn("FG%", min_value=0.0, max_value=1.0, format="%.3f"),
        "three_pointer_percentage": st.column_config.NumberColumn("3P%", min_value=0.0, max_value=1.0, format="%.3f"),
        "free_throw_percentage": st.column_config.NumberColumn("FT%", min_value=0.0, max_value=1.0, format="%.3f"),
    }

    edited_team_df = st.data_editor(
        team_df, column_config=column_config, use_container_width=True, hide_index=True, key="team_editor"
    )

    # Update game_data with edited values
    for i, row in edited_team_df.iterrows():
        game_data.team_box_scores[i] = game_data.team_box_scores[i].model_validate(row.to_dict())  # type: ignore

    return game_data


def edit_player_stats(game_data: GameData) -> GameData:
    """Edit player statistics with data editor."""
    st.subheader("👥 Player Statistics")

    # Group by team
    team_names = {team.team_id: team.team_name for team in game_data.team_box_scores}

    for team_id, team_name in team_names.items():
        st.write(f"**{team_name}**")

        # Filter players for this team
        team_players = [p for p in game_data.player_box_scores if p.team_id == team_id]

        if not team_players:
            st.warning(f"No players found for {team_name}")
            continue

        # Convert to DataFrame
        player_df = pd.DataFrame([p.model_dump() for p in team_players])

        # Configure columns
        column_config = {
            "player_id": st.column_config.NumberColumn("Player ID", disabled=True),
            "team_id": st.column_config.NumberColumn("Team ID", disabled=True),
            "media_name": st.column_config.TextColumn("Name", help="Format: LastInitial. FirstName"),
            "jersey_number": st.column_config.NumberColumn("Jersey #", min_value=0, max_value=99),
            "minutes": st.column_config.NumberColumn("Minutes", min_value=0.0, max_value=48.0, format="%.1f"),
            "points": st.column_config.NumberColumn("Points", min_value=0),
            "field_goal_percentage": st.column_config.NumberColumn("FG%", min_value=0.0, max_value=1.0, format="%.3f"),
            "three_pointer_percentage": st.column_config.NumberColumn(
                "3P%", min_value=0.0, max_value=1.0, format="%.3f"
            ),
            "free_throw_percentage": st.column_config.NumberColumn("FT%", min_value=0.0, max_value=1.0, format="%.3f"),
            "plus_minus": st.column_config.NumberColumn("+/-"),
        }

        # Select columns to display
        display_columns = [
            "media_name",
            "jersey_number",
            "minutes",
            "points",
            "field_goals_made",
            "field_goals_attempted",
            "field_goal_percentage",
            "three_pointers_made",
            "three_pointers_attempted",
            "three_pointer_percentage",
            "free_throws_made",
            "free_throws_attempted",
            "free_throw_percentage",
            "total_rebounds",
            "assists",
            "steals",
            "blocks",
            "turnovers",
            "fouls",
            "plus_minus",
        ]

        edited_player_df = st.data_editor(
            player_df[display_columns],
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            key=f"player_editor_{team_id}",
        )

        # Update game_data with edited values
        player_index = 0
        for i, p in enumerate(game_data.player_box_scores):
            if p.team_id == team_id:
                # Merge edited data back
                original_data = p.model_dump()
                edited_data = edited_player_df.iloc[player_index].to_dict()
                original_data.update(edited_data)
                game_data.player_box_scores[i] = game_data.player_box_scores[i].model_validate(original_data)
                player_index += 1

    return game_data


def save_section(game_data: GameData, game_id: int, game_service):
    """Handle saving edited data."""
    st.header("💾 Save to Database")

    col1, col2, col3 = st.columns([2, 1, 2])

    with col2:
        if st.button("💾 Save Statistics", type="primary", use_container_width=True):
            try:
                message = game_service.save_game_stats(game_id, game_data)
                st.success(f"✅ {message}")

                # Clear session state
                if "parsed_data" in st.session_state:
                    del st.session_state["parsed_data"]
                if "game_id" in st.session_state:
                    del st.session_state["game_id"]

                # Rerun to refresh stats
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error saving data: {e}")


def view_statistics_section(stats_service: StatsService):
    """Display game statistics and leaderboards."""
    st.header("📈 View Statistics")

    tab1, tab2, tab3 = st.tabs(["Team Standings", "Player Leaders", "Game Results"])

    with tab1:
        standings = stats_service.get_team_standings()
        if standings:
            st.dataframe(pd.DataFrame(standings), use_container_width=True, hide_index=True)
        else:
            st.info("No team statistics available yet.")

    with tab2:
        stat_option = st.selectbox("Select statistic:", ["points", "assists", "total_rebounds", "steals", "blocks"])

        min_games = st.slider("Minimum games played:", 1, 10, 3)

        leaders = stats_service.get_player_leaderboard(stat_option, min_games)
        if leaders:
            st.dataframe(pd.DataFrame(leaders), use_container_width=True, hide_index=True)
        else:
            st.info("No player statistics available yet.")

    with tab3:
        results = stats_service.get_game_results()
        if results:
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
        else:
            st.info("No games recorded yet.")


def main():
    """Main application flow."""
    display_header()

    # Initialize services
    game_service, stats_service = init_services()

    # Sidebar stats
    display_sidebar_stats(game_service)

    # Main content tabs
    tab1, tab2 = st.tabs(["📤 Upload & Edit", "📊 View Statistics"])

    with tab1:
        # Upload section
        file_path = upload_section()

        if file_path:
            # Parse and preview
            game_data, game_id = parse_and_preview_section(file_path, game_service)

            if game_data and game_id:
                st.markdown("---")
                st.header("✏️ Edit Statistics")
                st.info("💡 You can edit any values below before saving to the database.")

                # Edit team stats
                game_data = edit_team_stats(game_data)

                st.markdown("---")

                # Edit player stats
                game_data = edit_player_stats(game_data)

                st.markdown("---")

                # Save section
                save_section(game_data, game_id, game_service)

            # Cleanup temp file
            try:
                file_path.unlink()
            except Exception as e:
                print("Could not delete temporary file, it may still be in use.", e)
                pass

    with tab2:
        view_statistics_section(stats_service)


if __name__ == "__main__":
    main()
