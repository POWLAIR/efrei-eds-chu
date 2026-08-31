"""Étapes 2-3 — Fiabiliser & Restituer : bronze -> clean -> silver -> gold, 100 % en SQL.

Python se contente d'envoyer les fichiers sql/ dans l'ordre des couches.
Aucune donnée ne sort de ClickHouse.

La couche `clean` ne contient que le journal de quarantaine `clean.rejects` (DDL) ;
il est alimenté au fil du filtrage par les transformations `sql/silver/*.sql`.
"""

from __future__ import annotations

from pipeline.clickhouse import run_sql_file
from pipeline.config import settings
from pipeline.logging_conf import get_logger

log = get_logger("eds.transform")

LAYERS = ("bronze", "clean", "silver", "gold")


def run_layer(layer: str) -> None:
    layer_dir = settings.sql_dir / layer
    files = sorted(layer_dir.glob("*.sql"))
    if not files:
        log.warning("aucun fichier SQL dans %s (à implémenter)", layer_dir)
        return
    for f in files:
        run_sql_file(f)


def run_all() -> None:
    for layer in LAYERS:
        log.info("=== couche %s ===", layer)
        run_layer(layer)
