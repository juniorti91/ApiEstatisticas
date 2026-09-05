"""
Script de USO UNICO - descobre os IDs corretos, na API-Football de
verdade (usando sua propria chave), das ligas que voce pediu para
monitorar. NAO faz parte do app (nao e importado por nada) - roda uma vez,
mostra os resultados, e depois pode ser apagado.

Por que isso existe: eu (Claude) nao tenho como adivinhar com seguranca os
IDs numericos de ~30 ligas de cabeca - varias tem nomes parecidos em
paises diferentes (ex: "Primera Division" existe em Uruguai, Chile,
Venezuela, Paraguai, Costa Rica...) e um ID errado faz aquela liga
simplesmente nunca aparecer como "ao vivo", sem erro nenhum pra avisar -
exatamente o tipo de bug silencioso que ja apareceu antes neste projeto.
Em vez de arriscar isso, este script consulta a API-Football diretamente
(o mesmo endpoint /leagues que o app usaria) e mostra o ID real de cada
uma, pra voce conferir e colar no .env com confianca.

COMO USAR:
    cd backend
    python resolve_leagues.py

Precisa que backend/.env ja tenha API_FOOTBALL_KEY preenchido (o mesmo
que o app usa). Nao precisa do backend estar rodando.
"""
from __future__ import annotations

import time

import httpx
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY", "")
BASE_URL = os.getenv("API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io")

if not API_KEY or API_KEY == "coloque_sua_chave_aqui":
    raise SystemExit("API_FOOTBALL_KEY nao esta configurada no backend/.env - preencha antes de rodar este script.")

# (nome como voce pediu, termo de busca, pais como a API-Football devolve
# no campo country.name - deixe None para competicoes continentais/mundiais
# tipo Libertadores e Champions League. preferred_name, quando preenchido,
# e o nome EXATO da liga na API-Football - usado para escolher automatico
# entre varios resultados parecidos, tipo "Libertadores" vs "Libertadores
# U20" vs "Libertadores Femenina").
#
# IMPORTANTE (corrigido): a API-Football rejeita chamar /leagues com
# "search" e "country" ao mesmo tempo ("The Country field cannot be used
# with the Search field."). Por isso agora so mandamos "search" pra API e
# filtramos por pais/nome aqui no Python depois da resposta chegar.
LEAGUES_TO_RESOLVE = [
    ("Bundesliga (Alemanha)", "Bundesliga", "Germany", "Bundesliga"),
    ("Copa Libertadores", "Libertadores", None, "CONMEBOL Libertadores"),
    ("Copa Sul-Americana", "Sudamericana", None, "CONMEBOL Sudamericana"),
    ("Brasileirão Série A", "Serie A", "Brazil", "Serie A"),
    ("Brasileirão Série B", "Serie B", "Brazil", "Serie B"),
    ("La Liga (Espanha)", "La Liga", "Spain", "La Liga"),
    ("Primeira Liga (Portugal)", "Primeira Liga", "Portugal", "Primeira Liga"),
    ("UEFA Champions League", "Champions League", None, "UEFA Champions League"),
    ("Premier League (Inglaterra)", "Premier League", "England", "Premier League"),
    ("J1 League (Japão)", "J1 League", "Japan", "J1 League"),
    ("K League 1 (Coreia do Sul)", "K League 1", "South-Korea", "K League 1"),
    ("Eliteserien (Noruega)", "Eliteserien", "Norway", "Eliteserien"),
    ("Championship (Inglaterra)", "Championship", "England", "Championship"),
    ("Liga Profesional (Argentina)", "Liga Profesional", "Argentina", "Liga Profesional Argentina"),
    # Uruguai tambem tem uma "Primera Division - Clausura" separada (id
    # proprio) alem da liga principal escolhida aqui - inclua os dois ids
    # impressos abaixo no MONITORED_LEAGUE_IDS final pelo mesmo motivo do
    # Paraguai (ver comentario abaixo).
    ("Primera División (Uruguai)", "Primera Division", "Uruguay", "Primera División"),
    ("Primera División / LFP (Chile)", "Primera Division", "Chile", "Primera División"),
    # Corrigido: "BetPlay" e so o nome do patrocinador atual, a API-Football
    # lista a liga colombiana pelo nome oficial "Primera A".
    ("Liga BetPlay (Colômbia)", "Primera A", "Colombia", "Primera A"),
    # Corrigido: "Liga 1" e o apelido popular, mas a API-Football cadastra
    # a liga peruana como "Primera Division" (mesmo nome usado em varios
    # outros paises da America do Sul).
    ("Liga 1 (Peru)", "Primera Division", "Peru", "Primera División"),
    ("Liga Pro (Equador)", "Liga Pro", "Ecuador", "Liga Pro"),
    ("Primera División (Venezuela)", "Primera Division", "Venezuela", "Primera División"),
    # Paraguai nao tem entrada "Primera Division" na API-Football - a liga
    # e cadastrada como "Division Profesional", dividida em dois torneios
    # por ano (Apertura e Clausura, cada um com o seu proprio id). Este
    # script so escolhe 1 id automatico por linha - depois de rodar, pegue
    # os dois ids impressos abaixo (Apertura e Clausura) e inclua AMBOS no
    # MONITORED_LEAGUE_IDS final, senao partidas de uma das metades do ano
    # ficam de fora sem aviso nenhum.
    ("Primera División (Paraguai)", "Division Profesional", "Paraguay", None),
    # Corrigido: o termo "Division Profesional" so acha a copa (Cup) da
    # Bolivia (id 964) - a liga de pontos corridos de verdade esta listada
    # na API-Football como "Primera Division", igual varios outros paises.
    ("División Profesional (Bolívia)", "Primera Division", "Bolivia", "Primera División"),
    ("Ligue 1 (França)", "Ligue 1", "France", "Ligue 1"),
    ("Liga Panameña (Panamá)", "Liga Panamena", "Panama", "LPF"),
    ("Primera División (Costa Rica)", "Primera Division", "Costa-Rica", "Primera División"),
    ("Eredivisie (Holanda)", "Eredivisie", "Netherlands", "Eredivisie"),
    ("Liga Nacional (Honduras)", "Liga Nacional", "Honduras", "Liga Nacional"),
    ("Pro League (Bélgica)", "Pro League", "Belgium", "Jupiler Pro League"),
    ("Super League (Suíça)", "Super League", "Switzerland", "Super League"),
    ("Austrian Bundesliga (Áustria)", "Bundesliga", "Austria", "Bundesliga"),
    ("Scottish Premiership (Escócia)", "Premiership", "Scotland", "Premiership"),
    ("Super League (Grécia)", "Super League", "Greece", "Super League 1"),
    ("Süper Lig (Turquia)", "Super Lig", "Turkey", "Super Lig"),
    ("Allsvenskan (Suécia)", "Allsvenskan", "Sweden", "Allsvenskan"),
    # Corrigido: buscar "MLS" so acha a copa All-Star e a liga reserva
    # (Next Pro) - a liga principal esta cadastrada pelo nome por extenso.
    ("MLS (EUA / Canadá)", "Major League Soccer", "USA", "Major League Soccer"),
    ("Superligaen (Dinamarca)", "Superliga", "Denmark", "Superliga"),
]

# Palavras que indicam categorias que quase nunca sao a liga principal
# pedida (sub-categorias de base, feminino, versoes "2"/"B" de torneios
# continentais) - usadas so pra FILTRAR ruido antes de decidir, nunca pra
# escolher sozinhas.
NOISE_KEYWORDS = [
    "u15", "u16", "u17", "u18", "u19", "u20", "u21", "u23",
    "women", "female", "feminin", "girls", "youth",
]


def search_league(term: str) -> list[dict]:
    """Busca so por 'search' - a API rejeita combinar com 'country'."""
    resp = httpx.get(
        f"{BASE_URL}/leagues",
        params={"search": term},
        headers={"x-apisports-key": API_KEY},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        print(f"    !! API retornou erro: {data['errors']}")
    return data.get("response", [])


def _is_noise(league_name: str) -> bool:
    lowered = league_name.lower()
    return any(kw in lowered for kw in NOISE_KEYWORDS)


def pick_best_match(
    results: list[dict], country: str | None, preferred_name: str | None
) -> tuple[dict | None, list[dict]]:
    """Filtra os resultados brutos da API por pais (quando informado) e
    remove ruido obvio (sub-20, feminino...). Retorna (escolhido, restantes)
    - escolhido so vem preenchido quando da pra ter certeza (nome exato
    bate com preferred_name, ou sobrou exatamente 1 candidato depois do
    filtro); caso contrario None, e quem le decide a mao com a lista
    'restantes' impressa na tela.
    """
    candidates = results
    if country:
        country_lower = country.lower()
        by_country = [
            item for item in candidates
            if item.get("country", {}).get("name", "").lower() == country_lower
        ]
        if by_country:
            candidates = by_country

    filtered = [item for item in candidates if not _is_noise(item.get("league", {}).get("name", ""))]
    if filtered:
        candidates = filtered

    if preferred_name:
        exact = [
            item for item in candidates
            if item.get("league", {}).get("name", "").strip().lower() == preferred_name.strip().lower()
        ]
        if len(exact) == 1:
            return exact[0], candidates

    if len(candidates) == 1:
        return candidates[0], candidates

    return None, candidates


def main() -> None:
    resolved_ids: list[tuple[str, int]] = []
    ambiguous: list[str] = []
    not_found: list[str] = []

    for display_name, term, country, preferred_name in LEAGUES_TO_RESOLVE:
        print(f"\n{display_name}  (buscando \"{term}\"{f' / pais esperado: {country}' if country else ''})")
        try:
            results = search_league(term)
        except httpx.HTTPError as exc:
            print(f"    !! Falha na chamada: {exc}")
            not_found.append(display_name)
            time.sleep(1.2)
            continue

        if not results:
            print("    Nenhum resultado - tente ajustar o termo de busca manualmente.")
            not_found.append(display_name)
            time.sleep(1.2)
            continue

        best, candidates = pick_best_match(results, country, preferred_name)

        for item in results:
            league = item.get("league", {})
            country_info = item.get("country", {})
            marker = "  <== escolhida" if best is not None and league.get("id") == best.get("league", {}).get("id") else ""
            print(
                f"    id={league.get('id')}  {league.get('name')}  "
                f"({country_info.get('name')})  tipo={league.get('type')}{marker}"
            )

        if best is not None:
            resolved_ids.append((display_name, best["league"].get("id")))
        else:
            print("    !! Nao deu pra decidir sozinho entre os candidatos acima - escolha o id manualmente.")
            ambiguous.append(display_name)

        time.sleep(1.2)  # poupa a cota e evita rate limit do plano gratuito

    print("\n" + "=" * 70)
    print("RESUMO - confira cada liga marcada '<== escolhida' acima antes de usar esta linha:")
    print("=" * 70)
    ids_dedup = sorted(set(i for _, i in resolved_ids if i is not None))
    print("MONITORED_LEAGUE_IDS=" + ",".join(str(i) for i in ids_dedup))

    if ambiguous:
        print("\nAmbiguas - varios candidatos ficaram, escolha o id certo olhando a lista impressa acima:")
        for name in ambiguous:
            print(f"  - {name}")

    if not_found:
        print("\nSem nenhum resultado (ajuste o termo de busca e rode de novo so pra essas, ou me avise):")
        for name in not_found:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
