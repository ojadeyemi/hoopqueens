from sqlmodel import create_engine, Session, select
from db.models import Team, Player, Game, TeamBoxScore, PlayerBoxScore
sqlite_database = "../hoopqueens.db"
sqlite_url = f"sqlite:///{sqlite_database}"

engine = create_engine(sqlite_url, echo=True)

def read_teams():
    with Session(engine) as session:
        statement = select(Team)
        results = session.exec(statement).all()
        print(results)
        
read_teams()