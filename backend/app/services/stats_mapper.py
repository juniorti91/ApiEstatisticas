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
    }
