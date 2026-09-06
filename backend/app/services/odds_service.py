"""
Busca e interpreta odds ao vivo (in-play) da API-Football.

Usa o endpoint /odds/live (nao o /odds de pre-jogo - esse fica fixo desde
o apito inicial e nunca muda durante a partida, o que nao serve pra um
app que promete odd "ao vivo de verdade"). Confirmado com uma chamada de
teste real (script inspect_live_odds.py) que /odds/live:
  - devolve numa unica chamada TODAS as partidas em andamento agora (nao
    precisa de 1 chamada por partida como o /odds de pre-jogo);
  - nao agrupa por "bookmakers" como o /odds - os mercados vem direto
    numa lista "odds" (cada um com id/name/values);
  - a "linha" de mercados tipo Over/Under vem no campo "handicap" de cada
    value, SEPARADO do texto da selecao (que e so "Over"/"Under") - ao
    contrario do /odds de pre-jogo, onde a linha as vezes vinha embutida
    no proprio texto (ex: "Over 2.5");
  - cada value avisa se esta suspenso agora (`suspended: true` - mercado
    pausado, ex: bola parada perigosa) - uma odd suspensa NAO e uma odd
    real disponivel pra apostar e deve ser ignorada.

O plano contratado pode nao trazer odds ao vivo pra toda partida/mercado
(comum nos primeiros minutos, ou em ligas menores). Para o motor de
recomendacao nunca travar por causa disso, quando a odd real nao e
encontrada usamos uma "odd justa" sintetica derivada da probabilidade
estimada com uma margem de casa padrao - e deixamos isso explicito no
campo `source` para nao confundir odd real com estimativa.
"""
from __future__ import annotations

import logging

from app.services.api_football_client import ApiFootballError, api_football_client

logger = logging.getLogger("betanalyzer.odds")

HOUSE_MARGIN = 0.06  # margem tipica de casa de apostas, usada so na odd sintetica


async def fetch_live_odds_by_fixture() -> dict[int, list[dict]]:
    """Busca as odds ao vivo de TODAS as partidas em andamento agora numa
    unica chamada de API e organiza num dict {api_fixture_id: [mercados]}
    pra consulta rapida por partida no motor de recomendacao - evita
    gastar 1 chamada de API por partida monitorada a cada ciclo."""
    try:
        raw = await api_football_client.live_odds()
    except ApiFootballError as exc:
        logger.info("Odds ao vivo indisponiveis neste ciclo: %s", exc)
        return {}

    by_fixture: dict[int, list[dict]] = {}
    for item in raw:
        fixture_id = item.get("fixture", {}).get("id")
        if fixture_id is not None:
            by_fixture[fixture_id] = item.get("odds", [])
    return by_fixture


def find_live_odd(
    live_markets: list[dict],
    market_keywords: list[str],
    selection_keywords: list[str],
    target_line: float | None = None,
    exclude_keywords: list[str] | None = None,
    max_line_diff: float = 1.5,
) -> tuple[float, float | None, str] | None:
    """Procura, na lista de mercados ao vivo de uma partida (formato
    /odds/live - ver docstring do modulo), uma odd cujo nome de mercado
    bata com market_keywords (e NAO bata com exclude_keywords, usado pra
    nao confundir um mercado do jogo inteiro com sua variante "1st Half"/
    "2nd Half") e cuja selecao bata com selection_keywords.

    Quando target_line e informado (mercados Over/Under com uma linha,
    tipo "mais de 2.5 gols"), a linha normalmente NAO vem no texto da
    selecao (que e so "Over"/"Under") e sim no campo "handicap" de cada
    value - entao escolhemos o value cujo handicap mais se aproxima da
    linha calculada, entre os que batem com market/selection e nao estao
    suspensos. Quando target_line e None (ex: "Ambos Marcam - Nao", que
    nao tem linha), retorna a primeira selecao valida encontrada.

    Ignora values com suspended=True: um mercado suspenso esta
    momentaneamente pausado pela casa (ex: bola parada perigosa) e nao e
    uma odd real disponivel pra apostar agora.

    Retorna (odd, handicap_real, nome_do_mercado_real) quando acha algo
    aproveitavel, ou None quando nao acha nada. IMPORTANTE (bug corrigido
    aqui): se a linha real mais proxima disponivel no mercado ao vivo
    estiver mais longe do que max_line_diff da linha calculada, descarta
    o resultado em vez de devolver essa odd - caso contrario o chamador
    acabava exibindo um texto tipo "Mais de 3.5 Gols" colado a uma odd
    que na verdade era de uma linha bem mais alta (ex: 8.5), o que
    produz uma odd "ao vivo" tecnicamente real porem visivelmente sem
    sentido pro texto exibido (foi exatamente o caso reportado: "ODD
    ATUAL 23.00" pra "Mais de 3.5 Gols" aos 68'-85' com o jogo ja em 3
    gols - nao deu tempo de confirmar com o payload real porque a
    partida acabou antes, entao esse limite e uma protecao por design,
    nao 100% comprovada pra esse caso especifico). Quando aceita, o
    chamador deve usar o handicap_real devolvido como a linha
    efetivamente exibida (e recalcular a probabilidade em cima dela),
    nunca a linha calculada internamente, pra nunca descolar de novo o
    texto da odd real. O nome_do_mercado_real devolvido tambem e
    guardado na justificativa da recomendacao (ver recommendation_engine)
    pra qualquer proxima odd estranha poder ser investigada direto no
    historico salvo, sem precisar correr contra o relogio da partida de
    novo tentando capturar o payload ao vivo antes dela acabar.
    """
    exclude_keywords = exclude_keywords or []
    best_odd: float | None = None
    best_diff: float | None = None
    best_handicap: float | None = None
    best_market_name: str | None = None

    for market in live_markets:
        market_name_raw = market.get("name") or ""
        market_name = market_name_raw.lower()
        if not any(k in market_name for k in market_keywords):
            continue
        if any(k in market_name for k in exclude_keywords):
            continue

        for value in market.get("values", []):
            if value.get("suspended"):
                continue
            value_name = (value.get("value") or "").lower()
            if not any(k in value_name for k in selection_keywords):
                continue
            try:
                odd = float(value.get("odd"))
            except (TypeError, ValueError):
                continue

            if target_line is None:
                return odd, None, market_name_raw

            try:
                handicap = float(value.get("handicap"))
            except (TypeError, ValueError):
                continue
            diff = abs(handicap - target_line)
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_odd = odd
                best_handicap = handicap
                best_market_name = market_name_raw

    if best_odd is None:
        return None
    if target_line is not None and best_diff is not None and best_diff > max_line_diff:
        logger.info(
            "Odd ao vivo achada (mercado real='%s', mercados_procurados=%s) mas linha real "
            "mais proxima (%.2f) esta longe demais da calculada (%.2f, diff=%.2f > max %.2f) "
            "- descartando pra nao exibir odd descolada do texto da recomendacao.",
            best_market_name, market_keywords, best_handicap, target_line, best_diff, max_line_diff,
        )
        return None
    return best_odd, best_handicap, best_market_name or ""


def synthetic_fair_odd(estimated_probability: float) -> float:
    prob = max(0.03, min(0.97, estimated_probability))
    fair = 1 / prob
    with_margin = fair * (1 - HOUSE_MARGIN)
    return round(max(1.05, with_margin), 2)
