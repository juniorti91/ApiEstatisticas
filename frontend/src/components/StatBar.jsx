// Barra de preenchimento usada em TODOS os paineis de estatísticas
// (Dashboard e Partidas Ao Vivo) - um único lugar garante que o
// preenchimento tenha sempre a mesma leitura visual em qualquer tela.
//
// Antes, cada painel calculava a escala da barra usando só o maior valor
// ENTRE os dois lados daquela linha (Math.max(home, away, 1)). Isso
// parece razoável, mas quebra visualmente sempre que um lado é 0: por
// exemplo, mandante com 14 finalizações e visitante com 0 fazia a barra
// do mandante ficar 100% cheia (14 / 14) - a mesma barra 100% cheia que
// apareceria se ele tivesse feito só 5 finalizações e o visitante 0. O
// usuário via várias linhas diferentes (14, 6, 5, 0, 0, 0) e todas as
// barras não-zero apareciam igualmente "cheias", sem nenhuma noção de
// magnitude real.
//
// A correção: cada tipo de estatística tem um teto de referência
// realista (REFERENCE_MAX abaixo, calibrado pelo que é normal ver numa
// partida de futebol) e a escala da barra é o maior valor entre esse
// teto e os valores reais dos dois lados - assim 14 finalizações enche
// bem mais a barra que 5, mesmo quando o adversário está zerado, e se um
// jogo excepcional superar o teto (ex: 30 finalizações), a escala se
// ajusta sozinha pra nunca cortar a barra.
export const REFERENCE_MAX = {
  total_shots: 25,
  shots_on_target: 12,
  shots_off_target: 15,
  shots_blocked: 10,
  shots_inside_box: 15,
  shots_outside_box: 10,
  xg: 4,
  corners: 14,
  yellow_cards: 6,
  red_cards: 2,
  fouls: 25,
  offsides: 8,
  // Adicionado junto com a tela "Comparativo Detalhado" (stat-comparison) -
  // faltava aqui porque "Ataques Perigosos" nunca tinha sido exibido com
  // StatRow antes; sem um teto proprio, cairia no DEFAULT_REFERENCE_MAX de
  // 10 e qualquer partida normal (que costuma passar de 20-30 por time)
  // deixaria a barra sempre 100% cheia dos dois lados, sem noção real de
  // quem esta pressionando mais.
  dangerous_attacks: 60,
  possession: 100,
  passes_total: 700,
  passes_accurate: 600,
  passes_pct: 100,
  goalkeeper_saves: 10,
  duels_total: 80,
  duels_won: 50,
  dribbles_attempts: 20,
  dribbles_success: 12,
  tackles_total: 30,
  interceptions: 15,
  passes_key: 10,
  fouls_committed: 15,
};

const DEFAULT_REFERENCE_MAX = 10;

export function Bar({ value, max, color, align }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div
      className={`flex-1 h-2 rounded-full bg-panel2 overflow-hidden flex ${
        align === "right" ? "justify-end" : ""
      }`}
    >
      <div
        // Preenchimento animado mais lento e suave (900ms, com desaceleracao
        // no final) em vez do "transition-all" padrao do Tailwind (150ms) -
        // a mudanca de tamanho da barra a cada atualizacao ficava abrupta
        // demais, quase um "pulo" em vez de um preenchimento visivel.
        className="h-full rounded-full transition-[width] duration-[900ms] ease-out"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  );
}

export function StatRow({ label, home, away, statKey }) {
  const referenceMax = statKey && REFERENCE_MAX[statKey] != null ? REFERENCE_MAX[statKey] : DEFAULT_REFERENCE_MAX;
  // A escala nunca fica menor que o teto de referência, mas também nunca
  // corta um valor real que o supere - só serve como "piso" pra não
  // inflar visualmente números pequenos.
  const max = Math.max(home, away, referenceMax);
  const formattedHome = Number.isInteger(home) ? home : home.toFixed(1);
  const formattedAway = Number.isInteger(away) ? away : away.toFixed(1);
  return (
    <div className="flex items-center gap-1.5 sm:gap-3">
      <span className="w-8 sm:w-10 text-right text-sm text-slate-200 shrink-0">{formattedHome}</span>
      <Bar value={home} max={max} color="#3b82f6" align="right" />
      <span className="w-24 sm:w-48 text-center text-[10px] sm:text-xs text-muted shrink-0 truncate">{label}</span>
      <Bar value={away} max={max} color="#ef4444" />
      <span className="w-8 sm:w-10 text-sm text-slate-200 shrink-0">{formattedAway}</span>
    </div>
  );
}
