import { Loader2 } from "lucide-react";
import { StatRow } from "./StatBar";

// Linhas que vem do snapshot (coleta automatica a cada 5 min, sem custo
// extra de API) - basicas + as novas adicionadas em stats_mapper.py.
const SNAPSHOT_ROWS = [
  { key: "total_shots", label: "Finalizações" },
  { key: "shots_on_target", label: "Finalizações no alvo" },
  { key: "shots_off_target", label: "Finalizações para fora" },
  { key: "shots_blocked", label: "Finalizações bloqueadas" },
  { key: "shots_inside_box", label: "Finalizações de dentro da área" },
  { key: "shots_outside_box", label: "Finalizações de fora da área" },
];

const XG_ROW = { key: "xg", label: "Gols esperados (xG)" };

const PASSES_ROWS = [
  { key: "passes_total", label: "Passes totais" },
  { key: "passes_accurate", label: "Passes certos" },
  { key: "passes_pct", label: "Precisão de passe (%)" },
];

const DISCIPLINE_ROWS = [
  { key: "corners", label: "Escanteios" },
  { key: "offsides", label: "Impedimentos" },
  { key: "fouls", label: "Faltas" },
  { key: "yellow_cards", label: "Cartões Amarelos" },
  { key: "red_cards", label: "Cartões Vermelhos" },
];

// Linhas que vem do agregado sob demanda de /fixtures/players (custam uma
// chamada de API na hora em que a tela e aberta - ver detailed prop).
const DUEL_ROWS = [
  { key: "duels_total", label: "Duelos disputados" },
  { key: "duels_won", label: "Duelos vencidos" },
  { key: "dribbles_attempts", label: "Dribles tentados" },
  { key: "dribbles_success", label: "Dribles certos" },
];

const DEFENSE_ROWS = [
  { key: "tackles_total", label: "Desarmes" },
  { key: "interceptions", label: "Interceptações" },
  { key: "passes_key", label: "Passes-chave" },
  { key: "fouls_committed", label: "Faltas cometidas" },
];

function Section({ title, right, children }) {
  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="flex items-center justify-between mb-3.5">
        <span className="text-xs font-semibold text-muted tracking-wide">{title.toUpperCase()}</span>
        {right}
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function PlayerRatingCard({ label, players }) {
  if (!players || players.length === 0) return null;
  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="text-xs font-semibold text-muted tracking-wide mb-3.5">{label.toUpperCase()}</div>
      <div className="space-y-2.5">
        {players.map((p, i) => (
          <div key={`${p.name}-${i}`} className="flex items-center justify-between gap-2">
            <span className="text-sm text-slate-200 truncate">{p.name}</span>
            <span
              className={`text-xs font-semibold px-2 py-0.5 rounded-md shrink-0 ${
                p.rating >= 7.5
                  ? "bg-accentdim text-accent"
                  : p.rating >= 6.5
                  ? "bg-panel2 text-slate-200"
                  : "bg-red-500/15 text-red-400"
              }`}
            >
              {p.rating.toFixed(1)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function DetailedStatsPanel({ homeName, awayName, snapshot, detailed, loading }) {
  const s = snapshot || {};
  const d = detailed || {};
  const home = d.home || {};
  const away = d.away || {};

  const val = (key) => {
    // Primeiro tenta no snapshot (ex: total_shots_home), depois no
    // agregado detalhado (ex: home.duels_total).
    const snapKey = `${key}_home`;
    if (snapKey in s) return { home: s[`${key}_home`] ?? 0, away: s[`${key}_away`] ?? 0 };
    return { home: home[key] ?? 0, away: away[key] ?? 0 };
  };

  if (!snapshot) {
    return (
      <div className="bg-panel border border-border rounded-xl p-8 text-center">
        <p className="text-slate-200 font-medium mb-1">Ainda sem estatísticas coletadas para esta partida</p>
        <p className="text-sm text-muted">
          A primeira coleta acontece em até 5 minutos após a partida entrar em observação.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between text-sm font-medium px-1">
        <span className="text-blue-400 truncate">{homeName}</span>
        <span className="text-red-400 truncate">{awayName}</span>
      </div>

      <Section title="Finalizações">
        {SNAPSHOT_ROWS.map((r) => {
          const v = val(r.key);
          return <StatRow key={r.key} label={r.label} home={v.home} away={v.away} statKey={r.key} />;
        })}
        {(s.xg_home || s.xg_away) ? (
          <StatRow label={XG_ROW.label} home={s.xg_home ?? 0} away={s.xg_away ?? 0} statKey={XG_ROW.key} />
        ) : null}
      </Section>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <Section title="Posse & Passes">
          <StatRow
            label="Posse de bola (%)"
            home={s.possession_home ?? 0}
            away={s.possession_away ?? 0}
            statKey="possession"
          />
          {PASSES_ROWS.map((r) => {
            const v = val(r.key);
            return <StatRow key={r.key} label={r.label} home={v.home} away={v.away} statKey={r.key} />;
          })}
        </Section>

        <Section title="Disciplina">
          {DISCIPLINE_ROWS.map((r) => {
            const v = val(r.key);
            return <StatRow key={r.key} label={r.label} home={v.home} away={v.away} statKey={r.key} />;
          })}
        </Section>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <Section
          title="Duelos & Dribles"
          right={loading ? <Loader2 size={12} className="animate-spin text-muted" /> : null}
        >
          {d.player_stats_available === false ? (
            <p className="text-xs text-muted">
              A API-Football ainda não tem estatísticas por jogador para esta partida (comum nos primeiros
              minutos). Tentando novamente a cada minuto.
            </p>
          ) : (
            DUEL_ROWS.map((r) => {
              const v = val(r.key);
              return <StatRow key={r.key} label={r.label} home={v.home} away={v.away} statKey={r.key} />;
            })
          )}
        </Section>

        <Section title="Defesa">
          {d.player_stats_available === false ? (
            <p className="text-xs text-muted">Sem dados de jogador disponíveis ainda para esta partida.</p>
          ) : (
            <>
              {DEFENSE_ROWS.map((r) => {
                const v = val(r.key);
                return <StatRow key={r.key} label={r.label} home={v.home} away={v.away} statKey={r.key} />;
              })}
              <StatRow
                label="Defesas do goleiro"
                home={s.goalkeeper_saves_home ?? 0}
                away={s.goalkeeper_saves_away ?? 0}
                statKey="goalkeeper_saves"
              />
            </>
          )}
        </Section>
      </div>

      {(d.top_players_home?.length > 0 || d.top_players_away?.length > 0) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <PlayerRatingCard label={`Destaques - ${homeName}`} players={d.top_players_home} />
          <PlayerRatingCard label={`Destaques - ${awayName}`} players={d.top_players_away} />
        </div>
      )}
    </div>
  );
}
