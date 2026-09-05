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
    # estatisticas novas de novo). So pode ser mudado aqui/no .env - por
    # pedido explicito do usuario, NAO existe mais edicao pela tela (ver
    # app/routers/settings.py, que agora e so-leitura).
    odds_refresh_interval_minutes: int = 5

    monitored_league_ids: str = "39,140,135,78,61,71"

    # Limite de partidas monitoradas simultaneamente - protege a cota diaria
    # da API quando MONITORED_LEAGUE_IDS fica vazio (todas as ligas do mundo).
    # Partidas ja em observacao continuam sendo atualizadas mesmo acima do
    # limite; ele so barra a ENTRADA de novas partidas quando o limite bate.
    # Reduzido de 15 para 8: cada partida monitorada custa ~2 requisicoes
    # por ciclo de coleta de 5 min (estatisticas + odds ao vivo), entao 15
    # partidas geravam ~30 so nesse ciclo, alem do burst de ~8 chamadas
    # extras na primeira vez que um time novo aparece (calculo de forma).
    max_monitored_fixtures: int = 8

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
