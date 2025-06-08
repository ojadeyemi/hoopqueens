from sqlmodel import Session, create_engine, select

from db.models import Game, Player, PlayerBoxScore, Team, TeamBoxScore

sqlite_database = "hoopqueens.db"
sqlite_url = f"sqlite:///{sqlite_database}"
engine = create_engine(sqlite_url, echo=True)


def read_teams():
    with Session(engine) as session:
        return session.exec(select(Team)).all()


def read_players():
    with Session(engine) as session:
        return session.exec(select(Player)).all()


def read_games():
    with Session(engine) as session:
        return session.exec(select(Game)).all()


def read_team_box_scores():
    with Session(engine) as session:
        return session.exec(select(TeamBoxScore)).all()


def read_player_box_scores():
    with Session(engine) as session:
        return session.exec(select(PlayerBoxScore)).all()
