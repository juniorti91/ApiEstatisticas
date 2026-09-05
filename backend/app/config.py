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

    collector_interval_minutes: int = 5
    live_scan_interval_minutes: int = 2
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

    # Aceita uma ou varias origens separadas por virgula (ex: em producao,
    # a URL do frontend na Vercel + previews + localhost para dev local).
    frontend_origin: str = "http://localhost:5173"

    @property
    def monitored_league_id_list(self) -> list[int]:
        return [int(x) for x in self.monitored_league_ids.split(",") if x.strip()]

    @property
    def frontend_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
