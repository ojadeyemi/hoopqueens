from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from sqlmodel import Field as SQLField
from sqlmodel import Relationship, SQLModel

SQLModel.__table_args__ = {"extend_existing": True}


# SQLModels for database
class Team(SQLModel, table=True):
    """Basketball team with basic information"""

    id: Optional[int] = SQLField(default=None, primary_key=True, description="Team ID")
    name: str = SQLField(description="Team name")
    abbreviation: str = SQLField(None, description="Team abbreviation")
    bio: str = SQLField(None, description="Team history")
    coach: str = SQLField(None, description="Head coach name")
    general_manager: str = SQLField(None, description="GM name")

    players: List["Player"] = Relationship(back_populates="team")


class Player(SQLModel, table=True):
    """Basketball player profile"""

    id: Optional[int] = SQLField(default=None, primary_key=True, description="Player ID")
    team_id: int = SQLField(foreign_key="team.id", description="Team reference")
    name: str = SQLField(description="Player name")
    jersey_number: int = SQLField(None, description="Jersey number")
    position: str = SQLField(None, description="Position")
    school: Optional[str] = SQLField(None, description="Player's school")
    birth_date: Optional[str] = SQLField(None, description="Birth date")
    nationality: Optional[str] = SQLField(None, description="Nationality")

    team: Team = Relationship(back_populates="players")
    box_scores: List["PlayerBoxScore"] = Relationship(back_populates="player")


class Game(SQLModel, table=True):
    """Basketball game details"""

    id: Optional[int] = SQLField(default=None, primary_key=True, description="Game ID")
    game_number: int = SQLField(unique=True, description="Game number in season")
    date: datetime = SQLField(description="Game date")
    start_time: datetime = SQLField(description="Start time")
    location: Optional[str] = SQLField(None, description="Venue")
    attendance: Optional[int] = SQLField(None, description="Spectator count")

    team_box_scores: List["TeamBoxScore"] = Relationship(back_populates="game")
    player_box_scores: List["PlayerBoxScore"] = Relationship(back_populates="game")


class TeamBoxScore(SQLModel, table=True):
    """Team statistics for a game"""

    id: Optional[int] = SQLField(default=None, primary_key=True)
    game_id: int = SQLField(foreign_key="game.id", description="Game reference")
    team_id: int = SQLField(foreign_key="team.id", description="Team reference")
    team_name: str = SQLField(description="Team name")
    team_abbreviation: str = SQLField(description="Team abbreviation")
    final_score: int = SQLField(description="Final score")

    # Shooting stats
    field_goals_made: int = SQLField(description="FG made")
    field_goals_attempted: int = SQLField(description="FG attempted")
    field_goal_percentage: float = SQLField(description="FG %")
    three_pointers_made: int = SQLField(description="3PT made")
    three_pointers_attempted: int = SQLField(description="3PT attempted")
    three_pointer_percentage: float = SQLField(description="3PT %")
    free_throws_made: int = SQLField(description="FT made")
    free_throws_attempted: int = SQLField(description="FT attempted")
    free_throw_percentage: float = SQLField(description="FT %")

    # Rebounds
    offensive_rebounds: int = SQLField(description="Offensive rebounds")
    defensive_rebounds: int = SQLField(description="Defensive rebounds")
    total_rebounds: int = SQLField(description="Total rebounds")

    # General stats
    assists: int = SQLField(description="Assists")
    turnovers: int = SQLField(description="Turnovers")
    steals: int = SQLField(description="Steals")
    blocks: int = SQLField(description="Blocks")
    fouls: int = SQLField(description="Fouls committed")
    fouls_drawn: int = SQLField(description="Fouls drawn")
    plus_minus: int = SQLField(description="Plus/minus")
    efficiency: int = SQLField(description="Efficiency rating")

    # Advanced stats
    points_from_turnovers: int = SQLField(description="Points off turnovers")
    biggest_lead: Optional[str] = SQLField(None, description="Largest lead")
    biggest_run: Optional[str] = SQLField(None, description="Biggest run")
    points_in_paint_made: int = SQLField(description="Paint points")
    points_in_paint_attempted: int = SQLField(description="Paint attempts")
    points_in_paint_percentage: float = SQLField(description="Paint %")
    second_chance_points: int = SQLField(description="Second chance points")
    points_per_possession: float = SQLField(description="Points per possession")
    fast_break_points: int = SQLField(description="Fast break points")
    fast_break_points_from_turnovers: int = SQLField(description="FB points off TOs")
    bench_points: int = SQLField(description="Bench points")
    lead_changes: int = SQLField(description="Lead changes")
    times_tied: int = SQLField(description="Times tied")
    time_with_lead: Optional[str] = SQLField(None, description="Time with lead")

    game: Game = Relationship(back_populates="team_box_scores")


class PlayerBoxScore(SQLModel, table=True):
    """Player statistics for a game"""

    id: Optional[int] = SQLField(default=None, primary_key=True)
    game_id: int = SQLField(foreign_key="game.id", description="Game reference")
    team_id: int = SQLField(foreign_key="team.id", description="Team reference")
    player_id: int = SQLField(foreign_key="player.id", description="Player reference")
    player_name: str = SQLField(description="Player name")
    minutes: float = SQLField(default=0, description="Minutes played")

    # Shooting stats
    field_goals_made: int = SQLField(description="FG made")
    field_goals_attempted: int = SQLField(description="FG attempted")
    field_goal_percentage: float = SQLField(description="FG %")
    three_pointers_made: int = SQLField(description="3PT made")
    three_pointers_attempted: int = SQLField(description="3PT attempted")
    three_pointer_percentage: float = SQLField(description="3PT %")
    free_throws_made: int = SQLField(description="FT made")
    free_throws_attempted: int = SQLField(description="FT attempted")
    free_throw_percentage: float = SQLField(description="FT %")

    # Rebounds
    offensive_rebounds: int = SQLField(description="Offensive rebounds")
    defensive_rebounds: int = SQLField(description="Defensive rebounds")
    total_rebounds: int = SQLField(description="Total rebounds")

    # General stats
    assists: int = SQLField(description="Assists")
    turnovers: int = SQLField(description="Turnovers")
    steals: int = SQLField(description="Steals")
    blocks: int = SQLField(description="Blocks")
    fouls: int = SQLField(description="Fouls committed")
    fouls_drawn: int = SQLField(description="Fouls drawn")
    plus_minus: int = SQLField(description="Plus/minus")
    efficiency: int = SQLField(description="Efficiency rating")
    points: int = SQLField(description="Points scored")

    game: Game = Relationship(back_populates="player_box_scores")
    player: Player = Relationship(back_populates="box_scores")


############################################
#                                          #
#   Pydantic models for OpenAI parsing     #
#                                          #
############################################


class TeamBoxScoreModel(BaseModel):
    """Team statistics model for API responses"""

    team_id: int = Field(description="Team reference")
    team_name: str = Field(description="Team name")
    team_abbreviation: str = Field(description="Team abbreviation")
    final_score: int = Field(description="Final score")

    # Shooting stats
    field_goals_made: int = Field(description="FG made")
    field_goals_attempted: int = Field(description="FG attempted")
    field_goal_percentage: float = Field(description="FG %")
    three_pointers_made: int = Field(description="3PT made")
    three_pointers_attempted: int = Field(description="3PT attempted")
    three_pointer_percentage: float = Field(description="3PT %")
    free_throws_made: int = Field(description="FT made")
    free_throws_attempted: int = Field(description="FT attempted")
    free_throw_percentage: float = Field(description="FT %")

    # Rebounds
    offensive_rebounds: int = Field(description="Offensive rebounds")
    defensive_rebounds: int = Field(description="Defensive rebounds")
    total_rebounds: int = Field(description="Total rebounds")

    # General stats
    assists: int = Field(description="Assists")
    turnovers: int = Field(description="Turnovers")
    steals: int = Field(description="Steals")
    blocks: int = Field(description="Blocks")
    fouls: int = Field(description="Fouls committed")
    fouls_drawn: int = Field(description="Fouls drawn")
    plus_minus: int = Field(description="Plus/minus")
    efficiency: int = Field(description="Efficiency rating")

    # Advanced stats
    points_from_turnovers: int = Field(description="Points off turnovers")
    biggest_lead: Optional[str] = Field(None, description="Largest lead")
    biggest_run: Optional[str] = Field(None, description="Biggest run")
    points_in_paint_made: int = Field(description="Paint points")
    points_in_paint_attempted: int = Field(description="Paint attempts")
    points_in_paint_percentage: float = Field(description="Paint %")
    second_chance_points: int = Field(description="Second chance points")
    points_per_possession: float = Field(description="Points per possession")
    fast_break_points: int = Field(description="Fast break points")
    fast_break_points_from_turnovers: int = Field(description="FB points off TOs")
    bench_points: int = Field(description="Bench points")
    lead_changes: int = Field(description="Lead changes")
    times_tied: int = Field(description="Times tied")
    time_with_lead: Optional[str] = Field(None, description="Time with lead")


class PlayerBoxScoreModel(BaseModel):
    """Player statistics model for API responses"""

    player_id: int = Field(description="Player reference")
    team_id: int = Field(description="Team reference")
    player_name: str = Field(description="Player name")
    minutes: float = Field(description="Minutes played, default to 0 if no minutes played")

    # Shooting stats
    field_goals_made: int = Field(description="FG made")
    field_goals_attempted: int = Field(description="FG attempted")
    field_goal_percentage: float = Field(description="FG %")
    three_pointers_made: int = Field(description="3PT made")
    three_pointers_attempted: int = Field(description="3PT attempted")
    three_pointer_percentage: float = Field(description="3PT %")
    free_throws_made: int = Field(description="FT made")
    free_throws_attempted: int = Field(description="FT attempted")
    free_throw_percentage: float = Field(description="FT %")

    # Rebounds
    offensive_rebounds: int = Field(description="Offensive rebounds")
    defensive_rebounds: int = Field(description="Defensive rebounds")
    total_rebounds: int = Field(description="Total rebounds")

    # General stats
    assists: int = Field(description="Assists")
    turnovers: int = Field(description="Turnovers")
    steals: int = Field(description="Steals")
    blocks: int = Field(description="Blocks")
    fouls: int = Field(description="Fouls committed")
    fouls_drawn: int = Field(description="Fouls drawn")
    plus_minus: int = Field(description="Plus/minus")
    efficiency: int = Field(description="Efficiency rating")
    points: int = Field(description="Points scored")


class GameData(BaseModel):
    """Box score data package"""

    team_box_scores: List[TeamBoxScoreModel]
    player_box_scores: List[PlayerBoxScoreModel]
