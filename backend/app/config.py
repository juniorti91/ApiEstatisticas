"""
Configuracoes centrais da aplicacao.

Le valores do arquivo .env uma unica vez e expoe um objeto `settings`
singleton, evitando leitura repetida de variaveis de ambiente em todo o
codigo (organizacao + performance).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_football_key: str = ""
    api_football_base_url: str = "https://v3.football.api-sports.io"

    database_url: str = "sqlite+aiosqlite:///./betanalyzer.db"

    # Ciclo principal de coleta: busca TODAS as estatisticas disponiveis de
    # cada partida monitorada (de time via /fixtures/statistics + de
    # jogador via /fixtures/players) e grava um MatchSnapshot completo.
    # Volta a 5 min por pedido explicito do usuario (chegou a ser 3 min
    # antes) - sao 2 requisicoes de API por partida a cada ciclo. Combine
    # com MONITORED_LEAGUE_IDS e MAX_MONITORED_FIXTURES abaixo se sua cota
    # diaria for apertada.
    collector_interval_minutes: int = 5
    live_scan_interval_minutes: int = 2

    # Ciclo dedicado que SO reconsulta as odds ao vivo e recalcula as
    # recomendacoes (usa o ultimo snapshot ja salvo, sem buscar
    # estatisticas novas de novo). Em SEGUNDOS (nao minutos, como os dois
    # ciclos acima) - desde que passamos a usar /odds/live (1 UNICA
    # chamada de API cobre TODAS as partidas ao vivo de uma vez, ver
    # odds_service.fetch_live_odds_by_fixture), rodar isso com muito mais
    # frequencia ficou barato: nao escala com o numero de partidas
    # monitoradas. Ainda assim nao adianta descer muito de ~30-60s: pela
    # propria resposta da API-Football, o campo "update" de cada partida
    # vem arredondado ao minuto - ou seja, a fonte de dados deles parece
    # atualizar internamente por volta de 1x/minuto, entao consultar bem
    # mais rapido que isso so gastaria cota sem trazer dado mais fresco.
    # So pode ser mudado aqui/no .env - por pedido explicito do usuario,
    # NAO existe mais edicao pela tela (ver app/routers/settings.py, que
    # agora e so-leitura).
    odds_refresh_interval_seconds: int = 60

    # As 15 ligas de maior volume/liquidez no mercado de apostas que o
    # usuario decidiu manter (reduzido de 38 para caber com folga na cota
    # diaria da API-Football): Champions League(2), Sul-Americana(11),
    # Libertadores(13), Premier League(39), Championship(40), Ligue 1(61),
    # Brasileirao Serie A(71) e Serie B(72), Bundesliga(78), Eredivisie(88),
    # Primeira Liga Portugal(94), Liga Profesional Argentina(128),
    # La Liga(140), Super Lig Turquia(203), MLS(253).
    monitored_league_ids: str = "2,11,13,39,40,61,71,72,78,88,94,128,140,203,253"

    # Limite de partidas monitoradas simultaneamente - protege a cota diaria
    # da API. Partidas ja em observacao continuam sendo atualizadas mesmo
    # acima do limite; ele so barra a ENTRADA de novas partidas quando o
    # limite bate. Cada partida monitorada custa ~3 requisicoes por ciclo de
    # 5 min (estatisticas de time + de jogador + odds, depois de tirar a
    # duplicidade que existia entre collect_job e odds_job - ver
    # scheduler.py). Com 15 ligas de alto volume em vez de 38 aleatorias,
    # 15 vagas simultaneas cobrem tranquilamente ate rodadas cheias (ex:
    # sabado com Championship inteiro as 15h no mesmo horario) mantendo o
    # consumo diario com boa folga sob os ~7500/dia do plano Pro.
    max_monitored_fixtures: int = 15

    # Quantas das ultimas partidas de cada time usar para calcular a "forma"
    # (media de escanteios, chutes, gols...). O pedido original permite 3 ou
    # 5 - usar 3 reduz em ~40% as chamadas de API gastas nesse calculo.
    team_form_sample_size: int = 3

    # Pode conter uma ou mais URLs separadas por virgula (ex:
    # "https://betanalyzer.vercel.app,https://outra-url.vercel.app") - ver
    # frontend_origin_list abaixo, usado pelo CORS em main.py.
    frontend_origin: str = "http://localhost:5173"

    @property
    def monitored_league_id_list(self) -> list[int]:
        return [int(x) for x in self.monitored_league_ids.split(",") if x.strip()]

    @property
    def frontend_origin_list(self) -> list[str]:
        return [x.strip() for x in self.frontend_origin.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
