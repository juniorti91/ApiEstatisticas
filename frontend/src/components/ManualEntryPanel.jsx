import { useState } from "react";
import { ApiClient } from "../api/client";

export default function ManualEntryPanel({ selectedMatch, onTracked, onSnapshotAdded }) {
  const [apiFixtureId, setApiFixtureId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [manualOpen, setManualOpen] = useState(false);
  const [manual, setManual] = useState({
    minute: "", goals_home: 0, goals_away: 0, corners_home: 0, corners_away: 0,
    shots_on_target_home: 0, shots_on_target_away: 0, total_shots_home: 0, total_shots_away: 0,
    possession_home: 50, possession_away: 50, yellow_cards_home: 0, yellow_cards_away: 0,
    fouls_home: 0, fouls_away: 0,
  });

  async function handleTrack(e) {
    e.preventDefault();
    if (!apiFixtureId) return;
    setLoading(true);
    setError("");
    try {
      const fixture = await ApiClient.trackMatch(apiFixtureId.trim());
      onTracked?.(fixture);
      setApiFixtureId("");
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          "Não foi possível localizar essa partida (verifique o ID da API-Football ou a conectividade)."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleManualSubmit(e) {
    e.preventDefault();
    if (!selectedMatch || !manual.minute) return;
    setLoading(true);
    setError("");
    try {
      const payload = { ...manual, minute: Number(manual.minute) };
      Object.keys(payload).forEach((k) => {
        if (k !== "minute") payload[k] = Number(payload[k]);
      });
      await ApiClient.addManualSnapshot(selectedMatch.id, payload);
      onSnapshotAdded?.();
    } catch (err) {
      setError(err?.response?.data?.detail || "Falha ao registrar snapshot manual.");
    } finally {
      setLoading(false);
    }
  }

  function updateField(key, value) {
    setManual((m) => ({ ...m, [key]: value }));
  }

  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5 space-y-4">
      <div>
        <div className="text-sm font-medium text-slate-200 mb-2">MONITORAR NOVA PARTIDA</div>
        <p className="text-xs text-muted mb-3">
          Informe o ID da partida na API-Football (fixture id) para passar a monitorá-la a cada 5 minutos.
        </p>
        <form onSubmit={handleTrack} className="flex gap-2">
          <input
            value={apiFixtureId}
            onChange={(e) => setApiFixtureId(e.target.value)}
            placeholder="Ex: 1035037"
            className="flex-1 bg-panel2 border border-border rounded-md text-sm px-3 py-2 text-slate-200"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-accent text-black text-sm font-medium px-4 py-2 rounded-lg hover:brightness-110 disabled:opacity-60"
          >
            Monitorar
          </button>
        </form>
      </div>

      {selectedMatch && (
        <div className="border-t border-border pt-4">
          <button
            className="text-xs text-accent font-medium"
            onClick={() => setManualOpen((v) => !v)}
            type="button"
          >
            {manualOpen ? "Ocultar inserção manual" : "Inserir estatísticas manualmente (fallback sem API)"}
          </button>
          {manualOpen && (
            <form onSubmit={handleManualSubmit} className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-3 text-xs">
              {[
                ["minute", "Minuto"],
                ["goals_home", "Gols Casa"],
                ["goals_away", "Gols Fora"],
                ["corners_home", "Escanteios Casa"],
                ["corners_away", "Escanteios Fora"],
                ["shots_on_target_home", "Chutes Alvo Casa"],
                ["shots_on_target_away", "Chutes Alvo Fora"],
                ["total_shots_home", "Finalizações Casa"],
                ["total_shots_away", "Finalizações Fora"],
                ["possession_home", "Posse Casa %"],
                ["possession_away", "Posse Fora %"],
                ["yellow_cards_home", "Amarelos Casa"],
                ["yellow_cards_away", "Amarelos Fora"],
                ["fouls_home", "Faltas Casa"],
                ["fouls_away", "Faltas Fora"],
              ].map(([key, label]) => (
                <label key={key} className="flex flex-col gap-1">
                  <span className="text-muted">{label}</span>
                  <input
                    type="number"
                    value={manual[key]}
                    onChange={(e) => updateField(key, e.target.value)}
                    className="bg-panel2 border border-border rounded px-2 py-1 text-slate-200"
                  />
                </label>
              ))}
              <button
                type="submit"
                disabled={loading}
                className="col-span-2 sm:col-span-3 mt-1 bg-accentdim text-accent text-sm font-medium py-2 rounded-lg hover:brightness-110 disabled:opacity-60"
              >
                Registrar snapshot manual
              </button>
            </form>
          )}
        </div>
      )}

      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}
