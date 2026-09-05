import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "/api";
// Quando VITE_API_BASE_URL nao e definido, o proxy do Vite (vite.config.js)
// encaminha /api para o backend em http://127.0.0.1:8000 - funciona direto
// em desenvolvimento sem precisar configurar CORS/URL manualmente.
const api = axios.create({ baseURL: baseURL === "/api" ? "" : baseURL });

export const ApiClient = {
  listLiveMatches: () => api.get("/api/matches/live").then((r) => r.data),
  getMatch: (id) => api.get(`/api/matches/${id}`).then((r) => r.data),
  getSnapshots: (id) => api.get(`/api/matches/${id}/snapshots`).then((r) => r.data),
  getComparison: (id) => api.get(`/api/matches/${id}/comparison`).then((r) => r.data),
  getDetailedStats: (id) => api.get(`/api/matches/${id}/detailed-stats`).then((r) => r.data),
  trackMatch: (apiFixtureId) => api.post(`/api/matches/track/${apiFixtureId}`).then((r) => r.data),
  addManualSnapshot: (id, payload) =>
    api.post(`/api/matches/${id}/snapshots/manual`, payload).then((r) => r.data),

  listFixtureRecommendations: (id) =>
    api.get(`/api/recommendations/fixture/${id}`).then((r) => r.data),
  listPendingRecommendations: () => api.get("/api/recommendations/pending").then((r) => r.data),
  getOddsHistory: (recommendationId) =>
    api.get(`/api/recommendations/${recommendationId}/odds-history`).then((r) => r.data),

  getHistory: (limit = 50) =>
    api.get(`/api/history/recommendations?limit=${limit}`).then((r) => r.data),

  getPerformance: (days = 30) =>
    api.get(`/api/dashboard/performance?days=${days}`).then((r) => r.data),
  collectNow: () => api.post("/api/dashboard/collect-now").then((r) => r.data),
};

export default api;
