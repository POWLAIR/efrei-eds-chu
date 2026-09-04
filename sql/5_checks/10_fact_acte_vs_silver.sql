-- OK si 0 ligne : le fait actes conserve exactement les lignes de silver.actes
SELECT
    (SELECT count() FROM gold.fact_acte) AS fact_acte,
    (SELECT count() FROM silver.actes)   AS silver_actes
WHERE fact_acte != silver_actes;
