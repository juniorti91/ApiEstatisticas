"""
Schemas da tela detalhada de "Partidas Ao Vivo" (GET
/api/matches/{id}/detailed-stats).

Separado dos schemas normais de snapshot porque combina dois tipos de
dado com custo de API bem diferente: os campos do snapshot mais recente
(gratis - ja vem do ciclo de coleta normal a cada 5 min) e os agregados
de jogador (duelos, dribles, notas - custam 1 requisicao extra, feita na
hora em que o usuario abre a tela).
"""
from pydantic import BaseModel


class PlayerRatingOut(BaseModel):
    name: str
    rating: float
    photo: str = ""


class TeamDetailedStats(BaseModel):
    # Do snapshot mais recente - finalizacoes detalhadas, passes, goleiro,
    # xG. Sem custo extra de API (mesmo /fixtures/statistics do ciclo
    # normal de coleta).
    shots_blocked: int = 0
    shots_inside_box: int = 0
    shots_outside_box: int = 0
    passes_total: int = 0
    passes_accurate: int = 0
    passes_pct: float = 0
    goalkeeper_saves: int = 0
    xg: float = 0

    # Agregado sob demanda de /fixtures/players - duelos, dribles, desarmes,
    # interceptacoes, passes-chave, faltas.
    duels_total: int = 0
    duels_won: int = 0
    dribbles_attempts: int = 0
    dribbles_success: int = 0
    tackles_total: int = 0
    interceptions: int = 0
    passes_key: int = 0
    fouls_committed: int = 0
    fouls_drawn: int = 0


class DetailedMatchStats(BaseModel):
    home: TeamDetailedStats
    away: TeamDetailedStats
    top_players_home: list[PlayerRatingOut] = []
    top_players_away: list[PlayerRatingOut] = []
    # False quando a API-Football ainda nao tem dados de jogador para essa
    # partida (comum nos primeiros minutos) ou o plano/liga nao tem
    # cobertura - o frontend mostra um aviso em vez de zeros enganosos.
    player_stats_available: bool = True
