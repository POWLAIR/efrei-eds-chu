"""Étape 1 · lake — récupérer : filestorage (lecture seule) -> data/lake/ (copie de travail).

Point d'entrée : `ingest_date()`, appelé par `eds ingest` / `run-daily` / `replay`.
Incrémental & idempotent : un fichier n'est recopié que si son hash (du contenu
*après* pseudonymisation) est inconnu de `meta.ingested_files`.

Pseudonymisation RGPD — appliquée AVANT toute écriture dans le lake, pour
`patients.csv` et `sejours.csv` (cf. docs/context/03-contraintes-rgpd.md) :
  - patient_id        -> hachage déterministe salé (stable => jointures préservées, non réversible)
  - birth_date        -> année seule (généralisation)
  - nir, nom, prenom  -> supprimés (identifiants directs)
  - region_code       -> conservé (utile aux cohortes, non directement identifiant)
Le même hachage est appliqué au `patient_id` de `sejours.csv` -> le lien
patient <-> séjour est conservé. Aucune donnée identifiante n'atteint le lake.
"""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import UTC, datetime
from pathlib import Path

from pipeline.clickhouse import insert, query
from pipeline.config import SOURCES, settings
from pipeline.observabilite import get_logger

log = get_logger("eds.lake")


# --- Pseudonymisation RGPD (à l'entrée du lake) -------------------------------

_PATIENTS_DROP = {"nir", "nom", "prenom"}


def pseudonymize_patient_id(patient_id: str) -> str:
    salt = settings.require_salt()
    digest = hashlib.sha256(f"{salt}:{patient_id}".encode()).hexdigest()
    return digest[:16]


def _year(value: str) -> str:
    return value.strip()[:4] if value and value.strip() else ""


def transform_csv_bytes(source: str, raw: bytes) -> bytes:
    """Retourne le CSV pseudonymisé pour patients/ et sejours/. Sinon renvoie tel quel."""
    if source not in ("patients", "sejours"):
        return raw

    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    rows_in = list(reader)
    fields = list(reader.fieldnames or [])

    if source == "patients":
        out_fields = [f for f in fields if f not in _PATIENTS_DROP]
        if "birth_date" in out_fields:
            out_fields[out_fields.index("birth_date")] = "birth_year"
        if "patient_id" in out_fields:
            out_fields[out_fields.index("patient_id")] = "patient_hash"

        def convert(r: dict) -> dict:
            o = {
                k: r[k]
                for k in fields
                if k not in _PATIENTS_DROP and k not in ("birth_date", "patient_id")
            }
            o["patient_hash"] = pseudonymize_patient_id(r["patient_id"])
            o["birth_year"] = _year(r.get("birth_date", ""))
            return o

    else:  # sejours : on remplace juste patient_id par son hash
        out_fields = ["patient_hash" if f == "patient_id" else f for f in fields]

        def convert(r: dict) -> dict:
            o = dict(r)
            o["patient_hash"] = pseudonymize_patient_id(o.pop("patient_id"))
            return o

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=out_fields)
    writer.writeheader()
    for r in rows_in:
        writer.writerow(convert(r))
    return buf.getvalue().encode("utf-8")


# --- Ingestion filestorage -> lake (incrémentale) ----------------------------


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
