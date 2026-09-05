"""
Traduz o formato bruto de `/fixtures/statistics` da API-Football (uma
lista de {"type": "...", "value": ...} por time) para os campos
estruturados do MatchSnapshot.

Fica isolado num modulo proprio porque e o unico lugar do sistema que
conhece os nomes exatos dos campos da API externa - se a API mudar o
nome de um campo, o ajuste e feito em um unico arquivo.
"""
from __future__ import annotations

from typing import Any


def _to_number(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("%", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0


_FIELD_MAP = {
    "Shots on Goal": "shots_on_target",
    "Shots off Goal": "shots_off_target",
    "Total Shots": "total_shots",
    "Fouls": "fouls",
    "Corner Kicks": "corners",
    "Offsides": "offsides",
    "Ball Possession": "possession",
    "Yellow Cards": "yellow_cards",
    "Red Cards": "red_cards",
    # Campos adicionados para a tela detalhada de "Partidas Ao Vivo" - todos
    # ja vem de graca no mesmo /fixtures/statistics chamado a cada ciclo de
    # coleta (nenhuma requisicao extra de API), so nao eram lidos ainda.
    "Blocked Shots": "shots_blocked",
    "Shots insidebox": "shots_inside_box",
    "Shots outsidebox": "shots_outside_box",
    "Total passes": "passes_total",
    "Passes accurate": "passes_accurate",
    "Passes %": "passes_pct",
    "Goalkeeper Saves": "goalkeeper_saves",
    # Gols esperados (xG): so algumas competicoes/planos da API-Football
    # expoem esse tipo - quando ausente, fica 0 (ver _to_number/extract_side).
    "expected_goals": "xg",
}


def extract_side(raw_stats: list[dict]) -> dict[str, float]:
    """Publico: usado tambem por team_form_service para ler o lado de um time isolado."""
    out = {v: 0.0 for v in _FIELD_MAP.values()}
    for item in raw_stats:
        key = _FIELD_MAP.get(item.get("type", ""))
        if key:
            out[key] = _to_number(item.get("value"))
    return out


def parse_fixture_statistics(
    raw_statistics: list[dict], home_team_api_id: int, away_team_api_id: int
) -> dict[str, float]:
    """
    Recebe o `response` cru de /fixtures/statistics (uma entrada por time)
    e devolve um dict pronto para instanciar/atualizar um MatchSnapshot.
    """
    home_side: dict[str, float] = {}
    away_side: dict[str, float] = {}

    for entry in raw_statistics:
        team_id = entry.get("team", {}).get("id")
        parsed = extract_side(entry.get("statistics", []))
        if team_id == home_team_api_id:
            home_side = parsed
        elif team_id == away_team_api_id:
            away_side = parsed

    def g(side: dict[str, float], key: str) -> float:
        return side.get(key, 0.0)

    # A API-Football (planos padrao) nao expoe "ataques perigosos" no
    # endpoint de estatisticas - usamos uma proxima heuristica a partir de
    # finalizacoes + escanteios apenas para alimentar o grafico de
    # evolucao, deixando isso documentado para quem for evoluir o motor.
    dangerous_home = g(home_side, "total_shots") * 2 + g(home_side, "corners")
    dangerous_away = g(away_side, "total_shots") * 2 + g(away_side, "corners")

    return {
        "possession_home": g(home_side, "possession"),
        "possession_away": g(away_side, "possession"),
        "shots_on_target_home": int(g(home_side, "shots_on_target")),
        "shots_on_target_away": int(g(away_side, "shots_on_target")),
        "shots_off_target_home": int(g(home_side, "shots_off_target")),
        "shots_off_target_away": int(g(away_side, "shots_off_target")),
        "total_shots_home": int(g(home_side, "total_shots")),
        "total_shots_away": int(g(away_side, "total_shots")),
        "corners_home": int(g(home_side, "corners")),
        "corners_away": int(g(away_side, "corners")),
        "yellow_cards_home": int(g(home_side, "yellow_cards")),
        "yellow_cards_away": int(g(away_side, "yellow_cards")),
        "red_cards_home": int(g(home_side, "red_cards")),
        "red_cards_away": int(g(away_side, "red_cards")),
        "fouls_home": int(g(home_side, "fouls")),
        "fouls_away": int(g(away_side, "fouls")),
        "offsides_home": int(g(home_side, "offsides")),
        "offsides_away": int(g(away_side, "offsides")),
        "dangerous_attacks_home": int(dangerous_home),
        "dangerous_attacks_away": int(dangerous_away),
        "shots_blocked_home": int(g(home_side, "shots_blocked")),
        "shots_blocked_away": int(g(away_side, "shots_blocked")),
        "shots_inside_box_home": int(g(home_side, "shots_inside_box")),
        "shots_inside_box_away": int(g(away_side, "shots_inside_box")),
        "shots_outside_box_home": int(g(home_side, "shots_outside_box")),
        "shots_outside_box_away": int(g(away_side, "shots_outside_box")),
        "passes_total_home": int(g(home_side, "passes_total")),
        "passes_total_away": int(g(away_side, "passes_total")),
        "passes_accurate_home": int(g(home_side, "passes_accurate")),
        "passes_accurate_away": int(g(away_side, "passes_accurate")),
        "passes_pct_home": g(home_side, "passes_pct"),
        "passes_pct_away": g(away_side, "passes_pct"),
        "goalkeeper_saves_home": int(g(home_side, "goalkeeper_saves")),
        "goalkeeper_saves_away": int(g(away_side, "goalkeeper_saves")),
        "xg_home": g(home_side, "xg"),
        "xg_away": g(away_side, "xg"),
    }


def aggregate_player_stats(
    raw_players: list[dict], home_team_api_id: int, away_team_api_id: int
) -> dict[str, Any]:
    """
    Recebe o `response` cru de /fixtures/players (uma entrada por time, com
    a lista de jogadores e suas estatisticas na partida) e devolve os
    totais agregados por time - duelos, dribles, desarmes, interceptacoes,
    passes-chave, faltas - mais os 3 jogadores mais bem avaliados de cada
    lado.

    So e chamado sob demanda, quando o usuario abre os detalhes de uma
    partida (endpoint /matches/{id}/detailed-stats) - nunca no ciclo de
    coleta automatico do collector.py, porque /fixtures/players custa uma
    requisicao de API inteira por partida e rodar isso a cada 5 minutos
    para todas as partidas monitoradas gastaria cota rapido demais.
    """

    def empty_side() -> dict[str, int]:
        return {
            "duels_total": 0,
            "duels_won": 0,
            "dribbles_attempts": 0,
            "dribbles_success": 0,
            "tackles_total": 0,
            "interceptions": 0,
            "passes_key": 0,
            "fouls_committed": 0,
            "fouls_drawn": 0,
        }

    sides = {home_team_api_id: empty_side(), away_team_api_id: empty_side()}
    ratings: dict[int, list[dict]] = {home_team_api_id: [], away_team_api_id: []}

    for team_entry in raw_players:
        team_id = team_entry.get("team", {}).get("id")
        if team_id not in sides:
            continue
        side = sides[team_id]
        for player_entry in team_entry.get("players", []):
            stats_list = player_entry.get("statistics") or []
            if not stats_list:
                continue
            st = stats_list[0] or {}

            duels = st.get("duels") or {}
            dribbles = st.get("dribbles") or {}
            tackles = st.get("tackles") or {}
            passes = st.get("passes") or {}
            fouls = st.get("fouls") or {}
            games = st.get("games") or {}

            side["duels_total"] += duels.get("total") or 0
            side["duels_won"] += duels.get("won") or 0
            side["dribbles_attempts"] += dribbles.get("attempts") or 0
            side["dribbles_success"] += dribbles.get("success") or 0
            side["tackles_total"] += tackles.get("total") or 0
            side["interceptions"] += tackles.get("interceptions") or 0
            side["passes_key"] += passes.get("key") or 0
            side["fouls_committed"] += fouls.get("committed") or 0
            side["fouls_drawn"] += fouls.get("drawn") or 0

            rating = _to_number(games.get("rating")) or None
            minutes_played = games.get("minutes") or 0
            if rating and minutes_played > 0:
                player = player_entry.get("player") or {}
                ratings[team_id].append(
                    {
                        "name": player.get("name") or "?",
                        "rating": rating,
                        "photo": player.get("photo") or "",
                    }
                )

    def top3(team_id: int) -> list[dict]:
        return sorted(ratings.get(team_id, []), key=lambda p: p["rating"], reverse=True)[:3]

    return {
        "home": sides[home_team_api_id],
        "away": sides[away_team_api_id],
        "top_players_home": top3(home_team_api_id),
        "top_players_away": top3(away_team_api_id),
    }
