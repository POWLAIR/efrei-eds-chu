"""Tests d'intégration du pipeline — nécessitent ClickHouse peuplé (`make all`).

Ces tests utilisent le `.env` réel (même sel de pseudonymisation que le pipeline)
et ne modifient jamais le lake. Ignorés si ClickHouse n'est pas joignable ou vide.
"""

import pytest


def _ch():
    try:
        from pipeline.clickhouse import client

        c = client()
        c.command("SELECT 1")
        return c
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"ClickHouse indisponible: {exc}")


def _count(c, table: str) -> int:
    return c.query(f"SELECT count() FROM {table}").result_rows[0][0]


def test_transform_idempotent():
    """Rejouer bronze->clean->silver->gold ne change aucun compte (rebuild complet)."""
    c = _ch()
    if _count(c, "silver.sejours") == 0:
        pytest.skip("pipeline non exécuté — lancer `make all`")

    from pipeline.transform import run_all

    tables = ("silver.sejours", "silver.patients", "silver.monitoring",
              "silver.pathologies", "gold.fact_sejour", "clean.rejects")
    before = {t: _count(c, t) for t in tables}
    run_all()
    after = {t: _count(c, t) for t in tables}
    assert before == after


def test_ingest_incremental_deja_connu():
    """Le dépôt du 26/08 est intégralement connu de meta.ingested_files (aucune ré-ingestion)."""
    c = _ch()
    from pipeline.config import SOURCES, settings

    known = c.query(
        "SELECT count() FROM meta.ingested_files WHERE business_date = '2026-08-26'"
    ).result_rows[0][0]
    if not known:
        pytest.skip("date non ingérée — lancer `make ingest`")

    day_dir = settings.source_filestorage
    on_disk = sum(
        1
        for s in SOURCES
        for f in sorted((day_dir / s / "2026-08-26").glob("*"))
        if f.is_file()
    )
    assert known == on_disk


def test_verify_passe_sur_jeu_fourni():
    """Les 8 contrôles de réconciliation passent sur le jeu de données fourni."""
    c = _ch()
    if _count(c, "gold.fact_sejour") == 0:
        pytest.skip("pipeline non exécuté — lancer `make all`")

    from pipeline.verify import run_checks

    failed = [name for name, n in run_checks() if n]
    assert not failed, f"contrôles en échec : {failed}"


def test_pathologies_couvre_diagnostics():
    """silver.pathologies contient tout code_cim10 observé dans silver.diagnostics."""
    c = _ch()
    if _count(c, "silver.diagnostics") == 0:
        pytest.skip("pipeline non exécuté — lancer `make all`")
    orphelins = _count(
        c,
        "silver.diagnostics d "
        "LEFT ANTI JOIN silver.pathologies p ON p.code_cim10 = d.code_cim10",
    )
    assert orphelins == 0


def test_kanonymat_vues_recherche():
    """Aucune cohorte de moins de 5 patients n'est exposée."""
    c = _ch()
    if _count(c, "gold.fact_sejour") == 0:
        pytest.skip("pipeline non exécuté")
    assert _count(c, "gold.kpi_recherche_prevalence WHERE cohorte_patients < 5") == 0
    assert _count(c, "gold.kpi_recherche_cohorte_age_sexe WHERE nb_patients < 5") == 0
