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
from app.routers import dashboard, history, matches, recommendations
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(matches.router)
app.include_router(recommendations.router)
app.include_router(history.router)
app.include_router(dashboard.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
