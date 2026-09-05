"""
Importa todos os models para que Base.metadata os enxergue na hora de
criar as tabelas (init_db), sem precisar de import manual em outros
arquivos.
"""
from app.models.league import League  # noqa: F401
from app.models.team import Team  # noqa: F401
from app.models.fixture import Fixture  # noqa: F401
from app.models.snapshot import MatchSnapshot  # noqa: F401
from app.models.team_form import TeamForm  # noqa: F401
from app.models.recommendation import Recommendation, RecommendationStatus  # noqa: F401
from app.models.odds_history import OddsHistoryPoint  # noqa: F401
