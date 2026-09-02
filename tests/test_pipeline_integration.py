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

    from pipeline.steps import medallion

    tables = ("silver.sejours", "silver.patients", "silver.monitoring",
              "silver.pathologies", "gold.fact_sejour", "clean.rejects")
    before = {t: _count(c, t) for t in tables}
    medallion.run_all()
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
    """Les 12 contrôles de réconciliation passent sur le jeu de données fourni."""
    c = _ch()
    if _count(c, "gold.fact_sejour") == 0:
        pytest.skip("pipeline non exécuté — lancer `make all`")

    from pipeline.steps import verify

    failed = [name for name, n in verify.run_checks() if n]
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
    assert _count(c, "gold.kpi_recherche_prevalence WHERE nb_patients < 5") == 0
    assert _count(c, "gold.kpi_recherche_cohorte_age_sexe WHERE nb_patients < 5") == 0


def test_corrige_niveau1_repere_prevalence():
    """La prévalence reproduit la feuille de réponses officielle (tous diagnostics)."""
    c = _ch()
    if _count(c, "silver.diagnostics") == 0:
        pytest.skip("pipeline non exécuté")
    n39 = c.query(
        "SELECT nb_patients FROM gold.kpi_recherche_prevalence WHERE code_cim10 = 'N39'"
    ).result_rows[0][0]
    assert n39 == 2234


# --- Évolution : actes médicaux + description des services --------------------


def test_fact_acte_conserve_silver_actes():
    """gold.fact_acte conserve exactement silver.actes (> 0)."""
    c = _ch()
    n = _count(c, "silver.actes")
    if n == 0:
        pytest.skip("évolution non ingérée — lancer `make ingest`")
    assert _count(c, "gold.fact_acte") == n


def test_service_non_decrit_conserve():
    """Un service absent de description_service.csv est conservé, marqué non décrit."""
    c = _ch()
    if _count(c, "silver.services") == 0:
        pytest.skip("évolution non ingérée")
    row = c.query(
        "SELECT is_described, categorie, capacite_lits FROM silver.services "
        "WHERE service_code = 'NEURO'"
    ).result_rows[0]
    assert row[0] == 0 and row[1] == "(non décrit)" and row[2] is None


def test_acte_service_vient_du_sejour():
    """Le service d'un acte = le service de son séjour (jamais porté par l'acte)."""
    c = _ch()
    if _count(c, "gold.fact_acte") == 0:
        pytest.skip("évolution non ingérée")
    incoherents = _count(
        c,
        "gold.fact_acte a INNER JOIN gold.fact_sejour f ON f.stay_id = a.stay_id "
        "WHERE a.service_code != f.service_code",
    )
    assert incoherents == 0


def test_non_regression_fact_sejour():
    """L'évolution ne change pas le fait central : toujours 6 729 séjours."""
    c = _ch()
    if _count(c, "gold.fact_sejour") == 0:
        pytest.skip("pipeline non exécuté")
    assert _count(c, "gold.fact_sejour") == 6729
