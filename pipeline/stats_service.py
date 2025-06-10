"""
Statistics service - handles team standings and player leaderboards.
"""

from typing import Any

from game_service import GameService
from sqlmodel import Session, func, select

from db.models import PlayerBoxScore, TeamBoxScore


class StatsService:
    """Service for calculating and retrieving game statistics."""

    def __init__(self, game_service: GameService):
        self.game_service = game_service
        self.engine = game_service.engine

    def get_team_standings(self) -> list[dict[str, Any]]:
        """Calculate team standings with wins, losses, and percentages."""
        with Session(self.engine) as session:
            # Get team basic stats
            teams_query = select(
                TeamBoxScore.team_id,
                TeamBoxScore.team_name,
                func.count(TeamBoxScore.id).label("games_played"),  # type: ignore
                func.sum(TeamBoxScore.final_score).label("points_for"),
                func.avg(TeamBoxScore.final_score).label("ppg"),
            ).group_by(TeamBoxScore.team_id, TeamBoxScore.team_name)

            teams = session.exec(teams_query).all()

            if not teams:
                return []

            standings_data = []
            for team in teams:
                # Calculate wins and opponent stats
                wins, points_against = self._calculate_team_record(session, team.team_id)
                losses = team.games_played - wins
                win_pct = wins / team.games_played if team.games_played > 0 else 0

                # Calculate point differential
                opp_ppg = points_against / team.games_played if team.games_played > 0 else 0
                diff = team.ppg - opp_ppg if team.ppg and opp_ppg else 0

                standings_data.append(
                    {
                        "Team": team.team_name,
                        "GP": team.games_played,
                        "W": wins,
                        "L": losses,
                        "PCT": f"{win_pct:.3f}",
                        "PF": team.points_for,
                        "PA": points_against,
                        "PPG": f"{team.ppg:.1f}" if team.ppg else "0.0",
                        "OPP PPG": f"{opp_ppg:.1f}",
                        "DIFF": f"{diff:+.1f}",
                    }
                )

            # Sort by win percentage, then by point differential
            return sorted(standings_data, key=lambda x: (float(x["PCT"]), float(x["DIFF"])), reverse=True)

    def _calculate_team_record(self, session: Session, team_id: int) -> tuple[int, int]:
        """Calculate wins and points against for a specific team."""
        wins = 0
        points_against = 0

        # Get all games for this team
        team_games = session.exec(select(TeamBoxScore).where(TeamBoxScore.team_id == team_id)).all()

        for game in team_games:
            # Get opponent's score in the same game
            opponent = session.exec(
                select(TeamBoxScore).where(TeamBoxScore.game_id == game.game_id, TeamBoxScore.team_id != game.team_id)
            ).first()

            if opponent:
                points_against += opponent.final_score
                if game.final_score > opponent.final_score:
                    wins += 1

        return wins, points_against

    def get_player_leaderboard(
        self, stat: str = "points", min_games: int = 1, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get player leaderboard for specified statistic."""
        # Validate stat name
        if not hasattr(PlayerBoxScore, stat):
            valid_stats = [
                "points",
                "assists",
                "total_rebounds",
                "steals",
                "blocks",
                "field_goal_percentage",
                "three_pointer_percentage",
                "free_throw_percentage",
                "plus_minus",
                "efficiency",
            ]
            raise ValueError(f"Invalid stat: {stat}. Choose from: {', '.join(valid_stats)}")

        with Session(self.engine) as session:
            # Build query
            query = (
                select(
                    PlayerBoxScore.player_id,
                    PlayerBoxScore.media_name,
                    func.avg(getattr(PlayerBoxScore, stat)).label("avg_stat"),
                    func.sum(getattr(PlayerBoxScore, stat)).label("total_stat"),
                    func.count(PlayerBoxScore.id).label("games_played"),  # type: ignore
                    func.sum(PlayerBoxScore.minutes).label("total_minutes"),
                )
                .group_by(PlayerBoxScore.player_id, PlayerBoxScore.media_name)
                .having(func.count(PlayerBoxScore.id) >= min_games)  # type: ignore
                .order_by(func.avg(getattr(PlayerBoxScore, stat)).desc())
            )

            if limit:
                query = query.limit(limit)

            results = session.exec(query).all()

            # Format results based on stat type
            leaderboard = []
            for r in results:
                entry = {
                    "Rank": len(leaderboard) + 1,
                    "Player": r.media_name,
                    "GP": r.games_played,
                    "MIN": f"{r.total_minutes:.1f}",
                }

                # Format stat based on type
                if stat.endswith("percentage"):
                    entry[f"AVG {stat.upper().replace('_', ' ')}"] = f"{r.avg_stat:.1%}"
                elif stat in ["plus_minus", "efficiency"]:
                    entry[f"AVG {stat.upper().replace('_', ' ')}"] = f"{r.avg_stat:+.1f}"
                else:
                    entry[f"AVG {stat.upper().replace('_', ' ')}"] = f"{r.avg_stat:.1f}"
                    entry["TOTAL"] = int(r.total_stat)

                leaderboard.append(entry)

            return leaderboard

    def get_team_leaders(self, team_id: int, stat: str = "points") -> list[dict[str, Any]]:
        """Get statistical leaders for a specific team."""
        if not hasattr(PlayerBoxScore, stat):
            raise ValueError(f"Invalid statistic: {stat}")

        with Session(self.engine) as session:
            query = (
                select(
                    PlayerBoxScore.media_name,
                    func.avg(getattr(PlayerBoxScore, stat)).label("avg_stat"),
                    func.count(PlayerBoxScore.id).label("games_played"),  # type: ignore
                )
                .where(PlayerBoxScore.team_id == team_id)
                .group_by(PlayerBoxScore.player_id, PlayerBoxScore.media_name)  # type: ignore
                .order_by(func.avg(getattr(PlayerBoxScore, stat)).desc())
                .limit(5)
            )

            results = session.exec(query).all()

            return [
                {
                    "Player": r.media_name,  # type: ignore
                    f"Avg {stat.capitalize()}": f"{r.avg_stat:.1f}",  # type: ignore
                    "Games": r.games_played,  # type: ignore
                }
                for r in results
            ]

    def get_game_results(self) -> list[dict[str, Any]]:
        """Get all game results with scores and completion status."""
        games = self.game_service.get_all_games()

        if not games:
            return []

        game_data = []
        for game in games:
            team_scores = self.game_service.get_team_box_scores(game.id)  # type: ignore

            status = "✅" if team_scores else "⏳"
            score = "—"
            winner = ""

            if len(team_scores) >= 2:
                team1, team2 = team_scores[0], team_scores[1]
                score = f"{team1.team_abbreviation} {team1.final_score} - {team2.final_score} {team2.team_abbreviation}"

                if team1.final_score > team2.final_score:
                    winner = team1.team_abbreviation
                elif team2.final_score > team1.final_score:
                    winner = team2.team_abbreviation
                else:
                    winner = "TIE"

            game_data.append(
                {
                    "Game": f"#{game.game_number}",
                    "Date": game.date.strftime("%b %d"),
                    "Time": game.start_time.strftime("%I:%M %p"),
                    "Venue": game.location or "TBD",
                    "Score": score,
                    "Winner": winner,
                    "Status": status,
                }
            )

        return game_data

    def get_recent_performances(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get recent standout performances."""
        with Session(self.engine) as session:
            query = (
                select(
                    PlayerBoxScore.media_name,
                    PlayerBoxScore.points,
                    PlayerBoxScore.total_rebounds,
                    PlayerBoxScore.assists,
                    PlayerBoxScore.game_id,
                )  # type: ignore
                .where(PlayerBoxScore.minutes > 0)
                .order_by(PlayerBoxScore.points.desc())  # type: ignore
                .limit(limit)
            )

            results = session.exec(query).all()

            performances = []
            for r in results:
                # Get game info
                game = self.game_service.get_game_by_id(r.game_id)
                if game:
                    performances.append(
                        {
                            "Player": r.media_name,
                            "Game": f"#{game.game_number}",
                            "Date": game.date.strftime("%b %d"),
                            "PTS": r.points,
                            "REB": r.total_rebounds,
                            "AST": r.assists,
                            "Total": r.points + r.total_rebounds + r.assists,
                        }
                    )

            return performances


# Factory function
def create_stats_service(game_service: GameService) -> StatsService:
    """Create and return a StatsService instance."""
    return StatsService(game_service)
