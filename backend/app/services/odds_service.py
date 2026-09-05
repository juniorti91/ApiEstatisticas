"""
Busca e interpreta odds ao vivo da API-Football.

O plano contratado pode nao trazer odds "in-play" para todo mercado (isso
varia por bookmaker/liga). Para o motor de recomendacao nunca travar por
causa disso, quando a odd real nao e encontrada usamos uma "odd justa"
sintetica derivada da probabilidade estimada com uma margem de casa
padrao - e deixamos isso explicito no campo `source` para nao confundir
odd real com estimativa.
"""
from __future__ import annotations

import logging

from app.services.api_football_client import ApiFootballError, api_football_client

logger = logging.getLogger("betanalyzer.odds")

HOUSE_MARGIN = 0.06  # margem tipica de casa de apostas, usada so na odd sintetica


async def fetch_raw_odds(api_fixture_id: int) -> list[dict]:
    try:
        return await api_football_client.odds_for_fixture(api_fixture_id)
    except ApiFootballError as exc:
        logger.info("Odds indisponiveis para fixture %s: %s", api_fixture_id, exc)
        return []


def find_odd(raw_odds: list[dict], market_keywords: list[str], selection_keywords: list[str]) -> float | None:
    """Procura, nos bookmakers retornados, uma odd cujo nome de mercado e
    de selecao batam (case-insensitive, por substring) com os keywords."""
    for entry in raw_odds:
        for bookmaker in entry.get("bookmakers", []):
            for bet in bookmaker.get("bets", []):
                bet_name = (bet.get("name") or "").lower()
                if not any(k in bet_name for k in market_keywords):
                    continue
                for value in bet.get("values", []):
                    value_name = (value.get("value") or "").lower()
                    if any(k in value_name for k in selection_keywords):
                        try:
                            return float(value.get("odd"))
                        except (TypeError, ValueError):
                            continue
    return None


def synthetic_fair_odd(estimated_probability: float) -> float:
    prob = max(0.03, min(0.97, estimated_probability))
    fair = 1 / prob
    with_margin = fair * (1 - HOUSE_MARGIN)
    return round(max(1.05, with_margin), 2)
