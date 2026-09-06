import { CircleDot, Repeat, ShieldAlert } from "lucide-react";

// Linha do tempo de eventos (gols, cartões, substituições, VAR) plotados
// pelo minuto da partida, separada em dois tempos - como a API-Football
// não fornece um índice contínuo de "pressão"/momentum por minuto (isso é
// dado de outro tipo de provedor, igual ao xG avançado já mapeado antes
// neste projeto), aqui plotamos os eventos REAIS que já coletamos via
// /fixtures/events em vez de inventar uma métrica de pressão que não temos.
//
// V2 (depois do feedback visual do usuário num jogo real com muitos
// eventos - Portland Timbers x Minnesota United): 3 problemas corrigidos -
// 1) todo gol saía verde (bg-accent) igual pros dois times, só a posição
// acima/abaixo do eixo indicava o lado, o que ficava confuso perto da
// legenda azul/vermelho lá em cima; agora o círculo do gol/substituição
// usa a MESMA cor azul/vermelho da legenda e do resto do app (StatBar,
// LiveMatchCard). 2) substituições ficavam cinza-escuro sobre fundo
// escuro, quase invisíveis. 3) minutos próximos (ex: 71'/72'/72' do
// mesmo lado) desenhavam os ícones um em cima do outro - agora usa um
// algoritmo simples de "faixas" (lanes) que empilha em camadas extras
// quando dois eventos do mesmo lado ficam muito próximos no eixo.

const MIN_GAP_PCT = 7; // separação mínima (%) antes de empilhar numa faixa extra

// Agrupa eventos (já ordenados por posição) em "faixas" (lanes) sem
// sobreposição - cada evento entra na PRIMEIRA faixa onde cabe (distância
// do último item dessa faixa >= MIN_GAP_PCT); lane[0] fica sempre mais
// perto do eixo central. Retorna um array de faixas (cada uma é uma
// lista de items). Exportada só pra poder testar isoladamente (ver
// verificação em Node antes de entregar).
export function assignLanes(itemsWithPct) {
  const lanes = [];
  for (const item of itemsWithPct) {
    let placedLane = lanes.find((lane) => item.pct - lane[lane.length - 1].pct >= MIN_GAP_PCT);
    if (!placedLane) {
      placedLane = [];
      lanes.push(placedLane);
    }
    placedLane.push(item);
  }
  return lanes;
}

function sideColors(side) {
  return side === "home"
    ? { solid: "bg-blue-500", onSolid: "text-blue-50", soft: "bg-blue-500/20 border-blue-400/60 text-blue-300" }
    : { solid: "bg-red-500", onSolid: "text-red-50", soft: "bg-red-500/20 border-red-400/60 text-red-300" };
}

function EventIcon({ event }) {
  const t = (event.type || "").toLowerCase();
  const d = (event.detail || "").toLowerCase();
  const colors = sideColors(event.side);

  if (t === "goal" && !d.includes("missed")) {
    return (
      <div className={`w-5 h-5 rounded-full ${colors.solid} flex items-center justify-center shadow`}>
        <CircleDot size={12} className={colors.onSolid} />
      </div>
    );
  }
  if (t === "card") {
    const isRed = d.includes("red");
    return <div className={`w-3.5 h-5 rounded-sm ${isRed ? "bg-red-500" : "bg-yellow-400"}`} />;
  }
  if (t === "subst") {
    return (
      <div className={`w-5 h-5 rounded-full border flex items-center justify-center ${colors.soft}`}>
        <Repeat size={11} />
      </div>
    );
  }
  // "Var" ou qualquer outro tipo nao mapeado - mostra so um marcador neutro
  // em vez de esconder o evento.
  return (
    <div className={`w-5 h-5 rounded-full border flex items-center justify-center ${colors.soft}`}>
      <ShieldAlert size={11} />
    </div>
  );
}

function eventLabel(event) {
  const who = event.player_name ? `${event.player_name}` : "Jogador não informado";
  const minuteLabel = `${event.minute}${event.extra_minute ? `+${event.extra_minute}` : ""}'`;
  return `${minuteLabel} · ${event.detail || event.type} · ${who}`;
}

function LaneRow({ lane, label }) {
  return (
    <div className="relative h-6">
      {lane.map(({ event, pct }, i) => (
        <div
          key={i}
          title={`${label}: ${eventLabel(event)}`}
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2"
          style={{ left: `${pct}%` }}
        >
          <EventIcon event={event} />
        </div>
      ))}
    </div>
  );
}

function AxisTicks({ baseMinute, spanMinutes }) {
  // Marcas a cada 15min a partir do inicio desse tempo de jogo - sempre 4
  // marcas (0/15/30/45 relativos), reposicionadas se o acrescimo esticou
  // a escala (spanMinutes > 45).
  const ticks = [0, 15, 30, 45];
  return (
    <div className="relative h-4">
      <div className="absolute left-0 right-0 top-0 h-px bg-border" />
      {ticks.map((offset) => {
        const pct = (offset / spanMinutes) * 100;
        if (pct > 100) return null;
        return (
          <div
            key={offset}
            className="absolute top-0 -translate-x-1/2 flex flex-col items-center"
            style={{ left: `${pct}%` }}
          >
            <div className="w-px h-1.5 bg-border" />
            <span className="text-[9px] text-muted mt-0.5">{baseMinute + offset}'</span>
          </div>
        );
      })}
    </div>
  );
}

function HalfTrack({ events, baseMinute, spanMinutes, homeName, awayName }) {
  function positionPct(event) {
    const minute = event.minute + (event.extra_minute || 0);
    const pct = ((minute - baseMinute) / spanMinutes) * 100;
    return Math.min(98, Math.max(2, pct));
  }

  const home = events
    .filter((e) => e.side === "home")
    .map((event) => ({ event, pct: positionPct(event) }))
    .sort((a, b) => a.pct - b.pct);
  const away = events
    .filter((e) => e.side === "away")
    .map((event) => ({ event, pct: positionPct(event) }))
    .sort((a, b) => a.pct - b.pct);

  const homeLanes = assignLanes(home);
  const awayLanes = assignLanes(away);

  return (
    <div>
      {/* Faixas do mandante - a mais distante do eixo primeiro, pra a
          faixa 0 (mais eventos) ficar sempre coladinha na linha central. */}
      {[...homeLanes].reverse().map((lane, i) => (
        <LaneRow key={`h-${i}`} lane={lane} label={homeName} />
      ))}
      <AxisTicks baseMinute={baseMinute} spanMinutes={spanMinutes} />
      {awayLanes.map((lane, i) => (
        <LaneRow key={`a-${i}`} lane={lane} label={awayName} />
      ))}
    </div>
  );
}

export default function MomentumTimeline({ events, homeName, awayName }) {
  const safeEvents = events || [];
  const half1 = safeEvents.filter((e) => e.minute <= 45);
  const half2 = safeEvents.filter((e) => e.minute > 45);

  // A escala de cada tempo nunca fica menor que a duracao regulamentar
  // (45min), mas se acumulou acrescimo (ex: gol aos 45+3'), a escala se
  // estica pra caber sem cortar o icone.
  const span1 = Math.max(45, ...half1.map((e) => e.minute + (e.extra_minute || 0)));
  const span2 = Math.max(90, ...half2.map((e) => e.minute + (e.extra_minute || 0))) - 45;

  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="text-sm font-medium text-slate-200">LINHA DO TEMPO DE EVENTOS</div>
        <div className="flex items-center gap-3 text-[11px] text-muted">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500" /> {homeName}
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" /> {awayName}
          </span>
        </div>
      </div>

      {safeEvents.length === 0 ? (
        <p className="text-sm text-muted py-4 text-center">Nenhum evento registrado até agora.</p>
      ) : (
        <div className="space-y-5">
          <div>
            <div className="text-[10px] text-muted mb-1">1º TEMPO</div>
            <HalfTrack events={half1} baseMinute={0} spanMinutes={span1} homeName={homeName} awayName={awayName} />
          </div>
          <div>
            <div className="text-[10px] text-muted mb-1">2º TEMPO</div>
            <HalfTrack events={half2} baseMinute={45} spanMinutes={span2} homeName={homeName} awayName={awayName} />
          </div>

          {/* Lista textual - mesma informação dos ícones, mas acessível em
              telas pequenas e sem depender de passar o mouse por cima. */}
          <ul className="space-y-1 pt-2 border-t border-border text-xs">
            {safeEvents.map((e, i) => (
              <li key={i} className="flex items-center gap-2">
                <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${e.side === "home" ? "bg-blue-500" : "bg-red-500"}`} />
                <span className="text-muted w-10 shrink-0">
                  {e.minute}
                  {e.extra_minute ? `+${e.extra_minute}` : ""}'
                </span>
                <span className="text-slate-300 truncate">
                  {e.detail || e.type}
                  {e.player_name ? ` — ${e.player_name}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
