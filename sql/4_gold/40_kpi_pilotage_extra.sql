-- Gold — indicateurs PILOTAGE complémentaires (« toute autre vue d'activité pertinente »).
-- Vues SQL SECURITY DEFINER : accès via GRANT sur la vue uniquement.

-- 5. Répartition des modes de sortie (qualité / devenir des patients, séjours clos)
CREATE OR REPLACE VIEW gold.kpi_pilotage_mode_sortie
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    discharge_mode                                       AS mode_sortie,
    count()                                              AS nb_sejours,
    round(100 * count() / sum(count()) OVER (), 1)       AS part_pct
FROM gold.fact_sejour
WHERE is_closed = 1
GROUP BY mode_sortie
ORDER BY nb_sejours DESC;

-- 6. Charge par service : admissions, séjours en cours, patients-jours cumulés
CREATE OR REPLACE VIEW gold.kpi_pilotage_charge_service
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    f.service_code                          AS service_code,
    s.service_label                         AS service_label,
    count()                                 AS admissions,
    countIf(f.is_closed = 0)                AS sejours_en_cours,
    round(sum(f.los_days), 0)               AS patients_jours
FROM gold.fact_sejour f
LEFT JOIN gold.dim_service s ON s.service_code = f.service_code
GROUP BY service_code, service_label
ORDER BY admissions DESC;
