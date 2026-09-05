# BetAnalyzer - In-Play Analytics

Sistema de estatísticas e recomendações in-live de futebol: coleta dados de partidas ao vivo (via API-Football ou inserção manual), armazena um snapshot a cada 5 minutos, compara o desempenho ao vivo com a média das últimas 3-5 partidas de cada time, sugere entradas com probabilidade estimada / EV / confiança, e confere automaticamente se a recomendação acertou ou errou ao final da partida.

## Estrutura

```
ApiEstatisticas/
├── backend/     FastAPI + SQLAlchemy (assíncrono) + APScheduler + SQLite
└── frontend/    React + Vite + Tailwind + Recharts
```

## Como funciona (visão geral)

1. **Scan (a cada 2 min)**: busca partidas ao vivo nas ligas configuradas em `MONITORED_LEAGUE_IDS` e começa a monitorá-las.
2. **Coleta (a cada 5 min)**: para cada partida monitorada, busca as estatísticas atuais (escanteios, chutes, posse, cartões, faltas...) e grava um `MatchSnapshot` no banco.
3. **Motor de recomendação**: a cada coleta, recalcula os mercados (escanteios do time em ritmo mais forte, total de gols, ambos marcam) comparando a projeção ao vivo com a média histórica do time (`TeamForm`, calculada a partir das últimas 3-5 partidas). Gera probabilidade estimada, EV, confiança e uma justificativa em texto.
4. **Odds**: quando a API retorna cotação ao vivo para o mercado, ela é usada; quando não, o sistema calcula uma "odd justa" a partir da própria probabilidade estimada (com margem), deixando isso explícito na recomendação.
5. **Conferência de resultados**: quando a partida termina (status FT), cada recomendação pendente é avaliada contra o resultado final e marcada como `win` ou `loss`, alimentando o painel de performance (taxa de acerto, ROI, lucro/prejuízo).
6. **Inserção manual**: se uma partida não estiver disponível pela API, os dados podem ser inseridos manualmente pelo próprio dashboard (aba "Inserir estatísticas manualmente").

## Backend

### Requisitos
- Python 3.11+

### Configuração

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

O arquivo `backend/.env` já vem preenchido com a chave da API-Football informada. Revise os demais valores se quiser:

- `MONITORED_LEAGUE_IDS`: IDs das ligas monitoradas automaticamente (Premier League, La Liga, Serie A, Bundesliga, Ligue 1 e Brasileirão por padrão).
- `COLLECTOR_INTERVAL_MINUTES`: intervalo de coleta de estatísticas (padrão 5 min, conforme pedido).
- `LIVE_SCAN_INTERVAL_MINUTES`: intervalo de varredura por novas partidas ao vivo (padrão 2 min).
- `DATABASE_URL`: SQLite por padrão (zero configuração). Para produção, troque por uma URL Postgres (ex: `postgresql+asyncpg://usuario:senha@localhost:5432/betanalyzer`) - nenhum código precisa mudar, só essa variável.

### Rodando

```bash
uvicorn app.main:app --reload --port 8000
```

A API sobe em `http://127.0.0.1:8000`, cria o banco automaticamente (`backend/betanalyzer.db`) e já inicia o agendador de coleta em background. Documentação interativa em `http://127.0.0.1:8000/docs`.

### Teste rápido sem esperar uma partida ao vivo

`backend/tests/smoke_test.py` roda o pipeline inteiro (recomendação + conferência de resultado) com dados simulados, sem depender de rede:

```bash
PYTHONPATH=. python tests/smoke_test.py
```

### Nota importante sobre a API-Football

Este projeto foi desenvolvido e testado em um ambiente de nuvem cujo acesso à internet é restrito por política da organização (o host `v3.football.api-sports.io` foi bloqueado no proxy de saída durante os testes). Por isso a integração real com a API não pôde ser validada fim-a-fim aqui - toda a lógica de parsing, tratamento de erro e fallback foi validada com dados simulados (veja `smoke_test.py`). Ao rodar na sua máquina (com internet normal), a chamada real deve funcionar; se aparecer erro 403/401 nos logs, confira se a chave em `backend/.env` ainda está ativa no painel da api-football.com e se o plano contratado cobre os endpoints usados (`/fixtures`, `/fixtures/statistics`, `/odds`).

## Frontend

### Requisitos
- Node.js 18+

### Configuração e execução

```bash
cd frontend
npm install
npm run dev
```

Abre em `http://localhost:5173`. Em desenvolvimento, o Vite já faz proxy de `/api` para `http://127.0.0.1:8000` (veja `vite.config.js`) - não precisa configurar CORS nem URL manualmente. Para apontar para outro backend, copie `.env.example` para `.env` e defina `VITE_API_BASE_URL`.

### Build de produção

```bash
npm run build
```

Gera os arquivos estáticos em `frontend/dist`.

## Principais endpoints da API

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/matches/live` | Partidas ao vivo monitoradas |
| GET | `/api/matches/{id}` | Detalhe de uma partida |
| GET | `/api/matches/{id}/snapshots` | Histórico de snapshots (a cada 5 min) |
| GET | `/api/matches/{id}/comparison` | Média últimas partidas x desempenho atual |
| POST | `/api/matches/track/{api_fixture_id}` | Passa a monitorar uma partida específica |
| POST | `/api/matches/{id}/snapshots/manual` | Insere um snapshot manualmente |
| GET | `/api/recommendations/fixture/{id}` | Recomendações de uma partida |
| GET | `/api/recommendations/{id}/odds-history` | Evolução da odd/probabilidade de uma recomendação |
| GET | `/api/history/recommendations` | Histórico de recomendações (com resultado) |
| GET | `/api/dashboard/performance` | Taxa de acerto, ROI, lucro/prejuízo |
| POST | `/api/dashboard/collect-now` | Dispara um ciclo de coleta/recomendação na hora (sem esperar os 5 min) |

## Próximos passos sugeridos

- Trocar `DATABASE_URL` para Postgres em produção (multiusuário / múltiplas partidas simultâneas).
- Adicionar autenticação antes de expor a API publicamente.
- Enriquecer o motor de recomendação com mais mercados (cartões, handicap asiático) e, futuramente, um modelo estatístico mais sofisticado (ex: Dixon-Coles) no lugar da aproximação Poisson atual.
- Persistir o histórico de odds de todas as recomendações (não só as que passaram no filtro) para permitir backtesting do motor.
