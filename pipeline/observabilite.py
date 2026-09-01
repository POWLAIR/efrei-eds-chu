"""Plomberie — observabilité : journalisation + traçabilité des exécutions.

- `get_logger(name)` : logger console + fichier horodaté `logs/pipeline-AAAAMMJJ.log`,
  utilisé par toutes les étapes.
- `track(action, …)` : context manager qui enveloppe chaque commande du CLI et
  écrit une ligne dans `meta.runs` à sa terminaison (horodatages début/fin, statut
  succès/échec, message d'erreur). Répond à « d'où vient la donnée, quand a-t-elle
  été traitée » (Partie 2 — automatisation).
"""

from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime

from pipeline.config import settings

# --- Journalisation ----------------------------------------------------------


def get_logger(name: str = "eds") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(name)s  %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    settings.logs_dir.mkdir(exist_ok=True)
    fileh = logging.FileHandler(settings.logs_dir / f"pipeline-{datetime.now(UTC):%Y%m%d}.log")
    fileh.setFormatter(fmt)
    logger.addHandler(fileh)

    return logger


# --- Traçabilité : meta.runs ------------------------------------------------

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
    from pipeline.clickhouse import insert  # local : évite le cycle clickhouse <-> observabilite

    bdate = datetime.strptime(business_date, "%Y-%m-%d").date() if business_date else None
    insert(
        "meta.runs",
        [(run_id, action, layer, bdate, started, datetime.now(UTC), status, error)],
        _COLS,
    )
