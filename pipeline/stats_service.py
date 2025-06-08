"""
Statistics service - handles team standings and player leaderboards.
"""

from typing import Any, Dict, List

from sqlmodel import Session, func, select

from db.models import PlayerBoxScore, TeamBoxScore

from .game_service import GameService


class StatsService:
    """Service for calculating and retrieving game statistics."""

    def __init__(self, game_service: GameService):
        self.game_service = game_service
        self.engine = game_service.engine

    def get_team_standings(self) -> List[Dict[str, Any]]:
        """Calculate team standings with wins, losses, and percentages."""
        with Session(self.engine) as session:
            # Get team basic stats
            teams_query = select(
                TeamBoxScore.team_id,
                TeamBoxScore.team_name,
                func.count(TeamBoxScore.id).label("games_played"),
                func.sum(TeamBoxScore.final_score).label("points_for"),
            ).group_by(TeamBoxScore.team_id, TeamBoxScore.team_name)

            teams = session.exec(teams_query).all()

            if not teams:
                return []

            standings_data = []
            for team in teams:
                wins = self._calculate_team_wins(session, team.team_id)
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

            # Sort by win percentage, then by total points
            return sorted(standings_data, key=lambda x: (x["Win %"], x["Points"]), reverse=True)

    def _calculate_team_wins(self, session: Session, team_id: int) -> int:
        """Calculate wins for a specific team."""
        wins = 0
        team_games = session.exec(select(TeamBoxScore).where(TeamBoxScore.team_id == team_id)).all()

        for game in team_games:
            opponent = session.exec(
                select(TeamBoxScore).where(TeamBoxScore.game_id == game.game_id, TeamBoxScore.team_id != game.team_id)
            ).first()

            if opponent and game.final_score > opponent.final_score:
                wins += 1

        return wins

    def get_player_leaderboard(self, stat: str = "points", min_games: int = 1) -> List[Dict[str, Any]]:
        """Get player leaderboard for specified statistic."""
        if not hasattr(PlayerBoxScore, stat):
            raise ValueError(f"Invalid statistic: {stat}")

        with Session(self.engine) as session:
            query = (
                select(
                    PlayerBoxScore.player_id,
                    PlayerBoxScore.media_name,  # CHANGED FROM player_name
                    func.avg(getattr(PlayerBoxScore, stat)).label("avg_stat"),
                    func.count(PlayerBoxScore.id).label("games_played"),
                )
                .group_by(PlayerBoxScore.player_id, PlayerBoxScore.media_name)  # CHANGED FROM player_name
                .having(func.count(PlayerBoxScore.id) >= min_games)
                .order_by(func.avg(getattr(PlayerBoxScore, stat)).desc())
            )

            results = session.exec(query).all()

            return [
                {
                    "Player": r.media_name,
                    f"Avg {stat.capitalize()}": round(r.avg_stat, 1),
                    "Games": r.games_played,
                }  # CHANGED FROM r.player_name
                for r in results
            ]

    def get_game_results(self) -> List[Dict[str, Any]]:
        """Get all game results with scores and completion status."""
        games = self.game_service.get_all_games()

        if not games:
            return []

        game_data = []
        for game in games:
            team_scores = self.game_service.get_team_box_scores(game.id)

            has_stats = "✅ Complete" if team_scores else "❌ Missing"
            score = ""

            if len(team_scores) >= 2:
                score = (
                    f"{team_scores[0].team_name} {team_scores[0].final_score} - "
                    f"{team_scores[1].final_score} {team_scores[1].team_name}"
                )

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

        return game_data


# Factory function
def create_stats_service(game_service: GameService) -> StatsService:
    """Create and return a StatsService instance."""
    return StatsService(game_service)
