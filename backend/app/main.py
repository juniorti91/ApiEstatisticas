"""
Ponto de entrada da API BetAnalyzer.

Sobe o FastAPI, cria as tabelas do banco se ainda nao existirem, liga o
scheduler de coleta/recomendacao em background e registra os routers.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import dashboard, history, matches, recommendations, settings as settings_router, teams
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="BetAnalyzer API",
    description="Coleta, armazena e analisa estatisticas de partidas de futebol ao vivo para recomendacoes in-play.",
    version="1.0.0",
    lifespan=lifespan,
)

# FRONTEND_ORIGIN pode conter uma ou mais URLs separadas por virgula (ex:
# "https://betanalyzer.vercel.app,https://betanalyzer-git-main-seu-user.vercel.app").
# Os localhost de dev ficam sempre liberados, mesmo em producao, para nao
# quebrar quem roda o frontend localmente contra o backend hospedado.
allowed_origins = list(
    dict.fromkeys(settings.frontend_origin_list + ["http://localhost:5173", "http://127.0.0.1:5173"])
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # Cobre automaticamente os deploys de preview da Vercel (URLs geradas
    # tipo https://betanalyzer-<hash>-<user>.vercel.app), que mudam a cada
    # deploy e nao dariam pra listar uma a uma em FRONTEND_ORIGIN.
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(matches.router)
app.include_router(recommendations.router)
app.include_router(history.router)
app.include_router(dashboard.router)
app.include_router(settings_router.router)
app.include_router(teams.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
