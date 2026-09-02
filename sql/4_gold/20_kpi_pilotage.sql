-- Gold — indicateurs PILOTAGE hospitalier (vues : recalculées à la lecture).
-- SQL SECURITY DEFINER : ro_pilotage n'a besoin d'un GRANT que sur ces vues.
-- Définitions alignées sur la feuille de réponses officielle des KPI (corrigé niveau 1).

-- 1. Durée Moyenne de Séjour (DMS) par service — séjours clos uniquement
CREATE OR REPLACE VIEW gold.kpi_pilotage_dms
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    f.service_code                    AS service_code,
    s.service_label                   AS service_label,
    count()                           AS nb_sejours,
    round(avg(f.los_hours) / 24, 2)   AS dms_jours,
    round(avg(f.los_hours), 1)        AS dms_heures
FROM gold.fact_sejour f
LEFT JOIN gold.dim_service s ON s.service_code = f.service_code
WHERE f.is_closed = 1 AND f.los_hours IS NOT NULL
GROUP BY service_code, service_label
ORDER BY dms_jours DESC;

-- 2. Activité du service des URGENCES par jour d'admission
--    Périmètre = séjours dont le service est 'URGENCES' (le passage aux urgences
--    en tant que tel), et non le mode d'admission 'urgence' (qui concerne aussi
--    les admissions urgentes vers CARDIO, REA…). Cf. feuille de réponses officielle.
--    nb_passages         : séjours entrés aux urgences ce jour-là
--    nb_encore_presents  : parmi eux, ceux sans date de sortie (toujours présents)
--    duree_moy_heures    : durée moyenne (séjours clos uniquement)
CREATE OR REPLACE VIEW gold.kpi_pilotage_urgences_jour
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    admission_date                                        AS admission_date,
    count()                                               AS nb_passages,
    countIf(discharge_ts IS NULL)                         AS nb_encore_presents,
    round(avgIf(los_hours, discharge_ts IS NOT NULL), 1)  AS duree_moy_heures
FROM gold.fact_sejour
WHERE service_code = 'URGENCES'
GROUP BY admission_date
ORDER BY admission_date;

-- 3. Taux de réadmission à 30 jours (qualité des soins)
--    Réadmission = un séjour clos suivi d'une NOUVELLE admission du même patient
--    (close ou en cours) <= 30 j après sa sortie.
--    Dénominateur = tous les séjours valides (= count(silver.sejours)).
CREATE OR REPLACE VIEW gold.kpi_pilotage_readmission_30j
DEFINER = eds SQL SECURITY DEFINER
AS
WITH sejours_ordonnes AS (
    SELECT
        patient_hash, discharge_ts,
        leadInFrame(admission_ts) OVER (
            PARTITION BY patient_hash ORDER BY admission_ts
            ROWS BETWEEN CURRENT ROW AND 1 FOLLOWING
        ) AS prochaine_admission
    FROM gold.fact_sejour
)
SELECT
    countIf(discharge_ts IS NOT NULL
            AND prochaine_admission IS NOT NULL
            AND dateDiff('day', discharge_ts, prochaine_admission) BETWEEN 0 AND 30) AS nb_readmissions_30j,
    (SELECT count() FROM gold.fact_sejour)                                           AS nb_sejours,
    round(100 * nb_readmissions_30j / nb_sejours, 2)                                 AS taux_readmission_30j_pct
FROM sejours_ordonnes;

-- 4. Surveillance des constantes : relevés en alerte par jour
--    Bornes d'ALERTE clinique (≠ plausibilité physiologique du silver) :
--    SpO2 < 92 · FC < 50 ou > 100 · T° > 38.5
--    Un relevé est « en alerte » dès qu'au moins un seuil est franchi.
CREATE OR REPLACE VIEW gold.kpi_pilotage_alertes_constantes
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    toDate(ts)                                                                    AS jour,
    count()                                                                       AS nb_releves,
    countIf(spo2 < 92 OR heart_rate < 50 OR heart_rate > 100 OR temp_c > 38.5)    AS nb_alertes,
    round(100 * nb_alertes / nb_releves, 1)                                       AS taux_alertes_pct
FROM silver.monitoring
GROUP BY jour
ORDER BY jour;
