"""CLI du pipeline EDS.  `uv run eds --help`"""

from __future__ import annotations

from datetime import UTC, datetime

import typer

from pipeline.clickhouse import query, run_sql_file
from pipeline.ingest import ingest_date
from pipeline.logging_conf import get_logger
from pipeline.runs import track
from pipeline.transform import run_all, run_layer

app = typer.Typer(
    add_completion=False, help="Pipeline ELT médaillon de l'Entrepôt de Données de Santé du CHU."
)
log = get_logger("eds.cli")


@app.command()
def run(
    files: list[str] = typer.Argument(..., help="Fichiers .sql à exécuter"),
    sql_only: bool = typer.Option(
        False, "--sql-only", help="Exécute sans tracer dans meta.runs (bootstrap)"
    ),
):
    """Exécute des fichiers SQL bruts (utilisé par `make init-db`)."""
    for f in files:
        run_sql_file(f)


@app.command()
def ingest(date: list[str] = typer.Option(..., "--date", help="Date(s) de dépôt AAAA-MM-JJ")):
    """Récupère les fichiers du filestorage vers le lake (pseudonymisé, incrémental)."""
    for d in date:
        with track("ingest", layer="lake", business_date=d):
            copied = ingest_date(d)
            log.info("%s : %s", d, copied or "rien de nouveau")


@app.command()
def transform(
    layer: str = typer.Option("", "--layer", help="bronze|clean|silver|gold (défaut: toutes)"),
):
    """Rejoue les transformations SQL du médaillon dans ClickHouse."""
    with track("transform", layer=layer or "all"):
        run_layer(layer) if layer else run_all()


@app.command()
def replay(date: str = typer.Option(..., "--date", help="Date à rejouer AAAA-MM-JJ")):
    """Reprise sur incident : ré-ingère une date puis rejoue les transformations."""
    with track("replay", business_date=date):
        ingest_date(date)
        run_all()


@app.command()
def verify():
    """Contrôles de fiabilité (réconciliation KPI ↔ sources, k-anonymat, cohérence). Sort ≠ 0 si échec."""
    from pipeline.verify import verify as _verify

    with track("verify"):
        _verify()


@app.command(name="run-daily")
def run_daily(date: str = typer.Option("", "--date", help="Défaut : aujourd'hui (AAAA-MM-JJ)")):
    """Traitement quotidien complet (ingest + transforme + vérifie) dans un seul run tracé."""
    from pipeline.verify import verify as _verify

    day = date or datetime.now(UTC).strftime("%Y-%m-%d")
    with track("run-daily", business_date=day):
        ingest_date(day)
        run_all()
        _verify()
    log.info("run-daily %s : terminé", day)


@app.command()
def status(limit: int = 15):
    """Historique des exécutions (meta.runs)."""
    rows = query(
        f"SELECT started_at, action, layer, business_date, status, error "
        f"FROM meta.runs ORDER BY started_at DESC LIMIT {limit}"
    )
    for r in rows:
        typer.echo("  ".join(str(x) for x in r))


@app.command()
def dashboards(
    export: bool = typer.Option(
        True, "--export/--no-export", help="Exporter les dashboards en JSON"
    ),
):
    """Provisionne Metabase : connexions, groupes, permissions, 2 dashboards (idempotent)."""
    from pipeline.metabase import provision

    provision(export=export)


if __name__ == "__main__":
    app()
