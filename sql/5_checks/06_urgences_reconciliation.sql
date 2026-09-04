-- OK si 0 ligne : le total des passages du KPI urgences = le compte sur le fait
-- (séjours du service URGENCES).
SELECT
    (SELECT sum(nb_passages) FROM gold.kpi_pilotage_urgences_jour)          AS kpi_total,
    (SELECT countIf(service_code = 'URGENCES') FROM gold.fact_sejour)       AS fait_total
WHERE kpi_total != fait_total;
