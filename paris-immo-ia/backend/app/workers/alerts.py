"""Tâche de fond des alertes.

    python -m app.workers.alerts            # un passage (idéal en cron / Cloud Scheduler)
    python -m app.workers.alerts --loop 300 # boucle toutes les 5 minutes
"""

import argparse
import asyncio
import logging
import time

from fastapi.concurrency import run_in_threadpool

from ..db import SessionLocal
from ..services.alerts import check_alerts

log = logging.getLogger(__name__)


def run_once() -> int:
    with SessionLocal() as db:
        sent = check_alerts(db)
    for n in sent:
        log.info("Alerte %s : %d bien(s) envoyé(s) à %s", n.alert_id, len(n.matches), n.email)
    return len(sent)


async def periodic(interval: int) -> None:
    """Boucle intégrée au process FastAPI (ALERTS_INTERVAL_SECONDS > 0)."""
    while True:
        try:
            await run_in_threadpool(run_once)
        except Exception:
            log.exception("Échec du passage des alertes")
        await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--loop", type=int, metavar="SECONDES", help="répéter à cet intervalle")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not args.loop:
        run_once()
        return
    while True:
        try:
            run_once()
        except Exception:
            log.exception("Échec du passage des alertes")
        time.sleep(args.loop)


if __name__ == "__main__":
    main()
