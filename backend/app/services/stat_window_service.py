"""
Compara estatisticas de uma partida "zerando o relogio" numa janela recente
(ex: so os ultimos 10 minutos) em vez do acumulado desde o apito inicial -
usado na tela "Comparativo Detalhado" do frontend. Nao faz nenhuma chamada
nova a API-Football: reusa os snapshots que o collector ja salva a cada
ciclo (ver services/collector.py), calculando a DIFERENCA entre o snapshot
mais recente e o snapshot mais proximo (por baixo) do inicio da janela
pedida.

A maioria das metricas (chutes, escanteios, cartoes, passes, duelos etc) e
CUMULATIVA - so cresce durante a partida, nunca "volta" no meio do jogo -
entao dá pra calcular "quanto aconteceu nos ultimos N minutos" com uma
subtracao simples: delta = valor_no_snapshot_atual - valor_no_snapshot_da_
base_da_janela.

Duas metricas NAO sao simplesmente subtraiveis porque sao percentuais, nao
contagens:
  - posse de bola: a API reporta acumulado desde o apito inicial, e nao ha
    como recalcular so pra uma janela sem o dado bruto minuto a minuto (que
    a API nao fornece) - por isso so aparece na visao "jogo todo";
  - precisao de passes: essa SIM dá pra recalcular corretamente pra uma
    janela, mas nao subtraindo os dois percentuais (58% - 52% nao significa
    nada) - o jeito certo e dividir o DELTA de passes certos pelo DELTA de
    passes totais na janela.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.snapshot import MatchSnapshot

# (atributo-base no MatchSnapshot - vira f"{attr}_home"/f"{attr}_away" -,
# rotulo exibido). Mesma ordem em que aparecem na tela.
_CUMULATIVE_FIELDS: list[tuple[str, str]] = [
    ("total_shots", "Finalizações"),
    ("shots_on_target", "Finalizações no Gol"),
    ("shots_off_target", "Finalizações para Fora"),
    ("shots_blocked", "Chutes Bloqueados"),
    ("corners", "Escanteios"),
    ("fouls", "Faltas"),
    ("yellow_cards", "Cartões Amarelos"),
    ("red_cards", "Cartões Vermelhos"),
    ("shots_inside_box", "Finalizações de Dentro da Área"),
    ("shots_outside_box", "Finalizações de Fora da Área"),
    ("goalkeeper_saves", "Defesas do Goleiro"),
    ("passes_total", "Passes"),
    ("passes_accurate", "Passes Concluídos"),
    # "passes_pct" (Precisao de Passes) e inserida logo apos "Passes
    # Concluidos" abaixo, calculada a parte - ver _pct_from_deltas.
    ("dribbles_attempts", "Dribles"),
    ("dribbles_success", "Dribles Bem-sucedidos"),
    ("duels_total", "Duelos Totais"),
    ("duels_won", "Duelos Ganhos"),
    ("tackles_total", "Desarmes"),
    ("interceptions", "Interceptações"),
    ("dangerous_attacks", "Ataques Perigosos"),
    ("offsides", "Impedimentos"),
    ("passes_key", "Passes-Chave"),
]


@dataclass
class StatRow:
    key: str
    label: str
    home: float
    away: float


def _raw(snapshot: MatchSnapshot, attr: str) -> float:
    return getattr(snapshot, attr, None) or 0


def _delta(current: MatchSnapshot, baseline: MatchSnapshot | None, attr: str) -> float:
    current_value = _raw(current, attr)
    if baseline is None:
        return current_value
    baseline_value = _raw(baseline, attr)
    # Nunca negativo: uma contagem cumulativa nao "volta" no meio do jogo -
    # se a API corrigir algum numero pra baixo entre duas coletas (raro,
    # mas ja vimos com xG), zeramos em vez de mostrar uma janela negativa
    # sem sentido nenhum pro usuario.
    return max(0.0, current_value - baseline_value)


def _pct_from_deltas(accurate_delta: float, total_delta: float) -> float:
    if total_delta <= 0:
        return 0.0
    return round((accurate_delta / total_delta) * 100, 1)


def _find_baseline(snapshots: list[MatchSnapshot], target_minute: float) -> MatchSnapshot | None:
    """Snapshot mais recente com minuto <= target_minute (a "foto" mais
    proxima disponivel do inicio da janela pedida). None quando nem o
    snapshot mais antigo que temos chega tao pra tras - nesse caso a janela
    pedida vira, na pratica, "desde o primeiro dado que coletamos", que e
    exatamente o comportamento do "jogo todo" para partidas ainda no
    comeco."""
    candidates = [s for s in snapshots if s.minute <= target_minute]
    if not candidates:
        return None
    return max(candidates, key=lambda s: s.minute)


def build_stat_rows(
    snapshots: list[MatchSnapshot], window_minutes: int | None
) -> tuple[list[StatRow], int, int]:
    """snapshots deve vir ordenado por minuto crescente (mesma ordem que
    GET /api/matches/{id}/snapshots ja devolve). window_minutes=None e o
    "jogo todo" (acumulado desde o apito inicial); um numero (5/10/15)
    recalcula so pra essa janela recente. Retorna (linhas, minuto inicial
    da janela, minuto final) - os dois ultimos servem so pra a tela poder
    mostrar "de X' a Y'" quando quiser."""
    if not snapshots:
        return [], 0, 0

    current = snapshots[-1]
    to_minute = current.minute

    if window_minutes is None or window_minutes <= 0:
        baseline = None
        from_minute = 0
    else:
        target = max(0, to_minute - window_minutes)
        baseline = _find_baseline(snapshots, target)
        from_minute = baseline.minute if baseline else 0

    rows: list[StatRow] = []

    # Posse de bola so faz sentido no acumulado do jogo todo - ver docstring
    # do modulo pra o motivo de nao dar pra recalcular numa janela. Testa
    # window_minutes diretamente (nao "baseline is None"): mesmo quando uma
    # janela pedida (ex: ultimos 15min) cai pra tras do primeiro snapshot
    # que existe e a busca por baseline devolve None, ainda e uma janela
    # de verdade, so que sem base suficiente - nao vira "jogo todo".
    if window_minutes is None or window_minutes <= 0:
        rows.append(
            StatRow(
                key="possession",
                label="Posse de Bola (%)",
                home=round(_raw(current, "possession_home"), 1),
                away=round(_raw(current, "possession_away"), 1),
            )
        )

    rows.append(
        StatRow(
            key="xg",
            label="Gols Esperados (xG)",
            home=round(_delta(current, baseline, "xg_home"), 2),
            away=round(_delta(current, baseline, "xg_away"), 2),
        )
    )

    for attr, label in _CUMULATIVE_FIELDS:
        home = _delta(current, baseline, f"{attr}_home")
        away = _delta(current, baseline, f"{attr}_away")
        rows.append(StatRow(key=attr, label=label, home=home, away=away))

        if attr == "passes_accurate":
            total_home = _delta(current, baseline, "passes_total_home")
            total_away = _delta(current, baseline, "passes_total_away")
            rows.append(
                StatRow(
                    key="passes_pct",
                    label="Precisão de Passes (%)",
                    home=_pct_from_deltas(home, total_home),
                    away=_pct_from_deltas(away, total_away),
                )
            )

    return rows, from_minute, to_minute
