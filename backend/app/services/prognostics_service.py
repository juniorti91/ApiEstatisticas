"""
Modelos de "prognostico" da partida - probabilidade de vitoria (1X2),
probabilidade de proximo gol, probabilidade de gol nos proximos 5/10min,
indice de Momentum (0-100) e um resumo do "indice de anomalia" (desempenho
atual vs media historica).

Vieram do documento de especificacao original do projeto (conversa com
outra IA descrevendo a arquitetura desejada) - a maioria dos pesos/formulas
descritos la usa estatisticas que a API-Football NAO fornece (xGOT,
sprints, "entradas no terco final", "recuperacoes altas" como categoria
separada de recuperacao normal) - aqui os pesos foram redistribuidos pra
usar SO o que o collector ja coleta de verdade (ver MatchSnapshot), sem
inventar numero nenhum. Cada func├žao abaixo documenta essa adaptacao.

NAO faz nenhuma chamada nova a API-Football: tudo calculado em cima dos
snapshots (a cada 5min, ja salvos por app/services/collector.py) e do
TeamForm (media das ultimas partidas, ja calculado por
app/services/team_form_service.py) - mesmo dado que o motor de
recomendacao (recommendation_engine.py) ja usa.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.stats_math import blended_projection, poisson_pmf, project_to_full_match
from app.models.snapshot import MatchSnapshot
from app.models.team_form import TeamForm

# Janela usada pro indice de Momentum "nao acumulativo" (ver secao 3 do
# documento: momentum deve refletir o RITMO recente, nao o total acumulado
# desde o apito inicial) - 15min cobre 3 ciclos de coleta (a cada 5min),
# amostra pequena o bastante pra reagir rapido mas grande o bastante pra
# nao virar ruido de um unico snapshot.
MOMENTUM_WINDOW_MINUTES = 15

# Pesos do indice de Momentum, adaptados do documento original. O
# documento pedia xGOT (15%), "acoes na area" (10%), "entradas no terco
# final" (5%) e "recuperacoes ALTAS" (5%) - nenhum desses existe na
# API-Football. O peso foi redistribuido assim:
#   - xGOT (15%) -> somado ao xG (25% + 15% = 30%), ja que os dois medem a
#     mesma coisa (qualidade das chances), so que xGOT e so pra chutes no
#     alvo - sem esse recorte, o xG geral absorve o peso todo.
#   - "acoes na area" (10%) -> shots_inside_box como proxy (chutes de
#     dentro da area sao a acao mais valiosa dentro da area) + metade do
#     peso de "entradas no terco final" (nao temos esse dado, mas
#     finalizacoes de dentro da area sao um proxy razoavel de presenca na
#     area). Total: 15%.
#   - "ataques perigosos" (8%) recebe a outra metade de "entradas no
#     terco final": 12%.
#   - "recuperacoes altas" (5%) vira so "recuperacoes" (interceptacoes +
#     desarmes) sem o recorte de "altas" (nao da pra saber em que terco do
#     campo aconteceu) - peso reduzido pra 3%, ja que e uma proxy mais
#     fraca do que o indicador original.
# Some 1.00 no total.
MOMENTUM_WEIGHTS: dict[str, float] = {
    "xg": 0.30,
    "shots_on_target": 0.20,
    "shots_inside_box": 0.15,
    "dangerous_attacks": 0.12,
    "corners": 0.08,
    "possession": 0.07,
    "passes_accurate": 0.05,
    "recoveries": 0.03,
}

# "Teto" de referencia pra cada componente numa janela de MOMENTUM_WINDOW_MINUTES
# minutos (ou nivel atual, no caso de posse) - calibrado por cima do que e
# considerado uma pressao MUITO forte de um time num trecho de 15min real,
# igual ao raciocinio do REFERENCE_MAX do frontend (StatBar.jsx). O valor
# normalizado nunca passa de 1.0 (um trecho ainda mais intenso so satura o
# componente, nao gera nota acima de 100).
MOMENTUM_REFERENCE_MAX: dict[str, float] = {
    "xg": 0.6,
    "shots_on_target": 5,
    "shots_inside_box": 6,
    "dangerous_attacks": 25,
    "corners": 4,
    "possession": 70,
    "passes_accurate": 90,
    "recoveries": 12,
}

# Estatisticas do "indice de anomalia" (secao 11 do documento) - so as que
# TEM media historica de verdade guardada em TeamForm (avg_shots,
# avg_shots_on_target, avg_corners, avg_possession). O documento tambem
# lista xG e "acoes na area" no exemplo, mas TeamForm nao guarda media
# historica de xG (exigiria buscar estatisticas detalhadas de cada jogo
# passado so pra isso - custo extra de API, fica pra decisao futura, igual
# outras extensoes ja adiadas neste projeto).
_ANOMALY_STATS: list[tuple[str, str, str]] = [
    ("Finalizações", "total_shots", "avg_shots"),
    ("Finalizações no Alvo", "shots_on_target", "avg_shots_on_target"),
    ("Escanteios", "corners", "avg_corners"),
]


@dataclass
class WinProbability:
    home: float
    draw: float
    away: float


@dataclass
class NextGoalProbability:
    home: float
    away: float


@dataclass
class GoalWindowProbability:
    home_5min: float
    away_5min: float
    home_10min: float
    away_10min: float


@dataclass
class MomentumResult:
    home: float | None
    away: float | None
    home_delta: float | None
    away_delta: float | None
    home_trend: str
    away_trend: str


@dataclass
class AnomalyRow:
    label: str
    home_pct: float | None
    away_pct: float | None


def _raw(snapshot: MatchSnapshot, attr: str) -> float:
    return getattr(snapshot, attr, None) or 0


def _delta(current: MatchSnapshot, baseline: MatchSnapshot | None, attr: str) -> float:
    """Mesma logica de app/services/stat_window_service.py - nunca
    negativo, ja que sao contadores cumulativos."""
    current_value = _raw(current, attr)
    if baseline is None:
        return current_value
    return max(0.0, current_value - _raw(baseline, attr))


def _find_snapshot_at_or_before(snapshots: list[MatchSnapshot], target_minute: float) -> MatchSnapshot | None:
    candidates = [s for s in snapshots if s.minute <= target_minute]
    if not candidates:
        return None
    return max(candidates, key=lambda s: s.minute)


# ---- Probabilidade de vitoria / proximo gol / gol nos proximos N min ----


def compute_remaining_goal_expectation(
    current_goals_home: int,
    current_goals_away: int,
    minute: int,
    home_form: TeamForm,
    away_form: TeamForm,
) -> tuple[float, float]:
    """Projeta quantos gols cada time ainda deve marcar ATE O FIM da
    partida (nao o total do jogo) - mistura o ritmo ao vivo com a media
    historica combinada (o proprio ataque do time e a defesa do
    adversario), mesmo raciocinio ja usado em
    recommendation_engine._total_goals_market, so que separado por time em
    vez de combinado."""
    minute = max(minute, 1)
    home_hist_expected = (home_form.avg_goals_scored + away_form.avg_goals_conceded) / 2
    away_hist_expected = (away_form.avg_goals_scored + home_form.avg_goals_conceded) / 2

    home_live_proj = project_to_full_match(current_goals_home, minute)
    away_live_proj = project_to_full_match(current_goals_away, minute)

    home_total_proj = blended_projection(home_live_proj, home_hist_expected, minute)
    away_total_proj = blended_projection(away_live_proj, away_hist_expected, minute)

    remaining_home = max(home_total_proj - current_goals_home, 0.05)
    remaining_away = max(away_total_proj - current_goals_away, 0.05)
    return remaining_home, remaining_away


def compute_win_probability(
    current_goals_home: int,
    current_goals_away: int,
    remaining_home: float,
    remaining_away: float,
    max_extra_goals: int = 8,
) -> WinProbability:
    """Distribuicao conjunta de gols adicionais de cada time (Poisson
    independente - simplificacao padrao pra esse tipo de modelo, mesma
    familia usada nas outras probabilidades do motor de recomendacao) -
    soma a massa de probabilidade de cada combinacao (i gols de casa mais,
    j gols de fora mais) no resultado final (vitoria casa / empate /
    vitoria fora). max_extra_goals=8 cobre com folga qualquer virada
    realista (a cauda alem disso e desprezivel, mas ainda assim
    normalizamos no final pra garantir que soma 100%)."""
    home_win = draw = away_win = 0.0
    for i in range(max_extra_goals + 1):
        p_i = poisson_pmf(i, remaining_home)
        final_home = current_goals_home + i
        for j in range(max_extra_goals + 1):
            p_j = poisson_pmf(j, remaining_away)
            joint = p_i * p_j
            final_away = current_goals_away + j
            if final_home > final_away:
                home_win += joint
            elif final_home == final_away:
                draw += joint
            else:
                away_win += joint

    total = home_win + draw + away_win
    if total <= 0:
        return WinProbability(home=1 / 3, draw=1 / 3, away=1 / 3)  # nunca deveria acontecer, fallback neutro
    return WinProbability(home=home_win / total, draw=draw / total, away=away_win / total)


def compute_next_goal_probability(remaining_home: float, remaining_away: float) -> NextGoalProbability:
    """Probabilidade de qual time marca o PROXIMO gol - resultado padrao
    pra duas "corridas" de Poisson independentes competindo: a chance de
    uma delas "chegar primeiro" e proporcional a sua taxa relativa
    (remaining_home / (remaining_home + remaining_away))."""
    total = remaining_home + remaining_away
    if total <= 0:
        return NextGoalProbability(home=0.5, away=0.5)
    return NextGoalProbability(home=remaining_home / total, away=remaining_away / total)


def compute_goal_window_probability(
    remaining_home: float, remaining_away: float, minute: int
) -> GoalWindowProbability:
    """P(pelo menos 1 gol nos proximos 5/10min) por time - distribui a
    expectativa de gols restantes igualmente pelos minutos que faltam
    (ritmo constante e a suposicao mais simples e defensavel sem um modelo
    minuto-a-minuto de verdade) e usa Poisson(0) pra achar a chance de
    NENHUM gol nessa janela, invertendo pra achar "pelo menos 1"."""
    minutes_left = max(90 - minute, 0)
    if minutes_left <= 0:
        return GoalWindowProbability(home_5min=0.0, away_5min=0.0, home_10min=0.0, away_10min=0.0)

    rate_home_per_min = remaining_home / minutes_left
    rate_away_per_min = remaining_away / minutes_left

    def prob_at_least_one(rate_per_min: float, window: int) -> float:
        effective_window = min(window, minutes_left)
        rate = rate_per_min * effective_window
        return round(1 - poisson_pmf(0, rate), 4)

    return GoalWindowProbability(
        home_5min=prob_at_least_one(rate_home_per_min, 5),
        away_5min=prob_at_least_one(rate_away_per_min, 5),
        home_10min=prob_at_least_one(rate_home_per_min, 10),
        away_10min=prob_at_least_one(rate_away_per_min, 10),
    )


# ---- Indice de Momentum (0-100), nao-acumulativo ----


def _momentum_component_value(current: MatchSnapshot, baseline: MatchSnapshot | None, side: str, key: str) -> float:
    if key == "possession":
        return _raw(current, f"possession_{side}")  # nivel atual - nao e cumulativo, nao tem "delta"
    if key == "recoveries":
        return _delta(current, baseline, f"interceptions_{side}") + _delta(
            current, baseline, f"tackles_total_{side}"
        )
    return _delta(current, baseline, f"{key}_{side}")


def compute_momentum_score(
    snapshots: list[MatchSnapshot], side: str, up_to_minute: float, window_minutes: int = MOMENTUM_WINDOW_MINUTES
) -> float | None:
    """Nota 0-100 de "pressao recente" de um time, olhando so os ultimos
    `window_minutes` (nao o jogo inteiro) - None quando ainda nao ha
    nenhum snapshot ate `up_to_minute`."""
    current = _find_snapshot_at_or_before(snapshots, up_to_minute)
    if current is None:
        return None

    baseline = _find_snapshot_at_or_before(snapshots, max(0, up_to_minute - window_minutes))
    if baseline is current:
        baseline = None  # janela maior que o historico disponivel - usa desde o inicio da partida

    score = 0.0
    for key, weight in MOMENTUM_WEIGHTS.items():
        value = _momentum_component_value(current, baseline, side, key)
        reference = MOMENTUM_REFERENCE_MAX[key]
        normalized = min(1.0, value / reference) if reference > 0 else 0.0
        score += weight * normalized
    return round(score * 100, 1)


def _momentum_trend(delta: float | None) -> str:
    if delta is None:
        return "indisponivel"
    if delta >= 10:
        return "subindo_forte"
    if delta >= 3:
        return "subindo"
    if delta <= -10:
        return "caindo_forte"
    if delta <= -3:
        return "caindo"
    return "estavel"


def compute_momentum(snapshots: list[MatchSnapshot]) -> MomentumResult:
    """Momentum atual de cada time MAIS a variacao (Momentum Δ) em relacao
    a janela anterior de mesmo tamanho - ver secao 3 do documento
    ("momentum nao deve ser acumulativo", precisa de uma nota de
    "velocidade" separada da nota de "forca atual"). Quando a partida
    ainda nao tem historico suficiente pra comparar duas janelas
    (comeco de jogo), o delta e trend vem como None/"indisponivel" em vez
    de um numero inventado."""
    if not snapshots:
        return MomentumResult(home=None, away=None, home_delta=None, away_delta=None, home_trend="indisponivel", away_trend="indisponivel")

    now_minute = snapshots[-1].minute
    home_now = compute_momentum_score(snapshots, "home", now_minute)
    away_now = compute_momentum_score(snapshots, "away", now_minute)

    prev_minute = now_minute - MOMENTUM_WINDOW_MINUTES
    home_prev = compute_momentum_score(snapshots, "home", prev_minute) if prev_minute >= 0 else None
    away_prev = compute_momentum_score(snapshots, "away", prev_minute) if prev_minute >= 0 else None

    home_delta = round(home_now - home_prev, 1) if home_now is not None and home_prev is not None else None
    away_delta = round(away_now - away_prev, 1) if away_now is not None and away_prev is not None else None

    return MomentumResult(
        home=home_now,
        away=away_now,
        home_delta=home_delta,
        away_delta=away_delta,
        home_trend=_momentum_trend(home_delta),
        away_trend=_momentum_trend(away_delta),
    )


# ---- Indice de Anomalia (versao resumida) ----


def compute_anomaly_summary(
    latest_snapshot: MatchSnapshot, minute: int, home_form: TeamForm, away_form: TeamForm
) -> list[AnomalyRow]:
    """% de quanto o RITMO projetado pra 90min (nao o valor bruto parcial)
    esta acima/abaixo da media historica do time - versao resumida do
    "indice de anomalia" do documento, usando so as estatisticas que
    TeamForm realmente guarda media historica (finalizacoes, finalizacoes
    no alvo, escanteios, posse)."""
    minute = max(minute, 1)

    def pct_diff(projected: float, historical: float) -> float | None:
        if historical <= 0:
            return None  # sem media historica confiavel pra comparar (time novo/sem amostra)
        return round(((projected - historical) / historical) * 100, 1)

    rows: list[AnomalyRow] = []
    for label, snapshot_key, form_attr in _ANOMALY_STATS:
        home_projected = project_to_full_match(_raw(latest_snapshot, f"{snapshot_key}_home"), minute)
        away_projected = project_to_full_match(_raw(latest_snapshot, f"{snapshot_key}_away"), minute)
        rows.append(
            AnomalyRow(
                label=label,
                home_pct=pct_diff(home_projected, getattr(home_form, form_attr)),
                away_pct=pct_diff(away_projected, getattr(away_form, form_attr)),
            )
        )

    # Posse ja e um nivel (%), nao um contador cumulativo - compara direto
    # com a media, sem projetar.
    rows.append(
        AnomalyRow(
            label="Posse de Bola",
            home_pct=pct_diff(_raw(latest_snapshot, "possession_home"), home_form.avg_possession),
            away_pct=pct_diff(_raw(latest_snapshot, "possession_away"), away_form.avg_possession),
        )
    )
    return rows
