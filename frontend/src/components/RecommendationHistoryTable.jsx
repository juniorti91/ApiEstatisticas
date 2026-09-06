import { useState } from "react";
import { Check, X, Minus } from "lucide-react";

const STATUS_LABEL = { win: "Acertou", loss: "Errou", pending: "Pendente", void: "Anulada" };
const PAGE_SIZE = 12;

// Monta a lista de paginas a exibir tipo "1 2 3 ... 8": sempre mostra a
// primeira, a ultima e uma janela em volta da pagina atual, resumindo o
// resto num "..." pra nao lotar a tela quando tiver muita pagina no
// historico.
function buildPageList(current, total) {
  const pages = [];
  const WINDOW = 1;
  let lastAdded = 0;
  for (let p = 1; p <= total; p++) {
    const isEdge = p === 1 || p === total;
    const isNearCurrent = Math.abs(p - current) <= WINDOW;
    if (isEdge || isNearCurrent) {
      if (lastAdded && p - lastAdded > 1) pages.push("...");
      pages.push(p);
      lastAdded = p;
    }
  }
  return pages;
}

function StatusIcon({ status }) {
  if (status === "win") return <Check size={16} className="text-accent" />;
  if (status === "loss") return <X size={16} className="text-red-400" />;
  return <Minus size={16} className="text-muted" />;
}

function formatDay(dateStr) {
  const date = new Date(dateStr);
  const today = new Date();
  const isToday = date.toDateString() === today.toDateString();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  const isYesterday = date.toDateString() === yesterday.toDateString();
  const time = date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  if (isToday) return { label: "Hoje", time };
  if (isYesterday) return { label: "Ontem", time };
  return { label: date.toLocaleDateString("pt-BR"), time };
}

export default function RecommendationHistoryTable({ rows, onViewAll }) {
  const [page, setPage] = useState(1);
  // rows chega inteira (ate 50 linhas, ver Dashboard.jsx) e recarrega a
  // cada poll de 12s - se ela encolher (ex: filtro mudou) e a pagina atual
  // deixar de existir, volta pra ultima pagina valida em vez de mostrar
  // uma pagina vazia.
  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const safePage = Math.min(Math.max(page, 1), totalPages);
  const start = (safePage - 1) * PAGE_SIZE;
  const pageRows = rows.slice(start, start + PAGE_SIZE);
  const pageList = buildPageList(safePage, totalPages);

  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-slate-200">HISTÓRICO DE RECOMENDAÇÕES</span>
        {/* So aparece quando quem usa este componente passa onViewAll (ver
            Dashboard.jsx) - leva pra pagina "Recomendações" dedicada, com o
            historico completo (ate 200 linhas, contra as 50 mostradas aqui
            no resumo do Dashboard). Na propria pagina de Recomendações essa
            prop nao e passada, entao o botao some (nao faz sentido "ver
            todas" de dentro da tela que ja mostra todas). */}
        {onViewAll && (
          <button onClick={onViewAll} className="text-xs text-accent font-medium hover:underline">
            VER TODAS
          </button>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm min-w-[480px]">
          <thead>
            <tr className="text-muted text-xs">
              <th className="text-left font-normal pb-2">PARTIDA</th>
              <th className="text-left font-normal pb-2">RECOMENDAÇÃO</th>
              <th className="text-right font-normal pb-2">ODD</th>
              <th className="text-right font-normal pb-2">RESULTADO</th>
              <th className="text-right font-normal pb-2">ACERTO</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {pageRows.map((row) => {
              const { label, time } = formatDay(row.played_on);
              return (
                <tr key={row.id}>
                  <td className="py-2.5 text-slate-300">
                    <div className="text-xs text-muted">
                      {label} {time}
                    </div>
                    {row.fixture_label}
                  </td>
                  <td className="py-2.5 text-slate-300">{row.selection}</td>
                  <td className="py-2.5 text-right text-slate-200">{row.odd.toFixed(2)}</td>
                  <td className="py-2.5 text-right text-slate-300">{row.result_score ?? "-"}</td>
                  <td className="py-2.5 text-right">
                    <span className="inline-flex justify-end w-full" title={STATUS_LABEL[row.status]}>
                      <StatusIcon status={row.status} />
                    </span>
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="py-6 text-center text-muted text-sm">
                  Nenhuma recomendação registrada ainda.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-1.5 flex-wrap mt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={safePage === 1}
            className="text-xs font-medium px-3 py-1.5 rounded-md bg-panel2 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-110"
          >
            « Anterior
          </button>
          {pageList.map((p, idx) =>
            p === "..." ? (
              <span key={`ellipsis-${idx}`} className="text-xs text-muted px-1">
                ...
              </span>
            ) : (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={`text-xs font-medium w-7 h-7 rounded-md shrink-0 ${
                  p === safePage ? "bg-accent text-panel" : "bg-panel2 text-slate-300 hover:brightness-110"
                }`}
              >
                {p}
              </button>
            )
          )}
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={safePage === totalPages}
            className="text-xs font-medium px-3 py-1.5 rounded-md bg-panel2 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-110"
          >
            Próxima »
          </button>
        </div>
      )}
    </div>
  );
}
