-- Gold — indicateurs RECHERCHE clinique.
-- RGPD petits effectifs : toute cohorte de moins de 5 patients est masquée
-- directement dans la vue (le user ro_recherche n'a accès qu'à ces vues).
-- Définitions alignées sur la feuille de réponses officielle des KPI (corrigé niveau 1).

-- Les vues sont en SQL SECURITY DEFINER : ro_recherche n'a besoin d'un GRANT que
-- sur la vue, pas sur les tables sous-jacentes.
-- Source : silver.diagnostics (porte patient_hash, conserve les diagnostics des
-- séjours écartés pour incohérence temporelle — cf. 3_silver/40_diagnostics.sql).

-- 1. Prévalence par pathologie : nb de patients distincts porteurs du code CIM-10,
--    tous diagnostics confondus (principal + associé) — une prévalence
--    épidémiologique compte tout patient porteur, pas seulement en principal.
CREATE OR REPLACE VIEW gold.kpi_recherche_prevalence
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    d.code_cim10                AS code_cim10,
    c.libelle                   AS libelle_cim10,
    uniqExact(d.patient_hash)   AS nb_patients
FROM silver.diagnostics d
LEFT JOIN gold.dim_cim10 c ON c.code_cim10 = d.code_cim10
GROUP BY code_cim10, libelle_cim10
HAVING nb_patients >= 5           -- k-anonymat : cohortes < 5 non diffusées
ORDER BY nb_patients DESC;

-- 2. Description de cohorte : patients distincts par pathologie principale
--    × tranche d'âge × sexe.
CREATE OR REPLACE VIEW gold.kpi_recherche_cohorte_age_sexe
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    d.code_cim10               AS code_cim10,
    p.age_band                 AS tranche_age,
    p.sex                      AS sexe,
    uniqExact(d.patient_hash)  AS nb_patients
FROM silver.diagnostics d
INNER JOIN gold.dim_patient p ON p.patient_hash = d.patient_hash
WHERE d.type = 'principal'
GROUP BY code_cim10, tranche_age, sexe
HAVING nb_patients >= 5                -- k-anonymat
ORDER BY code_cim10, tranche_age, sexe;
