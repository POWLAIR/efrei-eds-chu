"""Les 4 étapes du pipeline EDS, dans l'ordre. Le numéro est en tête de fichier.

    1_lake.py        filestorage (lecture seule) -> data/lake/  (pseudonymisé, incrémental)
    2_medallion.py   bronze -> clean -> silver -> gold  — 100 % SQL dans ClickHouse
                     (joue sql/1_bronze/ … sql/4_gold/)
    3_verify.py      contrôles de fiabilité — joue sql/5_checks/, exit != 0 si un échoue
    4_dashboards.py  restitution — provisionne Metabase (2 dashboards, idempotent)

`eds run-daily` enchaîne 1 -> 2 -> 3 dans un seul run tracé ; `eds dashboards`
lance 4. Bootstrap une fois : `make init-db` (sql/0_init/).

Les noms de modules commencent par un chiffre (illisibles en `import` direct) :
ce module les ré-expose sous un nom propre, à la demande —
`from pipeline.steps import lake, medallion`.
"""

from importlib import import_module

_MODULES = {
    "lake": ".1_lake",
    "medallion": ".2_medallion",
    "verify": ".3_verify",
    "dashboards": ".4_dashboards",
}


def __getattr__(name: str):  # PEP 562 — import paresseux
    if name in _MODULES:
        return import_module(_MODULES[name], __name__)
    raise AttributeError(f"module {__name__!r} n'a pas d'attribut {name!r}")


def __dir__() -> list[str]:
    return [*globals(), *_MODULES]
