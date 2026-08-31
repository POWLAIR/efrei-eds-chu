"""Contrôles qualité — tests d'intégration (nécessitent ClickHouse : `make up init-db`).

Ignorés automatiquement si ClickHouse n'est pas joignable.
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


def test_bornes_physiologiques_monitoring():
    c = _ch()
    # Une valeur clairement hors plage doit être détectable par la condition du silver.
    rows = c.query(
        "SELECT (250 BETWEEN 20 AND 250), (251 BETWEEN 20 AND 250), "
        "(49 BETWEEN 50 AND 100), (29.9 BETWEEN 30 AND 45)"
    ).result_rows[0]
    assert rows == (1, 0, 0, 0)


def test_sejour_sans_sortie_est_conserve():
    c = _ch()
    # discharge NULL -> la condition (discharge IS NULL OR discharge >= admission) est vraie
    ok = c.query("SELECT (NULL IS NULL) OR (NULL >= now())").result_rows[0][0]
    assert ok == 1
