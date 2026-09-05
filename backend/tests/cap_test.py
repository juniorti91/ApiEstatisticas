"""
Teste de fumaca do limite de partidas monitoradas simultaneamente
(MAX_MONITORED_FIXTURES). Simula 5 partidas ao vivo com o limite setado
para 3 e confere que so as 3 primeiras entram em observacao, e que uma
partida ja monitorada continua sendo atualizada mesmo com o limite cheio.
"""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.config import settings
from app.database import AsyncSessionLocal, init_db
from app.models.fixture import Fixture
from app.services import collector


def _fake_fixture(fid: int, minute: int = 10) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "fixture": {"id": fid, "date": now, "status": {"short": "1H", "elapsed": minute}},
        "league": {"id": 1, "name": "Liga Teste", "country": "Testland", "round": "R1"},
        "teams": {
            "home": {"id": 1000 + fid, "name": f"Time Casa {fid}", "logo": ""},
            "away": {"id": 2000 + fid, "name": f"Time Fora {fid}", "logo": ""},
        },
        "goals": {"home": 0, "away": 0},
    }


async def main() -> None:
    await init_db()
    settings.max_monitored_fixtures = 3

    async with AsyncSessionLocal() as session:
        # Primeira rodada: 5 partidas ao vivo aparecem de uma vez, limite e 3
        fake_fixtures = [_fake_fixture(fid) for fid in range(1, 6)]
        with patch.object(collector.api_football_client, "live_fixtures", new=AsyncMock(return_value=fake_fixtures)):
            tracked = await collector.scan_live_fixtures(session)

        assert len(tracked) == 3, f"Esperava 3 partidas monitoradas, veio {len(tracked)}"
        print(f"OK: com limite=3 e 5 partidas ao vivo, monitorou {len(tracked)} (as 3 primeiras).")

        # Segunda rodada: as mesmas 5 partidas continuam ao vivo. As 3 ja
        # monitoradas devem continuar sendo atualizadas (nao somem), e
        # nenhuma partida NOVA deve entrar (limite continua cheio).
        with patch.object(collector.api_football_client, "live_fixtures", new=AsyncMock(return_value=fake_fixtures)):
            tracked_again = await collector.scan_live_fixtures(session)

        assert len(tracked_again) == 3, f"Esperava continuar com 3, veio {len(tracked_again)}"

        from sqlalchemy import select
        result = await session.execute(select(Fixture).where(Fixture.is_monitored.is_(True)))
        monitored_ids = sorted(f.api_fixture_id for f in result.scalars().all())
        assert monitored_ids == [1, 2, 3], f"Esperava manter fixtures [1,2,3] monitoradas, veio {monitored_ids}"
        print(f"OK: no ciclo seguinte, continuam monitoradas as mesmas {monitored_ids} (nenhuma nova entrou).")

    print("\nCAP TEST OK")


if __name__ == "__main__":
    asyncio.run(main())
