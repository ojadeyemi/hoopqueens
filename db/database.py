from sqlmodel import create_engine

# Basic database configuration
DATABASE_URL = "sqlite:///hoopqueens.sqlite"
engine = create_engine(DATABASE_URL)


# Legacy function for backward compatibility
def parse_date(date_str):
    """Parse date in multiple formats"""
    from datetime import datetime

    formats = [
        "%Y-%m-%d",
        "%a %d %b %Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse date: {date_str}")
