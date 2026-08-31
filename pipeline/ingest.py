"""Étape 1 — Récupérer : filestorage (lecture seule) -> lake (copie de travail).

Incrémental & idempotent : on ne recopie un fichier que si son hash n'est pas
déjà connu de meta.ingested_files. La pseudonymisation est appliquée pour les
sources identifiantes AVANT écriture.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from pipeline.clickhouse import insert, query
from pipeline.config import SOURCES, settings
from pipeline.logging_conf import get_logger
from pipeline.pseudonymize import transform_csv_bytes

log = get_logger("eds.ingest")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _already_ingested(sha: str) -> bool:
    return bool(query(f"SELECT 1 FROM meta.ingested_files WHERE sha256 = '{sha}' LIMIT 1"))


def _record(rel_path: str, sha: str, source: str, business_date: str, rows: int) -> None:
    bdate = datetime.strptime(business_date, "%Y-%m-%d").date()
    insert(
        "meta.ingested_files",
        [(rel_path, sha, source, bdate, rows, datetime.now(UTC))],
        ["path", "sha256", "source", "business_date", "rows", "ingested_at"],
    )


def ingest_date(business_date: str) -> dict[str, int]:
    """Ingère toutes les sources pour une date de dépôt. Retourne {source: nb_fichiers_copiés}."""
    src_root = settings.source_filestorage
    copied: dict[str, int] = {}

    for source in SOURCES:
        day_dir = src_root / source / business_date
        if not day_dir.is_dir():
            continue
        for f in sorted(day_dir.iterdir()):
            if not f.is_file():
                continue
            raw = f.read_bytes()

            if f.suffix == ".csv":
                payload = transform_csv_bytes(source, raw)
                rows = max(payload.count(b"\n") - 1, 0)
            else:
                payload = raw
                rows = 0  # parquet/json : compté plus tard en SQL (bronze)

            sha = _sha256(payload)
            if _already_ingested(sha):
                log.info("skip (déjà ingéré) %s/%s/%s", source, business_date, f.name)
                continue

            dest = settings.lake_dir / source / business_date / f.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(payload)

            rel = str(Path(source) / business_date / f.name)
            _record(rel, sha, source, business_date, rows)
            copied[source] = copied.get(source, 0) + 1
            log.info("lake <- %s  (%d lignes)", rel, rows)

    return copied
