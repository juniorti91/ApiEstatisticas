"""
Script de USO UNICO - mostra a resposta CRUA do endpoint /odds/live da
API-Football (odds AO VIVO de verdade, que mudam durante a partida - bem
diferente do /odds, que e a cotacao fixa de pre-jogo e e o que o app usa
hoje). NAO faz parte do app (nao e importado por nada).

Por que isso existe: eu (Claude) nao tenho acesso a documentacao completa
da API-Football agora (as paginas sao renderizadas em JavaScript) e ja
levei um bug nesta sessao por supor o formato de uma resposta de API sem
confirmar com dados reais. Em vez de arriscar de novo, este script chama
o endpoint de verdade com sua chave e mostra exatamente como a resposta
vem - ai eu conecto o parsing certo no app a partir disso.

COMO USAR:
    cd backend
    python inspect_live_odds.py
    python inspect_live_odds.py "nome do time"   # filtra so a(s) partida(s) com esse time

Precisa que backend/.env ja tenha API_FOOTBALL_KEY preenchido. Funciona
melhor com pelo menos uma partida ao vivo agora nas suas 15 ligas
monitoradas (rode com o Dashboard aberto mostrando algum jogo ao vivo).

Com um nome de time como argumento, mostra TODOS os mercados daquela
partida especifica (sem cortar em 2) - use isso pra investigar uma odd
estranha de uma partida em andamento agora mesmo, antes que ela acabe.
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


def _fixture_names() -> dict[int, str]:
    """/odds/live so devolve o fixture id, sem nome de time - busca em
    /fixtures?live=all (partidas ao vivo agora, com nome dos times) pra
    poder filtrar por nome de time. Custa 1 chamada extra de API."""
    try:
        resp = httpx.get(
            f"{BASE_URL}/fixtures",
            params={"live": "all"},
            headers={"x-apisports-key": API_KEY},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        print(f"(aviso: nao consegui buscar nomes de time via /fixtures?live=all: {exc})")
        return {}

    names: dict[int, str] = {}
    for item in data.get("response", []):
        fixture_id = item.get("fixture", {}).get("id")
        teams = item.get("teams", {})
        home = (teams.get("home") or {}).get("name", "?")
        away = (teams.get("away") or {}).get("name", "?")
        if fixture_id is not None:
            names[fixture_id] = f"{home} x {away}"
    return names


def main() -> None:
    resp = httpx.get(
        f"{BASE_URL}/odds/live",
        headers={"x-apisports-key": API_KEY},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()

    errors = data.get("errors")
    if errors:
        print(f"!! API retornou erro: {errors}")

    results = data.get("response", [])
    print(f"Total de partidas com odds ao vivo agora: {len(results)}")
    print(f"Chamadas de API restantes hoje: {data.get('rest') if isinstance(data.get('rest'), int) else resp.headers.get('x-ratelimit-requests-remaining', '?')}")
    print("=" * 70)

    if not results:
        print(
            "Nenhuma partida com odds ao vivo neste momento (comum fora de "
            "horario de jogo, ou se o plano/mercado nao tiver odds pra "
            "nenhuma partida rolando agora). Tente de novo com algum jogo "
            "ao vivo das suas 15 ligas monitoradas."
        )
        return

    team_filter = " ".join(sys.argv[1:]).strip().lower()

    if team_filter:
        names_by_id = _fixture_names()
        matches = [
            item for item in results
            if team_filter in names_by_id.get(item.get("fixture", {}).get("id"), "").lower()
        ]
        if not matches:
            print(
                f"Nenhuma partida com odds ao vivo casou com o filtro '{team_filter}'. "
                "Fixture ids com odds ao vivo agora (e o nome do jogo, quando achado):"
            )
            for item in results:
                fid = item.get("fixture", {}).get("id")
                print(f" - {fid}: {names_by_id.get(fid, '(nome nao encontrado)')}")
            return
        print(f"{len(matches)} partida(s) casou(aram) com '{team_filter}':")
        print("=" * 70)
        for item in matches:
            fid = item.get("fixture", {}).get("id")
            print(f"### {names_by_id.get(fid, '?')} (fixture {fid}) ###")
            print(json.dumps(item, indent=2, ensure_ascii=False))
            print("-" * 70)
        return

    # Sem filtro: mostra a resposta CRUA e completa das 2 primeiras
    # partidas - e exatamente essa saida que preciso ver pra ligar o
    # parsing certo.
    for item in results[:2]:
        print(json.dumps(item, indent=2, ensure_ascii=False))
        print("-" * 70)

    if len(results) > 2:
        print(f"(+ {len(results) - 2} outra(s) partida(s) omitida(s) - as 2 primeiras ja bastam)")


if __name__ == "__main__":
    main()
