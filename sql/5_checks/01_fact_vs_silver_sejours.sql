-- OK si 0 ligne : gold.fact_sejour a exactement autant de lignes que silver.sejours
SELECT
    (SELECT count() FROM gold.fact_sejour) AS fact,
    (SELECT count() FROM silver.sejours)   AS silver_sejours
WHERE fact != silver_sejours;
