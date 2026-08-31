"""Traçabilité des exécutions — table meta.runs.

Chaque commande du pipeline enregistre une ligne à sa terminaison (succès ou
échec), avec ses horodatages de début/fin. Permet de répondre à « d'où vient
chaque donnée et quand a-t-elle été traitée ».
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime

from pipeline.clickhouse import insert
from pipeline.logging_conf import get_logger

log = get_logger("eds.runs")

_COLS = [
    "run_id",
    "action",
    "layer",
    "business_date",
    "started_at",
    "finished_at",
    "status",
    "error",
]


@contextmanager
def track(action: str, layer: str = "", business_date: str = ""):
    run_id = str(uuid.uuid4())
    started = datetime.now(UTC)
    log.info("run %s  %s  %s %s  (début)", run_id[:8], action, layer, business_date)
    try:
        yield run_id
    except Exception as exc:
        _record(run_id, action, layer, business_date, started, "error", str(exc)[:500])
        log.exception("run %s  ÉCHEC", run_id[:8])
        raise
    else:
        _record(run_id, action, layer, business_date, started, "success", "")
        log.info("run %s  OK", run_id[:8])


def _record(run_id, action, layer, business_date, started, status, error):
    bdate = datetime.strptime(business_date, "%Y-%m-%d").date() if business_date else None
    insert(
        "meta.runs",
        [(run_id, action, layer, bdate, started, datetime.now(UTC), status, error)],
        _COLS,
    )
