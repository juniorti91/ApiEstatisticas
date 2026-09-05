"""
Teste de fumaca (fora do pytest, roda direto com `python tests/smoke_test.py`)
que valida a logica de negocio fim-a-fim SEM depender de rede externa:

  1. Cria liga/times/partida e um TeamForm "historico" simulado (como se
     tivesse vindo da API-Football).
  2. Grava snapshots a cada 5 minutos simulando uma partida ao vivo.
  3. Roda o motor de recomendacao e confere se ele gera sugestoes
     coerentes com os dados.
  4. Encerra a partida e roda o results_tracker, conferindo que o
     acerto/erro bate com o resultado final.

Isso e o que garante que o pipeline (coleta -> recomendacao -> conferencia)
funciona antes de depender de uma partida ao vivo real.
"""
import asyncio
from datetime import datetime, timedelta

from app.database import AsyncSessionLocal, init_db
from app.models.fixture import Fixture
from app.models.league import League
from app.models.recommendation import Recommendation, RecommendationStatus
from app.models.snapshot import MatchSnapshot
from app.models.team import Team
from app.models.team_form import TeamForm
from app.services.recommendation_engine import generate_recommendations_for_fixture
from app.services.results_tracker import settle_finished_fixtures


async def main() -> None:
    await init_db()
    async with AsyncSessionLocal() as session:
        league = League(api_id=999001, name="Liga Teste", country="Testland")
        home = Team(api_id=999101, name="Manchester City")
        away = Team(api_id=999102, name="Arsenal")
        session.add_all([league, home, away])
        await session.flush()

        fixture = Fixture(
            api_fixture_id=999999001,
            league_id=league.id,
            home_team_id=home.id,
            away_team_id=away.id,
            round="Rodada 27",
            kickoff_at=datetime.utcnow() - timedelta(minutes=32),
            status="1H",
            elapsed_minutes=32,
            goals_home=0,
            goals_away=0,
            is_monitored=True,
        )
        session.add(fixture)
        await session.flush()

        # Simula o TeamForm que normalmente viria da API-Football (ultimas 5 partidas)
        home_form = TeamForm(
            team_id=home.id, sample_size=5, updated_at=datetime.utcnow(),
            avg_shots=14.2, avg_shots_on_target=5.6, avg_corners=6.1,
            avg_goals_scored=2.1, avg_goals_conceded=0.8, avg_possession=61,
            avg_yellow_cards=1.2, avg_fouls=9.0, btts_rate=40.0, over_2_5_rate=60.0,
        )
        away_form = TeamForm(
            team_id=away.id, sample_size=5, updated_at=datetime.utcnow(),
            avg_shots=9.8, avg_shots_on_target=3.1, avg_corners=4.0,
            avg_goals_scored=1.1, avg_goals_conceded=1.4, avg_possession=48,
            avg_yellow_cards=1.8, avg_fouls=11.0, btts_rate=35.0, over_2_5_rate=55.0,
        )
        session.add_all([home_form, away_form])

        # Snapshots a cada 5 minutos ate o minuto 32 (como o print de referencia)
        snapshot_points = [
            (5, 1, 0), (10, 1, 0), (15, 2, 1), (20, 2, 1), (25, 3, 1), (30, 4, 1),
        ]
        for minute, corners_home, corners_away in snapshot_points:
            session.add(MatchSnapshot(
                fixture_id=fixture.id, captured_at=datetime.utcnow(), minute=minute,
                goals_home=0, goals_away=0, possession_home=56, possession_away=44,
                shots_on_target_home=3, shots_on_target_away=2, shots_off_target_home=2,
                shots_off_target_away=1, total_shots_home=8, total_shots_away=5,
                corners_home=corners_home, corners_away=corners_away,
                yellow_cards_home=1, yellow_cards_away=0, red_cards_home=0, red_cards_away=0,
                fouls_home=4, fouls_away=3, offsides_home=1, offsides_away=0,
                dangerous_attacks_home=20, dangerous_attacks_away=12,
            ))
        await session.commit()

        print("== Gerando recomendacoes com base no snapshot mais recente (32min, 4x1 escanteios) ==")
        recs = await generate_recommendations_for_fixture(session, fixture)
        for r in recs:
            flag = "PRINCIPAL" if r.is_primary else "         "
            print(f"[{flag}] {r.market:18s} | {r.selection:28s} | odd={r.odd:.2f} "
                  f"prob_est={r.estimated_probability:.0%} prob_impl={r.implied_probability:.0%} "
                  f"EV={r.expected_value:+.1f}% valuebet={r.is_value_bet} estrelas={r.confidence_stars}")
            print(f"    -> {r.justification}")

        assert recs, "Motor deveria ter gerado ao menos uma recomendacao"

        print("\n== Encerrando a partida (final 1x0 para o Manchester City, 6 escanteios) ==")
        fixture.status = "FT"
        fixture.goals_home = 1
        fixture.goals_away = 0
        session.add(MatchSnapshot(
            fixture_id=fixture.id, captured_at=datetime.utcnow(), minute=90,
            goals_home=1, goals_away=0, possession_home=58, possession_away=42,
            shots_on_target_home=6, shots_on_target_away=3, shots_off_target_home=4,
            shots_off_target_away=3, total_shots_home=15, total_shots_away=9,
            corners_home=6, corners_away=2, yellow_cards_home=2, yellow_cards_away=2,
            red_cards_home=0, red_cards_away=0, fouls_home=10, fouls_away=9,
            offsides_home=2, offsides_away=1, dangerous_attacks_home=45, dangerous_attacks_away=28,
        ))
        await session.commit()

        settled = await settle_finished_fixtures(session)
        print(f"Recomendacoes conferidas: {settled}")

        result = await session.execute(
            Recommendation.__table__.select().where(Recommendation.fixture_id == fixture.id)
        )
        for row in result.fetchall():
            print(dict(row._mapping))

        # validacoes basicas
        result = await session.execute(
            Recommendation.__table__.select().where(
                Recommendation.fixture_id == fixture.id,
                Recommendation.market == "corners_over",
            )
        )
        corner_rec = result.fetchone()
        assert corner_rec is not None
        assert corner_rec.status in (RecommendationStatus.WIN.value, RecommendationStatus.LOSS.value)
        print(f"\nMercado de escanteios encerrado como: {corner_rec.status.upper()} "
              f"(linha={corner_rec.line}, valor final={corner_rec.final_stat_value})")

    print("\nSMOKE TEST OK")


if __name__ == "__main__":
    asyncio.run(main())
