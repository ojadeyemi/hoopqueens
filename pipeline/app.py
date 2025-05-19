import os
import tempfile
from typing import List, Optional

import pandas as pd
import streamlit as st
from sqlmodel import Session, func, select
from streamlit_pdf_viewer import pdf_viewer

from db.database import engine, save_game_data
from db.models import Game, PlayerBoxScore, TeamBoxScore


@st.cache_resource
def get_db_engine():
    """Cache the database connection"""
    return engine


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


def get_games_from_db(sql_engine) -> List[Game]:
    try:
        with Session(sql_engine) as session:
            games = session.exec(select(Game).order_by(Game.date)).all()
            return games
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return []


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


def display_team_standings(sql_engine):
    try:
        with Session(sql_engine) as session:
            # Get all teams
            teams_query = select(
                TeamBoxScore.team_id,
                TeamBoxScore.team_name,
                func.count(TeamBoxScore.id).label("games_played"),
                func.sum(TeamBoxScore.final_score).label("points_for"),
            ).group_by(TeamBoxScore.team_id, TeamBoxScore.team_name)

            teams = session.exec(teams_query).all()

            if not teams:
                st.info("No team data available yet.")
                return

            standings_data = []
            for team in teams:
                # Get wins (when final_score > opponent's final_score)
                wins = 0
                games = session.exec(select(TeamBoxScore).where(TeamBoxScore.team_id == team.team_id)).all()

                for game in games:
                    opponent = session.exec(
                        select(TeamBoxScore).where(
                            TeamBoxScore.game_id == game.game_id, TeamBoxScore.team_id != game.team_id
                        )
                    ).first()

                    if opponent and game.final_score > opponent.final_score:
                        wins += 1

                losses = team.games_played - wins
                win_pct = round(wins / team.games_played, 3) if team.games_played > 0 else 0

                standings_data.append(
                    {
                        "Team": team.team_name,
                        "Games": team.games_played,
                        "Wins": wins,
                        "Losses": losses,
                        "Win %": win_pct,
                        "Points": team.points_for,
                    }
                )

            if not standings_data:
                st.info("No standings data available.")
                return

            df = pd.DataFrame(standings_data)

            # Safe sorting with fallbacks
            try:
                df = df.sort_values(by=["Win %", "Points"], ascending=[False, False])
            except Exception:
                # Fallback sorting if any issue occurs
                if "Wins" in df.columns:
                    df = df.sort_values(by=["Wins"], ascending=[False])

            st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error displaying team standings: {str(e)}")


def display_player_leaderboard(sql_engine, stat: str = "points", min_games: int = 1):
    try:
        with Session(sql_engine) as session:
            # Check if the stat exists in PlayerBoxScore
            if not hasattr(PlayerBoxScore, stat):
                st.error(f"Invalid statistic: {stat}")
                return

            query = (
                select(
                    PlayerBoxScore.player_id,
                    PlayerBoxScore.player_name,
                    func.avg(getattr(PlayerBoxScore, stat)).label("avg_stat"),
                    func.count(PlayerBoxScore.id).label("games_played"),
                )
                .group_by(PlayerBoxScore.player_id, PlayerBoxScore.player_name)
                .having(func.count(PlayerBoxScore.id) >= min_games)
                .order_by(func.avg(getattr(PlayerBoxScore, stat)).desc())
            )

            results = session.exec(query).all()

            if not results:
                st.info("No player statistics available yet.")
                return

            leaderboard_data = [
                {"Player": r.player_name, f"Avg {stat.capitalize()}": round(r.avg_stat, 1), "Games": r.games_played}
                for r in results
            ]

            df = pd.DataFrame(leaderboard_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error displaying player leaderboard: {str(e)}")


def main():
    configure_page()
    st.title("🏀 HoopQueens Stats Tracker")

    try:
        db_engine = get_db_engine()
    except Exception as e:
        st.error(f"Failed to connect to database: {str(e)}")
        st.stop()

    main_tabs = st.tabs(["Update Games", "Standings", "Stats Leaders"])

    with main_tabs[0]:
        st.markdown("Upload box score PDFs to update game statistics")

        if not setup_openai_api():
            st.info("Please provide an OpenAI API key to continue.")
            return

        games = get_games_from_db(db_engine)

        if not games:
            st.warning("No games found in database.")
            st.stop()

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
                with Session(db_engine) as session:
                    game = session.exec(select(Game).where(Game.id == selected_game_id)).first()
                    if game:
                        st.info(
                            f"**Selected Game:** #{game.game_number} on {game.date.strftime('%Y-%m-%d')} at {game.location}"
                        )

                        team_scores = session.exec(
                            select(TeamBoxScore).where(TeamBoxScore.game_id == selected_game_id)
                        ).all()

                        if team_scores:
                            st.warning(
                                "⚠️ This game already has statistics. No changes will be made if you upload a PDF."
                            )
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
                            result = save_game_data(
                                db_engine, st.session_state.selected_game_id, st.session_state.stats_data
                            )
                            if result == "Game already has statistics. No changes made.":
                                st.warning(result)
                            else:
                                st.success(result)

                            if st.button("Process Another Game"):
                                if "stats_data" in st.session_state:
                                    del st.session_state.stats_data
                                if "selected_game_id" in st.session_state:
                                    del st.session_state.selected_game_id
                                if temp_file_path and os.path.exists(temp_file_path):
                                    os.unlink(temp_file_path)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Database save error: {str(e)}")

            # Clean up temp file if not needed
            if temp_file_path and os.path.exists(temp_file_path) and "stats_data" not in st.session_state:
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass

    with main_tabs[1]:
        st.subheader("Team Standings")
        display_team_standings(db_engine)

        try:
            with Session(db_engine) as session:
                games = session.exec(select(Game).order_by(Game.date)).all()

                if not games:
                    st.info("No games available yet.")
                    return

                game_data = []
                for game in games:
                    team_scores = session.exec(select(TeamBoxScore).where(TeamBoxScore.game_id == game.id)).all()

                    has_stats = "✅ Complete" if team_scores else "❌ Missing"
                    score = ""

                    if len(team_scores) >= 2:
                        score = f"{team_scores[0].team_name} {team_scores[0].final_score} - {team_scores[1].final_score} {team_scores[1].team_name}"

                    game_data.append(
                        {
                            "Game #": game.game_number,
                            "Date": game.date.strftime("%Y-%m-%d") if game.date else "Unknown",
                            "Time": game.start_time.strftime("%H:%M") if game.start_time else "Unknown",
                            "Location": game.location,
                            "Score": score,
                            "Status": has_stats,
                        }
                    )

                if game_data:
                    st.divider()
                    st.subheader("Game Results")
                    schedule_df = pd.DataFrame(game_data)
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

        display_player_leaderboard(db_engine, stat_key)


if __name__ == "__main__":
    main()
