import { Check, X, Minus } from "lucide-react";

const STATUS_LABEL = { win: "Acertou", loss: "Errou", pending: "Pendente", void: "Anulada" };

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

export default function RecommendationHistoryTable({ rows }) {
  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-slate-200">HISTÓRICO DE RECOMENDAÇÕES</span>
        <button className="text-xs text-accent font-medium">VER TODAS</button>
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
            {rows.map((row) => {
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
    </div>
  );
}
