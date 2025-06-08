from fastapi import APIRouter
from services import read_games, read_player_box_scores, read_players, read_team_box_scores, read_teams

from db.models import Game, Player, PlayerBoxScore, Team, TeamBoxScore

router = APIRouter()


@router.get("/teams", response_model=list[Team])
def get_teams():
    return read_teams()


@router.get("/players", response_model=list[Player])
def get_players():
    return read_players()


@router.get("/games", response_model=list[Game])
def get_games():
    return read_games()


@router.get("/team-box-scores", response_model=list[TeamBoxScore])
def get_team_box_scores():
    return read_team_box_scores()


@router.get("/player-box-scores", response_model=list[PlayerBoxScore])
def get_player_box_scores():
    return read_player_box_scores()
