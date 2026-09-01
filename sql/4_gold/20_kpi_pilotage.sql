-- Gold — indicateurs PILOTAGE hospitalier (vues : recalculées à la lecture).
-- SQL SECURITY DEFINER : ro_pilotage n'a besoin d'un GRANT que sur ces vues.

-- 1. Durée Moyenne de Séjour (DMS) par service — séjours clos uniquement
CREATE OR REPLACE VIEW gold.kpi_pilotage_dms
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    f.service_code             AS service_code,
    s.service_label            AS service_label,
    count()                    AS nb_sejours_clos,
    round(avg(f.los_days), 2)  AS dms_jours
FROM gold.fact_sejour f
LEFT JOIN gold.dim_service s ON s.service_code = f.service_code
WHERE f.is_closed = 1 AND f.los_days IS NOT NULL
GROUP BY service_code, service_label
ORDER BY dms_jours DESC;

-- 2. Activité des urgences : passages par jour
CREATE OR REPLACE VIEW gold.kpi_pilotage_urgences_jour
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    admission_date               AS jour,
    countIf(is_urgence = 1)      AS passages_urgence,
    count()                      AS admissions_totales
FROM gold.fact_sejour
GROUP BY jour
ORDER BY jour;

-- 3. Taux de réadmission à 30 jours (qualité des soins)
--    Réadmission = nouvelle admission du même patient <= 30 j après une sortie.
CREATE OR REPLACE VIEW gold.kpi_pilotage_readmission_30j
DEFINER = eds SQL SECURITY DEFINER
AS
WITH sejours_ordonnes AS (
    SELECT
        patient_hash, admission_ts, discharge_ts,
        leadInFrame(admission_ts) OVER (
            PARTITION BY patient_hash ORDER BY admission_ts
            ROWS BETWEEN CURRENT ROW AND 1 FOLLOWING
        ) AS prochaine_admission
    FROM gold.fact_sejour
    WHERE is_closed = 1
)
SELECT
    count()                                                                   AS sorties,
    countIf(prochaine_admission IS NOT NULL
            AND dateDiff('day', discharge_ts, prochaine_admission) BETWEEN 0 AND 30) AS readmissions_30j,
    round(100 * readmissions_30j / sorties, 2)                                AS taux_pct
FROM sejours_ordonnes;

-- 4. Surveillance des constantes : relevés en alerte par jour
--    Bornes d'ALERTE clinique (≠ plausibilité physiologique du silver) :
--    FC <40 ou >120 · SpO2 <92 · temp >38.5 ou <35
CREATE OR REPLACE VIEW gold.kpi_pilotage_alertes_constantes
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    toDate(ts)                                                              AS jour,
    countIf(heart_rate < 40 OR heart_rate > 120)                            AS alertes_fc,
    countIf(spo2 < 92)                                                      AS alertes_spo2,
    countIf(temp_c < 35 OR temp_c > 38.5)                                   AS alertes_temp,
    count()                                                                 AS releves_total
FROM silver.monitoring
GROUP BY jour
ORDER BY jour;
