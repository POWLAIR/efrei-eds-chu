"""Point d'entrée `eds` (Typer) — mappe les sous-commandes (ingest, transform,
verify, run-daily, replay, status, dashboards) sur les étapes de `pipeline/steps/`.
Aucune logique métier ici.  `uv run eds --help`
"""

from __future__ import annotations

from datetime import UTC, datetime

import typer

from pipeline.clickhouse import query, run_sql_file
from pipeline.observabilite import get_logger, track

# verify / dashboards : import paresseux dans leur commande (garde `eds --help` léger)
from pipeline.steps import lake, medallion

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
            copied = lake.ingest_date(d)
            log.info("%s : %s", d, copied or "rien de nouveau")


@app.command()
def transform(
    layer: str = typer.Option("", "--layer", help="bronze|clean|silver|gold (défaut: toutes)"),
):
    """Rejoue les transformations SQL du médaillon dans ClickHouse."""
    if layer and layer not in medallion.LAYERS:
        raise typer.BadParameter(f"couche inconnue : {layer!r}", param_hint="--layer")
    with track("transform", layer=layer or "all"):
        medallion.run_layer(layer) if layer else medallion.run_all()


@app.command()
def replay(date: str = typer.Option(..., "--date", help="Date à rejouer AAAA-MM-JJ")):
    """Reprise sur incident : ré-ingère une date puis rejoue les transformations."""
    with track("replay", business_date=date):
        lake.ingest_date(date)
        medallion.run_all()


@app.command()
def verify():
    """Contrôles de fiabilité (réconciliation KPI ↔ sources, k-anonymat, cohérence). Sort ≠ 0 si échec."""
    from pipeline.steps import verify as verify_step

    with track("verify"):
        verify_step.verify()


@app.command(name="run-daily")
def run_daily(date: str = typer.Option("", "--date", help="Défaut : aujourd'hui (AAAA-MM-JJ)")):
    """Traitement quotidien complet (ingest + transforme + vérifie) dans un seul run tracé."""
    from pipeline.steps import verify as verify_step

    day = date or datetime.now(UTC).strftime("%Y-%m-%d")
    with track("run-daily", business_date=day):
        lake.ingest_date(day)
        medallion.run_all()
        verify_step.verify()
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
def dashboards():
    """Provisionne Metabase : connexions, groupes, permissions, 2 dashboards (idempotent)."""
    from pipeline.steps import dashboards as dashboards_step

    dashboards_step.provision()


if __name__ == "__main__":
    app()
