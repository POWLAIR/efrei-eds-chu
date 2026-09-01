"""Plomberie — seul module qui parle au moteur ClickHouse (clickhouse-connect).

`client()` (connexion), `run_sql_file()` (envoie un `.sql` versionné de `sql/`),
`query()` et `insert()` pour les contrôles et la traçabilité. Python n'exécute
aucune transformation : il envoie le SQL, la donnée ne sort pas du moteur.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import clickhouse_connect

from pipeline.config import settings
from pipeline.observabilite import get_logger

log = get_logger("eds.ch")


def client():
    return clickhouse_connect.get_client(
        host=settings.ch_host,
        port=settings.ch_http_port,
        username=settings.ch_user,
        password=settings.ch_password,
        database=settings.ch_database,
    )


def _split_statements(sql: str) -> list[str]:
    # Découpe naïve sur ';' en ignorant les lignes de commentaire pur.
    cleaned = "\n".join(l for l in sql.splitlines() if not l.strip().startswith("--"))
    return [s.strip() for s in cleaned.split(";") if s.strip()]


def run_sql_file(path: str | Path) -> None:
    path = Path(path)
    log.info("SQL <- %s", path)
    statements = _split_statements(path.read_text(encoding="utf-8"))
    c = client()
    for stmt in statements:
        c.command(stmt)


def query(sql: str) -> list[tuple[Any, ...]]:
    return client().query(sql).result_rows


def insert(table: str, rows: list[tuple], column_names: list[str]) -> None:
    client().insert(table, rows, column_names=column_names)
