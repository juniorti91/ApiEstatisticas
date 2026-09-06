import { useState } from "react";
import { CircleDot, Repeat, ShieldAlert } from "lucide-react";

// Aba "Relato": narracao textual dos lances da partida, mais recente
// primeiro (como um "live blog"). IMPORTANTE - limite conhecido: a
// API-Football (nosso unico provedor de dados) so fornece EVENTOS
// discretos via /fixtures/events (gol, cartao, substituicao, VAR), sem
// nenhum campo de narracao livre (tipo "chute passou perto do gol") -
// esse tipo de comentario minuto-a-minuto de lances comuns e uma feature
// de provedores dedicados de "live commentary" (ex: SofaScore/Livescore),
// que fica fora do plano contratado. Por isso este Relato usa os MESMOS
// eventos ja coletados pela aba Eventos (zero chamadas novas de API),
// convertidos em frases legiveis - cobre os lances realmente importantes
// (gol, cartao, substituicao, VAR), so nao narra lances sem finalizacao
// certeira/cartao (chutes perdidos, escanteios sem finalizacao etc).

function isImportant(event) {
  const t = (event.type || "").toLowerCase();
  const d = (event.detail || "").toLowerCase();
  if (t === "goal") return true;
  if (t === "var") return true;
  if (t === "card" && d.includes("red")) return true;
  return false;
}

function ReportIcon({ event }) {
  const t = (event.type || "").toLowerCase();
  const d = (event.detail || "").toLowerCase();
  const sideColor = event.side === "home" ? "text-blue-400 bg-blue-500/15" : "text-red-400 bg-red-500/15";

  if (t === "goal" && !d.includes("missed")) {
    return (
      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${sideColor}`}>
        <CircleDot size={16} />
      </div>
    );
  }
  if (t === "card") {
    const isRed = d.includes("red");
    return (
      <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-panel2">
        <div className={`w-3.5 h-5 rounded-sm ${isRed ? "bg-red-500" : "bg-yellow-400"}`} />
      </div>
    );
  }
  if (t === "subst") {
    return (
      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${sideColor}`}>
        <Repeat size={16} />
      </div>
    );
  }
  return (
    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${sideColor}`}>
      <ShieldAlert size={16} />
    </div>
  );
}

// Gera uma frase legivel a partir do evento cru (type/detail/player/assist)
// - nao e narracao original da API, e um TEXTO GERADO por nos em cima do
// dado estruturado que ela fornece (ver aviso no topo do arquivo).
function reportText(event, homeName, awayName) {
  const team = event.side === "home" ? homeName : awayName;
  const t = (event.type || "").toLowerCase();
  const d = (event.detail || "").toLowerCase();
  const player = event.player_name || "jogador não informado";

  if (t === "goal") {
    if (d.includes("missed")) return `Pênalti perdido por ${player} (${team}).`;
    if (d.includes("penalty")) {
      return `GOL DE PÊNALTI! ${player} marca para ${team}.`;
    }
    if (d.includes("own")) return `Gol contra: ${player} (${team}) marca contra o próprio time.`;
    const assist = event.assist_name ? ` Assistência de ${event.assist_name}.` : "";
    return `GOL! ${player} marca para ${team}.${assist}`;
  }
  if (t === "card") {
    const isRed = d.includes("red");
    return `Cartão ${isRed ? "vermelho" : "amarelo"} para ${player} (${team}).`;
  }
  if (t === "subst") {
    const out = event.assist_name ? `, sai ${event.assist_name}` : "";
    return `Substituição em ${team}: entra ${player}${out}.`;
  }
  if (t === "var") {
    return `Revisão do VAR (${team}): ${event.detail || "decisão em análise"}.`;
  }
  return `${event.detail || event.type || "Lance"} - ${player} (${team}).`;
}

export default function MatchReport({ events, homeName, awayName }) {
  const [onlyImportant, setOnlyImportant] = useState(false);
  const safeEvents = events || [];
  const filtered = onlyImportant ? safeEvents.filter(isImportant) : safeEvents;
  // Mais recente primeiro - como um live blog, o lance mais novo aparece no topo.
  const ordered = [...filtered].sort((a, b) => {
    const minuteA = a.minute + (a.extra_minute || 0);
    const minuteB = b.minute + (b.extra_minute || 0);
    return minuteB - minuteA;
  });

  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="text-sm font-medium text-slate-200">RELATO DA PARTIDA</div>
        <div className="flex items-center gap-1 bg-panel2 rounded-lg p-0.5 text-xs">
          <button
            onClick={() => setOnlyImportant(false)}
            className={`px-2.5 py-1 rounded-md transition-colors ${!onlyImportant ? "bg-accentdim text-accent font-medium" : "text-muted"}`}
          >
            Todos os Lances
          </button>
          <button
            onClick={() => setOnlyImportant(true)}
            className={`px-2.5 py-1 rounded-md transition-colors ${onlyImportant ? "bg-accentdim text-accent font-medium" : "text-muted"}`}
          >
            Só Importantes
          </button>
        </div>
      </div>

      {/* Aviso de limitação de dados - deixa claro que não é uma narração
          completa tipo um site de resultados ao vivo dedicado. */}
      <p className="text-[11px] text-muted mb-3 pb-3 border-b border-border">
        Gerado a partir dos eventos oficiais da partida (gols, cartões, substituições, VAR). Lances sem
        finalização ou cartão (chutes, escanteios, faltas comuns) não têm narração disponível no provedor de dados.
      </p>

      {ordered.length === 0 ? (
        <p className="text-sm text-muted py-4 text-center">
          {onlyImportant ? "Nenhum lance importante registrado até agora." : "Nenhum lance registrado até agora."}
        </p>
      ) : (
        <ul className="space-y-3">
          {ordered.map((e, i) => (
            <li key={i} className="flex items-start gap-3">
              <ReportIcon event={e} />
              <div className="min-w-0 flex-1 pt-1">
                <div className="flex items-baseline gap-2">
                  <span className="text-xs font-semibold text-slate-400 shrink-0">
                    {e.minute}
                    {e.extra_minute ? `+${e.extra_minute}` : ""}'
                  </span>
                  <span className="text-sm text-slate-200">{reportText(e, homeName, awayName)}</span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
