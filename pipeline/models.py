from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from pydantic import ConfigDict


class Team(SQLModel, table=True):
    """Basketball team with basic information and management."""
    model_config = ConfigDict(validate_assignment=True)
    
    id: str = Field(primary_key=True, description="Unique team identifier")
    name: str = Field(description="Full team name (e.g., 'Los Angeles Lakers')")
    short_name: str | None = Field(None, description="Shortened team name (e.g., 'Lakers')")
    abbreviation: str | None = Field(None, description="Team abbreviation (e.g., 'LAL')")
    bio: str | None = Field(None, description="Team history and background information")
    coach: str | None = Field(None, description="Head coach name")
    general_manager: str | None = Field(None, description="General manager name")
    
    players: list["Player"] = Relationship(back_populates="team")


class Player(SQLModel, table=True):
    """Basketball player with team association and profile information."""
    model_config = ConfigDict(validate_assignment=True)
    
    id: str = Field(primary_key=True, description="Unique player identifier")
    name: str = Field(description="Player's full name")
    jersey_number: str | None = Field(None, description="Player's jersey number (e.g., '23')")
    position: str | None = Field(None, description="Playing position (e.g., 'Point Guard', 'Center')")
    team_id: str = Field(foreign_key="team.id", description="Reference to player's team")
    profile: dict[str, str | int | float] | None = Field(None, description="Additional player information (height, weight, etc.)")
    
    team: Team | None = Relationship(back_populates="players")


class Game(SQLModel, table=True):
    """Basketball game with timing, venue, and officiating details."""
    model_config = ConfigDict(validate_assignment=True)
    
    id: str = Field(primary_key=True, description="Unique game identifier")
    game_number: int | None = Field(None, description="Sequential game number in season")
    date: datetime = Field(description="Game date")
    start_time: datetime = Field(description="Game start time")
    report_generated: datetime = Field(description="When game statistics were compiled")
    location: str | None = Field(None, description="Game venue (e.g., 'Madison Square Garden')")
    attendance: int | None = Field(None, description="Number of spectators at the game")
    duration_seconds: int | None = Field(None, description="Total game duration in seconds")
    crew_chief: str | None = Field(None, description="Head referee name")
    umpires: str | None = Field(None, description="Other officials' names")


class TeamBoxScore(SQLModel, table=True):
    """Team-level statistics and performance metrics for a game."""
    model_config = ConfigDict(validate_assignment=True)
    
    id: int | None = Field(default=None, primary_key=True)
    game_id: str = Field(foreign_key="game.id", description="Reference to the game")
    team_id: str = Field(foreign_key="team.id", description="Reference to the team")
    final_score: int = Field(description="Team's final score for the game")
    interval_scores: dict[str, int] = Field(description="Scores by time intervals (e.g., {'0-5': 8, '5-10': 12})")
    
    # Shooting statistics
    field_goals_made: int = Field(description="Total field goals made")
    field_goals_attempted: int = Field(description="Total field goals attempted")
    field_goal_percentage: float = Field(description="Field goal percentage (0-100)")
    three_pointers_made: int = Field(description="Three-point shots made")
    three_pointers_attempted: int = Field(description="Three-point shots attempted")
    three_pointer_percentage: float = Field(description="Three-point percentage (0-100)")
    free_throws_made: int = Field(description="Free throws made")
    free_throws_attempted: int = Field(description="Free throws attempted")
    free_throw_percentage: float = Field(description="Free throw percentage (0-100)")
    
    # Rebounding statistics
    offensive_rebounds: int = Field(description="Offensive rebounds collected by team")
    defensive_rebounds: int = Field(description="Defensive rebounds collected by team")
    total_rebounds: int = Field(description="Total rebounds (offensive + defensive)")
    
    # General statistics
    assists: int = Field(description="Number of assists recorded")
    turnovers: int = Field(description="Number of turnovers committed")
    steals: int = Field(description="Number of steals recorded")
    blocks: int = Field(description="Number of shots blocked")
    fouls: int = Field(description="Personal fouls committed by team")
    fouls_drawn: int = Field(description="Fouls drawn from opposing team")
    plus_minus: int = Field(description="Point differential when team was on court")
    efficiency: int = Field(description="Team efficiency rating")
    
    # Advanced statistics
    points_from_turnovers: int = Field(description="Points scored off opponent turnovers")
    biggest_lead: str | None = Field(None, description="Largest lead held during game (e.g., '15 points')")
    biggest_run: str | None = Field(None, description="Longest scoring run (e.g., '12-0 run')")
    points_in_paint_made: int = Field(description="Points scored in the paint area")
    points_in_paint_attempted: int = Field(description="Shot attempts in the paint")
    points_in_paint_percentage: float = Field(description="Shooting percentage in the paint")
    second_chance_points: int = Field(description="Points scored off offensive rebounds")
    points_per_possession: float = Field(description="Average points scored per possession")
    fast_break_points: int = Field(description="Points scored on fast break opportunities")
    fast_break_points_from_turnovers: int = Field(description="Fast break points generated from turnovers")
    bench_points: int = Field(description="Points contributed by bench players")
    lead_changes: int = Field(description="Number of times the lead changed hands")
    times_tied: int = Field(description="Number of times the score was tied")
    time_with_lead: str | None = Field(None, description="Duration team held the lead (e.g., '32:45')")


class PlayerBoxScore(SQLModel, table=True):
    """Individual player statistics and performance for a game."""
    model_config = ConfigDict(validate_assignment=True)
    
    id: int | None = Field(default=None, primary_key=True)
    game_id: str = Field(foreign_key="game.id", description="Reference to the game")
    team_id: str = Field(foreign_key="team.id", description="Reference to the team")
    player_id: str = Field(foreign_key="player.id", description="Reference to the player")
    status: str | None = Field(None, description="Player status (e.g., 'Starter', 'Bench', 'DNP - Injury')")
    minutes: float | None = Field(None, description="Minutes played (e.g., 32.5)")
    
    # Shooting statistics
    field_goals_made: int = Field(description="Field goals made by player")
    field_goals_attempted: int = Field(description="Field goals attempted by player")
    field_goal_percentage: float = Field(description="Player's field goal percentage")
    three_pointers_made: int = Field(description="Three-point shots made")
    three_pointers_attempted: int = Field(description="Three-point shots attempted")
    three_pointer_percentage: float = Field(description="Player's three-point percentage")
    free_throws_made: int = Field(description="Free throws made by player")
    free_throws_attempted: int = Field(description="Free throws attempted by player")
    free_throw_percentage: float = Field(description="Player's free throw percentage")
    
    # Rebounding statistics
    offensive_rebounds: int = Field(description="Offensive rebounds collected by player")
    defensive_rebounds: int = Field(description="Defensive rebounds collected by player")
    total_rebounds: int = Field(description="Total rebounds by player")
    
    # General statistics
    assists: int = Field(description="Assists recorded by player")
    turnovers: int = Field(description="Turnovers committed by player")
    steals: int = Field(description="Steals recorded by player")
    blocks: int = Field(description="Shots blocked by player")
    fouls: int = Field(description="Personal fouls committed by player")
    fouls_drawn: int = Field(description="Fouls drawn by player from opponents")
    plus_minus: int = Field(description="Point differential when player was on court")
    efficiency: int = Field(description="Player efficiency rating")
    points: int = Field(description="Total points scored by player")