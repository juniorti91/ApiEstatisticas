"""
Script de USO UNICO - verifica se a resposta da API-Football para uma
partida especifica (endpoint /fixtures) traz algum dado de "onde assistir"
(canal de TV, streaming etc).

Por que isso existe: a documentacao publica da API-Football (varios planos
testados ao longo deste projeto) NAO lista nenhum campo de emissora/canal
de TV em nenhum endpoint - isso normalmente vem de um provedor
especializado em guia de programacao, nao de uma API de estatisticas
esportivas. Mas em vez de simplesmente assumir isso, este script busca a
resposta CRUA de verdade e procura por qualquer campo com nome parecido
("broadcast", "tv", "channel", "stream", "watch") em QUALQUER nivel do
JSON, pra confirmar com dados reais antes de decidir se da pra construir
essa parte da tela ou nao.

NAO faz parte do app (nao e importado por nada).

COMO USAR:
    cd backend
    python inspect_broadcast.py                    # lista as partidas ao vivo agora (qualquer liga do mundo)
    python inspect_broadcast.py "nome de um time"   # investiga a partida ao vivo desse time

Precisa que backend/.env ja tenha API_FOOTBALL_KEY preenchido. Rodar sem
argumento nenhum so lista os jogos ao vivo agora (fixture id + nomes dos
times) - use um desses nomes na segunda chamada.
"""
from __future__ import annotations

import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY", "")
BASE_URL = os.getenv("API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io")

if not API_KEY or API_KEY == "coloque_sua_chave_aqui":
    raise SystemExit("API_FOOTBALL_KEY nao esta configurada no backend/.env - preencha antes de rodar este script.")

SUSPECT_KEYWORDS = ["broadcast", "tv", "channel", "stream", "watch", "media"]


def _list_live_fixtures() -> list[tuple[int, str]]:
    resp = httpx.get(
        f"{BASE_URL}/fixtures",
        params={"live": "all"},
        headers={"x-apisports-key": API_KEY},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    out: list[tuple[int, str]] = []
    for item in data.get("response", []):
        teams = item.get("teams", {})
        home = (teams.get("home") or {}).get("name", "")
        away = (teams.get("away") or {}).get("name", "")
        fixture_id = item.get("fixture", {}).get("id")
        if fixture_id is not None:
            out.append((fixture_id, f"{home} x {away}"))
    return out


def _find_live_fixture(team_filter: str, live: list[tuple[int, str]]) -> tuple[int, str] | None:
    for fixture_id, label in live:
        if team_filter.lower() in label.lower():
            return fixture_id, label
    return None


def _scan_for_suspects(node, path: str = "$", hits: list[str] | None = None) -> list[str]:
    if hits is None:
        hits = []
    if isinstance(node, dict):
        for key, value in node.items():
            key_lower = str(key).lower()
            if any(word in key_lower for word in SUSPECT_KEYWORDS):
                hits.append(f"{path}.{key} = {json.dumps(value, ensure_ascii=False)}")
            _scan_for_suspects(value, f"{path}.{key}", hits)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            _scan_for_suspects(item, f"{path}[{i}]", hits)
    return hits


def main() -> None:
    team_filter = " ".join(sys.argv[1:]).strip()

    live = _list_live_fixtures()
    if not live:
        print(
            "Nenhuma partida ao vivo em lugar nenhum agora (nao so nas suas ligas monitoradas - "
            "isso aqui olha TODAS as partidas ao vivo do mundo). Tente de novo em outro horario."
        )
        return

    if not team_filter:
        print("Uso: python inspect_broadcast.py \"nome de um time\" - partidas ao vivo agora:")
        for fixture_id, label in live:
            print(f" - {label} (fixture {fixture_id})")
        return

    found = _find_live_fixture(team_filter, live)
    if found is None:
        print(f"Nenhuma partida ao vivo agora com '{team_filter}'. Partidas ao vivo agora:")
        for fixture_id, label in live:
            print(f" - {label} (fixture {fixture_id})")
        return

    fixture_id, label = found
    print(f"Partida encontrada: {label} (fixture {fixture_id})")
    print("=" * 70)

    resp = httpx.get(
        f"{BASE_URL}/fixtures",
        params={"id": fixture_id},
        headers={"x-apisports-key": API_KEY},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    results = data.get("response", [])
    if not results:
        print("A API nao devolveu detalhes para esse fixture id (inesperado).")
        return

    item = results[0]

    hits = _scan_for_suspects(item)
    print(f"Campos com nome parecido com 'broadcast/tv/channel/stream/watch': {len(hits)}")
    for hit in hits:
        print(f"  - {hit}")
    if not hits:
        print("  (nenhum encontrado)")
    print("=" * 70)

    print("Resposta CRUA completa do endpoint /fixtures para essa partida:")
    print(json.dumps(item, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
