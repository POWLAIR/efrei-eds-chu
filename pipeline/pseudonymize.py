"""Pseudonymisation RGPD — appliquée AVANT toute écriture dans le lake.

Règles (cf. docs/context/03-contraintes-rgpd.md) :
  - patient_id  -> hachage déterministe salé (stable => jointures préservées, non réversible)
  - birth_date  -> année seule (généralisation)
  - nir, nom, prenom -> supprimés (identifiants directs)
  - region_code -> conservé (donnée utile aux cohortes, non directement identifiante)

Le même hachage est appliqué à la colonne patient_id de sejours.csv pour garder
le lien patient <-> séjour.
"""

from __future__ import annotations

import csv
import hashlib
import io

from pipeline.config import settings

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
