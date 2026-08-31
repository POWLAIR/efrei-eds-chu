-- OK si 0 ligne : le total des passages urgences du KPI = le compte sur le fait
SELECT
    (SELECT sum(passages_urgence) FROM gold.kpi_pilotage_urgences_jour) AS kpi_total,
    (SELECT countIf(is_urgence = 1) FROM gold.fact_sejour)              AS fait_total
WHERE kpi_total != fait_total;
