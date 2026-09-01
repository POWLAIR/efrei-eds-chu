-- Gold — indicateurs RECHERCHE clinique.
-- RGPD petits effectifs : toute cohorte de moins de 5 patients est masquée
-- directement dans la vue (le user ro_recherche n'a accès qu'à ces vues).

-- Les vues sont en SQL SECURITY DEFINER : ro_recherche n'a besoin d'un GRANT que
-- sur la vue, pas sur les tables sous-jacentes (fact_sejour contient le patient_hash).

-- 1. Prévalence par pathologie : taille des cohortes par diagnostic principal
CREATE OR REPLACE VIEW gold.kpi_recherche_prevalence
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    d.code_cim10                AS code_cim10,
    c.libelle                   AS libelle,
    uniqExact(f.patient_hash)   AS cohorte_patients
FROM gold.fact_sejour f
INNER JOIN silver.diagnostics d ON d.stay_id = f.stay_id AND d.type = 'principal'
LEFT JOIN gold.dim_cim10 c ON c.code_cim10 = d.code_cim10
GROUP BY code_cim10, libelle
HAVING cohorte_patients >= 5           -- k-anonymat
ORDER BY cohorte_patients DESC;

-- 2. Description de cohorte : distribution par tranche d'âge et sexe
CREATE OR REPLACE VIEW gold.kpi_recherche_cohorte_age_sexe
DEFINER = eds SQL SECURITY DEFINER
AS
SELECT
    p.age_band  AS age_band,
    p.sex       AS sex,
    count()     AS nb_patients
FROM gold.dim_patient p
WHERE p.patient_hash IN (SELECT DISTINCT patient_hash FROM gold.fact_sejour)
GROUP BY age_band, sex
HAVING nb_patients >= 5                -- k-anonymat
ORDER BY age_band, sex;
