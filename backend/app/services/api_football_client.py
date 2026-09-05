"""
Cliente assincrono para a API-Football (https://www.api-football.com).

Centraliza toda a comunicacao HTTP em um unico lugar: autenticacao,
timeouts, tratamento de erro e parsing basico da resposta. Os servicos
(collector, team_form_service, recommendation_engine) so falam com esta
classe - nunca chamam httpx diretamente - o que deixa o resto do sistema
organizado e facil de testar com um cliente falso.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("betanalyzer.api_football")


class ApiFootballError(RuntimeError):
    pass


class ApiFootballClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or settings.api_football_key
        self.base_url = (base_url or settings.api_football_base_url).rstrip("/")
        self._client: httpx.AsyncClient | None = None

    def _headers(self) -> dict[str, str]:
        return {"x-apisports-key": self.api_key}

    async def __aenter__(self) -> "ApiFootballClient":
        self._client = httpx.AsyncClient(
            base_url=self.base_url, headers=self._headers(), timeout=20.0
        )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> list[dict]:
        if self._client is None:
            # permite uso sem context manager (cria/fecha uma conexao pontual)
            async with self as client:
                return await client._get(path, params)

        if not self.api_key:
            raise ApiFootballError(
                "API_FOOTBALL_KEY nao configurada. Defina no backend/.env."
            )

        try:
            resp = await self._client.get(path, params=params or {})
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("API-Football HTTP %s em %s: %s", exc.response.status_code, path, exc.response.text[:300])
            raise ApiFootballError(f"Erro HTTP {exc.response.status_code} ao chamar {path}") from exc
        except httpx.HTTPError as exc:
            logger.error("Falha de rede ao chamar API-Football %s: %s", path, exc)
            raise ApiFootballError(f"Falha de rede ao chamar {path}") from exc

        payload = resp.json()
        errors = payload.get("errors")
        if errors:
            logger.warning("API-Football retornou erros em %s: %s", path, errors)
        return payload.get("response", [])

    # ---- Endpoints usados pelo sistema -------------------------------

    async def live_fixtures(self, league_ids: list[int] | None = None) -> list[dict]:
        """Partidas ao vivo agora. Filtra por ligas monitoradas quando informado."""
        params: dict[str, Any] = {"live": "all"}
        data = await self._get("/fixtures", params)
        if league_ids:
            data = [f for f in data if f.get("league", {}).get("id") in league_ids]
        return data

    async def fixture_by_id(self, fixture_id: int) -> dict | None:
        data = await self._get("/fixtures", {"id": fixture_id})
        return data[0] if data else None

    async def fixture_statistics(self, fixture_id: int) -> list[dict]:
        """Estatisticas (escanteios, chutes, posse etc) por time, para uma partida."""
        return await self._get("/fixtures/statistics", {"fixture": fixture_id})

    async def fixture_events(self, fixture_id: int) -> list[dict]:
        return await self._get("/fixtures/events", {"fixture": fixture_id})

    async def team_last_fixtures(self, team_id: int, last: int = 5) -> list[dict]:
        """Ultimas N partidas finalizadas de um time (para calcular a forma)."""
        return await self._get(
            "/fixtures", {"team": team_id, "last": last, "status": "FT"}
        )

    async def odds_for_fixture(self, fixture_id: int) -> list[dict]:
        return await self._get("/odds", {"fixture": fixture_id})


api_football_client = ApiFootballClient()
