#!/usr/bin/env python3
"""
Database management script for HoopQueens.
Simple interface for seeding and managing data.
"""

import sys
from pathlib import Path

from pipeline.data_seeder import create_data_seeder
from pipeline.game_service import create_game_service


def main():
    """Simple CLI for database management."""
    if len(sys.argv) < 2:
        print_help()
        return

    command = sys.argv[1].lower()

    # Initialize services
    game_service = create_game_service()
    seeder = create_data_seeder(game_service)

    if command == "seed":
        # Default to seed_data.json if no file specified
        file_path = sys.argv[2] if len(sys.argv) > 2 else "data/seed_data.json"

        if not Path(file_path).exists():
            print(f"❌ File not found: {file_path}")
            return

        print(f"🌱 Seeding data from {file_path}...")
        result = seeder.seed_from_file(file_path)
        print(f"✅ {result}")

    elif command == "stats":
        print("📊 Database Statistics:")
        stats = seeder.get_database_stats()
        for table, count in stats.items():
            print(f"   {table}: {count}")

    elif command == "reset":
        confirm = input("⚠️  This will delete ALL data. Type 'yes' to confirm: ")
        if confirm.lower() == "yes":
            result = seeder.reset_database()
            print(f"🗑️  {result}")
        else:
            print("❌ Reset cancelled")

    elif command == "init":
        # Full initialization: reset + seed
        print("🚀 Initializing database...")

        confirm = input("This will reset ALL data and seed fresh data. Type 'yes' to confirm: ")
        if confirm.lower() != "yes":
            print("❌ Initialization cancelled")
            return

        # Reset first
        reset_result = seeder.reset_database()
        print(f"🗑️  {reset_result}")

        # Then seed
        file_path = sys.argv[2] if len(sys.argv) > 2 else "data/seed_data.json"
        if Path(file_path).exists():
            seed_result = seeder.seed_from_file(file_path)
            print(f"🌱 {seed_result}")
        else:
            print(f"❌ Seed file not found: {file_path}")

    else:
        print(f"❌ Unknown command: {command}")
        print_help()


def print_help():
    """Print help information."""
    print("""
🏀 HoopQueens Database Manager

Usage:
  python manage_data.py <command> [options]

Commands:
  seed [file]     Seed database with data (default: data/seed_data.json)
  stats           Show current database statistics  
  reset           Delete all data from database
  init [file]     Reset database and seed with fresh data

Examples:
  python manage_data.py seed                    # Seed with default data
  python manage_data.py seed data/custom.json   # Seed with custom file
  python manage_data.py stats                   # Show current stats
  python manage_data.py init                    # Fresh start with default data
    """)


if __name__ == "__main__":
    main()
