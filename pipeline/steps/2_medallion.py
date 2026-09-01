"""Étape 2 · médaillon — bronze -> clean -> silver -> gold, 100 % en SQL.

Envoie à ClickHouse chaque dossier `sql/<n>_<couche>/` dans l'ordre, fichier par
fichier (ordre alphabétique intra-dossier). Aucune transformation n'est faite en
Python — la donnée ne sort jamais du moteur.

- `run_all()`       : les 4 couches (bronze -> clean -> silver -> gold).
- `run_layer("bronze")` : une seule couche (pour `eds transform --layer`).

Le nom logique de couche (`bronze`, …) sert au CLI et à `meta.runs` ; le dossier
correspondant est numéroté (`sql/1_bronze/`). Détails d'une couche : voir le
README du dossier (`sql/1_bronze/README.md`) et report/dossier.md § 4-7.
"""

from __future__ import annotations

from pipeline.clickhouse import run_sql_file
from pipeline.config import settings
from pipeline.observabilite import get_logger

log = get_logger("eds.medallion")

# Dossiers sous sql/, dans l'ordre d'exécution.
LAYER_DIRS = ("1_bronze", "2_clean", "3_silver", "4_gold")
# nom logique -> dossier :  "bronze" -> "1_bronze"
_DIR = {d.split("_", 1)[1]: d for d in LAYER_DIRS}
LAYERS = tuple(_DIR)  # ("bronze", "clean", "silver", "gold")


def run_layer(layer: str) -> None:
    layer_dir = settings.sql_dir / _DIR[layer]
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
