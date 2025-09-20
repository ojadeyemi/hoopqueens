"""
Configuration constants for the HoopQueens db application.
"""

from pathlib import Path

# Current season - update this each year
CURRENT_SEASON = 2025

# Database configuration
# Get the project root directory (where this config.py file is located)
PROJECT_ROOT = Path(__file__).parent
DATABASE_PATH = PROJECT_ROOT / "hoopqueens.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
