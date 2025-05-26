import os
import tempfile
from typing import Optional

import pandas as pd
import streamlit as st
from streamlit_pdf_viewer import pdf_viewer

from pipeline.game_service import create_game_service
from pipeline.stats_service import create_stats_service


@st.cache_resource
def get_services():
    """Create and cache service instances."""
    game_service = create_game_service()
    stats_service = create_stats_service(game_service)
    return game_service, stats_service


def configure_page():
    st.set_page_config(page_title="HoopQueens Data", page_icon="🏀", layout="wide")


def upload_section() -> Optional[str]:
    uploaded_file = st.file_uploader("Upload basketball box score PDF", type="pdf")
    if not uploaded_file:
        return None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        st.subheader("PDF Preview")
        pdf_viewer(uploaded_file.getvalue(), width="100%", height=700)
        st.info(f"Filename: {uploaded_file.name}")
        return tmp_path
    except Exception as e:
        st.error(f"Error processing uploaded file: {str(e)}")
        return None


@st.cache_data(show_spinner="Parsing PDF…")
def get_game_data(file_path: str):
    try:
        from pipeline.parser import parse_game_pdf

        return parse_game_pdf(file_path)
    except Exception as e:
        st.error(f"Failed to parse PDF: {str(e)}")
        return None


def display_team_stats(stats_data) -> Optional[pd.DataFrame]:
    try:
        team_data = [t.model_dump() for t in stats_data.team_box_scores]
        if not team_data:
            st.info("No team statistics available")
            return None
        team_df = pd.DataFrame(team_data)
        return st.data_editor(team_df, use_container_width=True)
    except Exception as e:
        st.error(f"Error displaying team stats: {str(e)}")
        return None


def display_player_stats(stats_data) -> Optional[pd.DataFrame]:
    try:
        player_data = [p.model_dump() for p in stats_data.player_box_scores]
        if not player_data:
            st.info("No player statistics available")
            return None

        player_df = pd.DataFrame(player_data)
        if not player_df.empty and {"team_id", "points"}.issubset(player_df.columns):
            player_df = player_df.sort_values(by=["team_id", "points"], ascending=[True, False])
        return st.data_editor(player_df, use_container_width=True, height=400)
    except Exception as e:
        st.error(f"Error displaying player stats: {str(e)}")
        return None


def process_pdf(file_path: str):
    with st.spinner("Processing PDF with AI…"):
        try:
            progress = st.progress(0)
            for i in range(1, 4):
                progress.progress(i * 30)
            stats_data = get_game_data(file_path)
            progress.progress(100)
            return stats_data
        except ValueError as e:
            st.error(f"Validation error: {e}")
        except Exception as e:
            st.error(f"Error extracting data: {e}")
    return None


def setup_openai_api() -> bool:
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        return True

    user_api_key = st.text_input("Enter your OpenAI API key:", type="password")
    if user_api_key:
        os.environ["OPENAI_API_KEY"] = user_api_key
        return True

    st.warning("OpenAI API key not found in environment.")
    return False


def main():
    configure_page()
    st.title("🏀 HoopQueens Stats Tracker")

    try:
        game_service, stats_service = get_services()
    except Exception as e:
        st.error(f"Failed to initialize services: {str(e)}")
        st.stop()

    main_tabs = st.tabs(["Update Games", "Standings", "Stats Leaders"])

    with main_tabs[0]:
        st.markdown("Upload box score PDFs to update game statistics")

        if not setup_openai_api():
            st.info("Please provide an OpenAI API key to continue.")
            return

        games = game_service.get_all_games()

        if not games:
            st.warning("No games found in database.")
            st.stop()

        # Create game selection options
        game_options = []
        for game in games:
            game_date = game.date.strftime("%Y-%m-%d") if game.date else "Unknown"
            game_time = game.start_time.strftime("%H:%M") if game.start_time else "Unknown"
            display_text = f"Game #{game.game_number}: {game_date} at {game_time} - {game.location}"
            game_options.append((game.id, display_text))

        selected_game_text = st.selectbox(
            "Select a game to update:", options=[text for _, text in game_options], index=0 if game_options else None
        )

        if selected_game_text:
            selected_game_id = next((id for id, text in game_options if text == selected_game_text), None)

            try:
                game = game_service.get_game_by_id(selected_game_id)
                if game:
                    st.info(
                        f"**Selected Game:** #{game.game_number} on {game.date.strftime('%Y-%m-%d')} at {game.location}"
                    )

                    if game_service.game_has_stats(selected_game_id):
                        st.warning("⚠️ This game already has statistics. No changes will be made if you upload a PDF.")
            except Exception as e:
                st.error(f"Error loading game data: {str(e)}")

            temp_file_path = upload_section()

            if temp_file_path and st.button("Process PDF", type="primary"):
                stats_data = process_pdf(temp_file_path)
                if stats_data:
                    st.session_state.stats_data = stats_data
                    st.session_state.selected_game_id = selected_game_id
                    st.success("Data extracted successfully!")

            if "stats_data" in st.session_state:
                st.divider()
                tabs = st.tabs(["Team Stats", "Player Stats"])

                with tabs[0]:
                    st.subheader("Team Statistics")
                    edited_team_df = display_team_stats(st.session_state.stats_data)
                    if edited_team_df is not None:
                        st.session_state.edited_team = edited_team_df

                with tabs[1]:
                    st.subheader("Player Statistics")
                    edited_player_df = display_player_stats(st.session_state.stats_data)
                    if edited_player_df is not None:
                        st.session_state.edited_player = edited_player_df

                st.divider()
                if st.button("Save to Database", type="primary"):
                    with st.spinner("Saving data to database…"):
                        try:
                            result = game_service.save_game_stats(
                                st.session_state.selected_game_id, st.session_state.stats_data
                            )
                            if result == "Game already has statistics. No changes made.":
                                st.warning(result)
                            else:
                                st.success(result)

                            if st.button("Process Another Game"):
                                # Clear session state
                                for key in ["stats_data", "selected_game_id", "edited_team", "edited_player"]:
                                    if key in st.session_state:
                                        del st.session_state[key]

                                if temp_file_path and os.path.exists(temp_file_path):
                                    os.unlink(temp_file_path)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Database save error: {str(e)}")

            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path) and "stats_data" not in st.session_state:
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass

    with main_tabs[1]:
        st.subheader("Team Standings")

        try:
            standings_data = stats_service.get_team_standings()
            if standings_data:
                df = pd.DataFrame(standings_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No team data available yet.")
        except Exception as e:
            st.error(f"Error displaying team standings: {str(e)}")

        try:
            game_results = stats_service.get_game_results()
            if game_results:
                st.divider()
                st.subheader("Game Results")
                schedule_df = pd.DataFrame(game_results)
                st.dataframe(schedule_df, use_container_width=True, hide_index=True)
            else:
                st.info("No game results available.")
        except Exception as e:
            st.error(f"Error displaying game results: {str(e)}")

    with main_tabs[2]:
        st.subheader("Player Leaderboards")

        stat_options = [
            ("points", "Points Per Game"),
            ("rebounds", "Rebounds Per Game"),
            ("assists", "Assists Per Game"),
            ("steals", "Steals Per Game"),
            ("blocks", "Blocks Per Game"),
            ("efficiency", "Efficiency Rating"),
        ]

        selected_stat = st.selectbox("Select Statistic:", options=[label for _, label in stat_options], index=0)

        stat_key = next((key for key, label in stat_options if label == selected_stat), "points")

        try:
            leaderboard_data = stats_service.get_player_leaderboard(stat_key)
            if leaderboard_data:
                df = pd.DataFrame(leaderboard_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No player statistics available yet.")
        except Exception as e:
            st.error(f"Error displaying player leaderboard: {str(e)}")


if __name__ == "__main__":
    main()
