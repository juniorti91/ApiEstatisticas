"""
Funcoes estatisticas puras usadas pelo motor de recomendacao.

Mantidas sem dependencias externas (numpy/scipy) de proposito: sao poucas
linhas, faceis de testar isoladamente e nao pesam no tempo de start do
servico - alinhado com a diretriz de performance do projeto.
"""
from __future__ import annotations

import math


def poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam**k) / math.factorial(k)


def poisson_prob_over(line: float, lam: float) -> float:
    """
    P(X > line) para X ~ Poisson(lam). `line` normalmente termina em .5
    (ex: 5.5 escanteios), entao basta somar a cauda a partir do proximo
    inteiro.
    """
    if lam <= 0:
        return 0.0
    threshold = math.floor(line) + 1
    # cauda = 1 - CDF(threshold - 1)
    cdf = 0.0
    for k in range(threshold):
        cdf += poisson_pmf(k, lam)
    return max(0.0, min(1.0, 1 - cdf))


def poisson_prob_under(line: float, lam: float) -> float:
    return max(0.0, min(1.0, 1 - poisson_prob_over(line, lam)))


def project_to_full_match(current_value: float, elapsed_minutes: int, match_length: int = 90) -> float:
    """
    Projeta um total de fim de jogo a partir do ritmo atual (ex: 4
    escanteios aos 32min -> projeta ~11.25 a 90min), com piso de 1 minuto
    para evitar divisao por zero logo no inicio da partida.
    """
    minutes = max(elapsed_minutes, 1)
    rate_per_minute = current_value / minutes
    return rate_per_minute * match_length


def blended_projection(
    live_projection: float,
    historical_average: float,
    elapsed_minutes: int,
    ramp_minutes: int = 90,
) -> float:
    """
    Combina a projecao ao vivo com a media historica do time. No inicio da
    partida (poucos minutos jogados) a amostra ao vivo e pouco confiavel,
    entao pesamos mais a media historica; conforme o jogo avanca, o peso
    migra gradualmente para o que esta acontecendo ao vivo, atingindo 100%
    de peso na projecao ao vivo apenas quando a partida termina (`ramp_minutes`
    = duracao total, 90 por padrao) - o que tambem faz sentido no limite,
    pois nesse ponto a "projecao" ao vivo e o proprio resultado final.
    """
    live_weight = min(1.0, elapsed_minutes / ramp_minutes)
    hist_weight = 1 - live_weight
    return (live_projection * live_weight) + (historical_average * hist_weight)


def implied_probability(odd: float) -> float:
    if odd <= 1.0:
        return 1.0
    return 1 / odd


def expected_value_pct(estimated_probability: float, odd: float) -> float:
    """EV% = (prob estimada * odd - 1) * 100"""
    return (estimated_probability * odd - 1) * 100


def confidence_stars(estimated_probability: float, implied_prob: float) -> int:
    """
    Converte a vantagem (edge) entre a probabilidade estimada e a
    implicita pela odd em uma nota de 1 a 5 estrelas, usada como atalho
    visual de confianca no dashboard.
    """
    edge = estimated_probability - implied_prob
    if edge >= 0.20:
        return 5
    if edge >= 0.12:
        return 4
    if edge >= 0.06:
        return 3
    if edge >= 0.0:
        return 2
    return 1
