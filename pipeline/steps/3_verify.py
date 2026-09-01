"""Étape 3 · verify — contrôles de fiabilité (`eds verify`), joués après le gold.

Chaque fichier `sql/5_checks/*.sql` renvoie **0 ligne si le contrôle passe**, et les
lignes fautives sinon. `verify()` sort en exception si au moins un contrôle échoue,
de sorte que `make verify` / le cron s'arrêtent en erreur.
"""

from __future__ import annotations

from pipeline.clickhouse import client
from pipeline.config import settings
from pipeline.observabilite import get_logger

log = get_logger("eds.verify")


class VerificationError(RuntimeError):
    pass


def run_checks() -> list[tuple[str, int]]:
    """Retourne la liste (nom, nb_lignes_fautives). nb=0 => OK."""
    checks_dir = settings.sql_dir / "5_checks"
    results: list[tuple[str, int]] = []
    c = client()
    for f in sorted(checks_dir.glob("*.sql")):
        sql = "\n".join(
            line for line in f.read_text(encoding="utf-8").splitlines()
            if not line.strip().startswith("--")
        ).strip().rstrip(";")
        rows = c.query(sql).result_rows
        n = len(rows)
        status = "OK  " if n == 0 else "ÉCHEC"
        log.info("%s  %s%s", status, f.name, f"  ({n} ligne(s) : {rows[:3]})" if n else "")
        results.append((f.name, n))
    return results


def verify() -> None:
    results = run_checks()
    failed = [name for name, n in results if n]
    log.info("%d/%d contrôles OK", len(results) - len(failed), len(results))
    if failed:
        raise VerificationError("contrôles en échec : " + ", ".join(failed))
