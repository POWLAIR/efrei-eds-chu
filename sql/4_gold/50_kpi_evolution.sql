-- Gold — indicateurs liés à l'ÉVOLUTION (description des services + actes / T2A).
-- Vues SQL SECURITY DEFINER : accès via GRANT sur la vue uniquement (role_pilotage).
-- Aucune vue ne relie fact_acte ↔ fact_sejour : le service de l'acte est déjà
-- porté par fact_acte (résolu dans silver.actes via le séjour).

-- E1. Activité et DMS par CATÉGORIE de service
CREATE OR REPLACE VIEW gold.kpi_pilotage_activite_categorie
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    sv.categorie                                        AS categorie,
    count()                                             AS nb_sejours,
    countIf(f.is_closed = 1)                            AS nb_sejours_clos,
    round(avgIf(f.los_hours, f.is_closed = 1) / 24, 2)  AS dms_jours
FROM gold.fact_sejour f
LEFT JOIN gold.dim_service sv ON sv.service_code = f.service_code
GROUP BY categorie
ORDER BY nb_sejours DESC;

-- E2. Nombre d'actes par service + nombre moyen d'actes par séjour
CREATE OR REPLACE VIEW gold.kpi_pilotage_actes_service
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    a.service_code                          AS service_code,
    any(sv.service_label)                   AS service_label,
    count()                                 AS nb_actes,
    any(sc.nb_sejours)                      AS nb_sejours,
    round(count() / any(sc.nb_sejours), 2)  AS actes_par_sejour
FROM gold.fact_acte a
LEFT JOIN gold.dim_service sv ON sv.service_code = a.service_code
LEFT JOIN (
    SELECT service_code, count() AS nb_sejours
    FROM gold.fact_sejour GROUP BY service_code
) sc ON sc.service_code = a.service_code
GROUP BY service_code
ORDER BY nb_actes DESC;

-- E3. Répartition des actes par type d'acte (les plus fréquents)
CREATE OR REPLACE VIEW gold.kpi_pilotage_actes_type
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    a.code_ccam                                     AS code_ccam,
    any(c.libelle)                                  AS libelle,
    count()                                         AS nb_actes,
    round(100 * count() / sum(count()) OVER (), 1)  AS part_pct
FROM gold.fact_acte a
LEFT JOIN gold.dim_ccam c ON c.code_ccam = a.code_ccam
GROUP BY code_ccam
ORDER BY nb_actes DESC;

-- E4. Densité d'actes par lit (intensité du plateau technique)
--     capacite_lits NULL pour un service non décrit → actes_par_lit NULL (assumé).
CREATE OR REPLACE VIEW gold.kpi_pilotage_densite_actes_lit
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    a.service_code                             AS service_code,
    any(sv.service_label)                      AS service_label,
    any(sv.capacite_lits)                      AS capacite_lits,
    count()                                    AS nb_actes,
    round(count() / any(sv.capacite_lits), 1)  AS actes_par_lit
FROM gold.fact_acte a
LEFT JOIN gold.dim_service sv ON sv.service_code = a.service_code
GROUP BY service_code
ORDER BY actes_par_lit DESC NULLS LAST;

-- E5. Montant facturé par service (T2A) — somme des tarifs des actes réalisés
CREATE OR REPLACE VIEW gold.kpi_pilotage_montant_t2a
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    a.service_code                 AS service_code,
    any(sv.service_label)          AS service_label,
    count()                        AS nb_actes,
    sum(a.tarif_euros)             AS montant_total_euros,
    round(avg(a.tarif_euros), 2)   AS tarif_moyen_euros
FROM gold.fact_acte a
LEFT JOIN gold.dim_service sv ON sv.service_code = a.service_code
GROUP BY service_code
ORDER BY montant_total_euros DESC;
