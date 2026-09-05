import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";

export default function OddsMovementChart({ history, marketLabel }) {
  const hasData = history && history.length > 0;

  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-slate-200">MOVIMENTAÇÃO DA RECOMENDAÇÃO</span>
        {marketLabel && <span className="text-xs text-muted">{marketLabel}</span>}
      </div>
      {hasData ? (
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={history} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#232733" />
            <XAxis dataKey="minute" tickFormatter={(m) => `${m}'`} stroke="#8a90a2" fontSize={12} />
            <YAxis yAxisId="odd" stroke="#22c55e" fontSize={12} domain={["auto", "auto"]} />
            <YAxis
              yAxisId="prob"
              orientation="right"
              stroke="#8a90a2"
              fontSize={12}
              tickFormatter={(v) => `${Math.round(v * 100)}%`}
            />
            <Tooltip
              contentStyle={{ background: "#171a24", border: "1px solid #232733", borderRadius: 8, fontSize: 12 }}
              labelFormatter={(m) => `Minuto ${m}'`}
              formatter={(value, name) =>
                name === "Probabilidade estimada" ? [`${(value * 100).toFixed(0)}%`, name] : [value, name]
              }
            />
            <Line yAxisId="odd" type="monotone" dataKey="odd" name="Odd" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
            <Line
              yAxisId="prob"
              type="monotone"
              dataKey="estimated_probability"
              name="Probabilidade estimada"
              stroke="#8a90a2"
              strokeWidth={1.5}
              dot={{ r: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <div className="h-64 flex items-center justify-center text-sm text-muted">
          Sem histórico suficiente ainda - volte após o próximo ciclo de coleta (5 min).
        </div>
      )}
    </div>
  );
}
