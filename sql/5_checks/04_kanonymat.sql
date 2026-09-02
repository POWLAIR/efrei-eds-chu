-- OK si 0 ligne : aucune cohorte de recherche diffusée avec moins de 5 patients (RGPD)
SELECT 'prevalence' AS vue, code_cim10 AS cle, nb_patients AS n
FROM gold.kpi_recherche_prevalence WHERE nb_patients < 5
UNION ALL
SELECT 'cohorte_age_sexe' AS vue, concat(code_cim10, '/', tranche_age, '/', sexe) AS cle, nb_patients AS n
FROM gold.kpi_recherche_cohorte_age_sexe WHERE nb_patients < 5;
