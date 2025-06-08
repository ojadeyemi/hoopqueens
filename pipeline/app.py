import os
import tempfile
from typing import Optional

import pandas as pd
import streamlit as st

from pipeline.game_service import create_game_service
from pipeline.stats_service import create_stats_service


@st.cache_resource
def get_services():
    """Create and cache service instances."""
    game_service = create_game_service()
    stats_service = create_stats_service(game_service)
    return game_service, stats_service


def configure_page():
    """Set Streamlit page configuration."""
    st.set_page_config(page_title="HoopQueens Data", page_icon="🏀", layout="wide")


def upload_section() -> Optional[str]:
    """Upload and preview a basketball box score file."""
    uploaded = st.file_uploader(
        "Upload box score file (PDF, JPEG, PNG, etc.)",
        type=["pdf", "jpeg", "jpg", "png"],
    )
    if not uploaded:
        return None
    ext = os.path.splitext(uploaded.name)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name
    st.subheader("File Preview")
    if ext == ".pdf":
        from streamlit_pdf_viewer import pdf_viewer

        pdf_viewer(uploaded.getvalue(), width="100%", height=700)
    else:
        st.image(uploaded, use_container_width=True)
    st.info(f"Filename: {uploaded.name}")
    return tmp_path


@st.cache_data(show_spinner="Parsing file…")
def get_game_data(file_path: str):
    """Parse game data via AI."""
    from pipeline.parser import parse_game_file

    return parse_game_file(file_path)


def display_team_stats(stats_data) -> Optional[pd.DataFrame]:
    """Display editable team statistics."""
    rows = [t.model_dump() for t in stats_data.team_box_scores]
    if not rows:
        st.info("No team statistics available")
        return None
    df = pd.DataFrame(rows)
    return st.data_editor(df, use_container_width=True)


def display_player_stats(stats_data) -> Optional[pd.DataFrame]:
    """Display editable player statistics."""
    rows = [p.model_dump() for p in stats_data.player_box_scores]
    if not rows:
        st.info("No player statistics available")
        return None
    df = pd.DataFrame(rows)
    if {"team_id", "points"}.issubset(df.columns):
        df = df.sort_values(["team_id", "points"], ascending=[True, False])
    return st.data_editor(df, use_container_width=True, height=400)


def process_file(file_path: str):
    """Process the uploaded file via AI and show progress."""
    with st.spinner("Processing file with AI…"):
        progress = st.progress(0)
        for i in range(1, 4):
            progress.progress(i * 30)
        data = get_game_data(file_path)
        progress.progress(100)
        return data


def setup_openai_api() -> bool:
    """Ensure OpenAI API key is set."""
    if os.environ.get("OPENAI_API_KEY"):
        return True
    key = st.text_input("Enter your OpenAI API key:", type="password")
    if key:
        os.environ["OPENAI_API_KEY"] = key
        return True
    st.warning("OpenAI API key not found in environment.")
    return False


def main():
    configure_page()
    st.title("🏀 HoopQueens Stats Tracker")

    try:
        game_service, stats_service = get_services()
    except Exception as e:
        st.error(f"Failed to initialize services: {e}")
        st.stop()

    tabs = st.tabs(["Update Games", "Standings", "Stats Leaders"])
    with tabs[0]:
        st.markdown("Upload box score files to update game statistics")
        if not setup_openai_api():
            st.info("Please provide an OpenAI API key to continue.")
            return

        games = game_service.get_all_games()
        if not games:
            st.warning("No games found in database.")
            st.stop()

        opts = [
            (
                g.id,
                f"Game #{g.game_number}: {g.date.strftime('%Y-%m-%d') if g.date else 'Unknown'} "
                f"at {g.start_time.strftime('%H:%M') if g.start_time else 'Unknown'} – {g.location}",
            )
            for g in games
        ]
        selection = st.selectbox("Select a game to update:", [label for _, label in opts])
        selected_id = next((i for i, lbl in opts if lbl == selection), None)
        if selected_id:
            game = game_service.get_game_by_id(selected_id)
            if game:
                st.info(
                    f"**Selected Game:** #{game.game_number} on {game.date.strftime('%Y-%m-%d')} at {game.location}"
                )
                if game_service.game_has_stats(selected_id):
                    st.warning("⚠️ This game already has statistics.")

        tmp = upload_section()
        if tmp and st.button("Process File", type="primary"):
            stats = process_file(tmp)
            if stats:
                st.session_state.stats_data = stats
                st.session_state.selected_game_id = selected_id
                st.success("Data extracted successfully!")

        if st.session_state.get("stats_data"):
            st.divider()
            subtabs = st.tabs(["Team Stats", "Player Stats"])
            with subtabs[0]:
                st.subheader("Team Statistics")
                st.session_state.edited_team = display_team_stats(st.session_state.stats_data)
            with subtabs[1]:
                st.subheader("Player Statistics")
                st.session_state.edited_player = display_player_stats(st.session_state.stats_data)

            st.divider()
            if st.button("Save to Database", type="primary"):
                with st.spinner("Saving data to database…"):
                    result = game_service.save_game_stats(
                        st.session_state.selected_game_id, st.session_state.stats_data
                    )
                    st.warning(result) if "already" in result else st.success(result)
                    if st.button("Process Another Game"):
                        for k in ["stats_data", "selected_game_id", "edited_team", "edited_player"]:
                            st.session_state.pop(k, None)
                        if tmp and os.path.exists(tmp):
                            os.unlink(tmp)
                        st.rerun()

        if tmp and os.path.exists(tmp) and "stats_data" not in st.session_state:
            os.unlink(tmp)

    with tabs[1]:
        st.subheader("Team Standings")
        try:
            df = pd.DataFrame(stats_service.get_team_standings() or [])
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error displaying team standings: {e}")
        try:
            results = stats_service.get_game_results()
            if results:
                st.divider()
                st.subheader("Game Results")
                st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error displaying game results: {e}")

    with tabs[2]:
        st.subheader("Player Leaderboards")
        stat_map = [
            ("points", "Points Per Game"),
            ("rebounds", "Rebounds Per Game"),
            ("assists", "Assists Per Game"),
            ("steals", "Steals Per Game"),
            ("blocks", "Blocks Per Game"),
            ("efficiency", "Efficiency Rating"),
        ]
        label = st.selectbox("Select Statistic:", options=[lbl for _, lbl in stat_map])
        key = next(k for k, lbl in stat_map if lbl == label)
        try:
            df = pd.DataFrame(stats_service.get_player_leaderboard(key) or [])
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error displaying player leaderboard: {e}")


if __name__ == "__main__":
    main()
