import os
import tempfile
from parser import parse_game_pdf
from typing import Optional

import pandas as pd
import streamlit as st

from db.database import create_tables, save_game_data
from db.models import GameData


def configure_page() -> None:
    """Setup Streamlit page layout"""
    st.set_page_config(page_title="HoopQueens Data Extractor", page_icon="🏀", layout="wide")

    st.markdown(
        """
        <style>
        .main .block-container {
            padding-top: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def upload_section() -> Optional[str]:
    """Handle PDF upload and display preview"""
    from streamlit_pdf_viewer import pdf_viewer

    uploaded_file = st.file_uploader("Upload basketball box score PDF", type="pdf")

    if uploaded_file:
        # Save PDF temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        # Display full-width PDF preview
        st.subheader("PDF Preview")
        pdf_viewer(uploaded_file.getvalue(), width="100%", height=700)
        st.info(f"Filename: {uploaded_file.name}")

        return tmp_path

    return None


def display_game_info(game_data: GameData) -> None:
    """Show game information in table"""
    game_df = pd.DataFrame([game_data.game.model_dump()])

    # Format datetime columns
    if "date" in game_df.columns:
        game_df["date"] = pd.to_datetime(game_df["date"]).dt.strftime("%Y-%m-%d")
    if "start_time" in game_df.columns:
        game_df["start_time"] = pd.to_datetime(game_df["start_time"]).dt.strftime("%H:%M:%S")
    if "report_generated" in game_df.columns:
        game_df["report_generated"] = pd.to_datetime(game_df["report_generated"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    st.dataframe(game_df, use_container_width=True)


def display_team_stats(game_data: GameData) -> None:
    """Show team statistics in table"""
    team_data = [t.model_dump() for t in game_data.team_box_scores]
    team_df = pd.DataFrame(team_data)
    st.dataframe(team_df, use_container_width=True)


def display_player_stats(game_data: GameData) -> None:
    """Show player statistics in table"""
    player_data = [p.model_dump() for p in game_data.player_box_scores]
    player_df = pd.DataFrame(player_data)

    # Sort by team and points
    if not player_df.empty and "team_id" in player_df.columns and "points" in player_df.columns:
        player_df = player_df.sort_values(by=["team_id", "points"], ascending=[True, False])

    st.dataframe(player_df, use_container_width=True, height=400)


def process_pdf(file_path: str) -> Optional[GameData]:
    """Extract data from PDF using AI"""
    with st.spinner("Processing PDF with AI..."):
        try:
            progress_bar = st.progress(0)
            for i in range(3):
                progress_bar.progress((i + 1) * 30)

            game_data = parse_game_pdf(file_path)
            progress_bar.progress(100)
            return game_data

        except ValueError as e:
            st.error(f"Validation error: {str(e)}")
            return None
        except Exception as e:
            st.error(f"Error extracting data: {str(e)}")
            return None


def setup_openai_api() -> bool:
    """Ensure OpenAI API key is available"""
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        st.warning("OpenAI API key not found in environment.")
        user_api_key = st.text_input("Enter your OpenAI API key:", type="password")

        if user_api_key:
            os.environ["OPENAI_API_KEY"] = user_api_key
            return True
        return False

    return True


def main() -> None:
    """Main application function"""
    configure_page()

    st.title("🏀 HoopQueens Data Extractor")
    st.markdown("Extract basketball game statistics from box score PDFs")

    # Check for API key
    api_key_available = setup_openai_api()
    if not api_key_available:
        st.info("Please provide an OpenAI API key to continue.")
        return

    # Initialize database
    try:
        create_tables()
    except Exception as e:
        st.error(f"Database initialization failed: {str(e)}")
        return

    # File upload
    temp_file_path = upload_section()

    # Process button
    if temp_file_path:
        if st.button("Process PDF", type="primary"):
            game_data = process_pdf(temp_file_path)
            if game_data:
                # Store in session state for persistent access
                st.session_state.game_data = game_data
                st.success("Data extracted successfully!")

    # Display extracted data if available in session state
    if "game_data" in st.session_state:
        st.divider()

        # Data tabs
        tab1, tab2, tab3 = st.tabs(["Game Info", "Team Stats", "Player Stats"])

        with tab1:
            st.subheader("Game Information")
            display_game_info(st.session_state.game_data)

        with tab2:
            st.subheader("Team Statistics")
            display_team_stats(st.session_state.game_data)

        with tab3:
            st.subheader("Player Statistics")
            display_player_stats(st.session_state.game_data)

        # Save button
        st.divider()
        if st.button("Save to Database", type="primary"):
            with st.spinner("Saving data to database..."):
                try:
                    save_game_data(st.session_state.game_data)
                    st.success("Data saved to database!")

                    # Reset for processing another PDF
                    if st.button("Process Another PDF"):
                        del st.session_state.game_data
                        if temp_file_path and os.path.exists(temp_file_path):
                            os.unlink(temp_file_path)
                        st.rerun()

                except Exception as e:
                    st.error(f"Database save error: {str(e)}")

    # Clean up temp file when not needed
    if temp_file_path and os.path.exists(temp_file_path) and "game_data" not in st.session_state:
        os.unlink(temp_file_path)


if __name__ == "__main__":
    main()
