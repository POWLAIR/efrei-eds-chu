-- OK si 0 ligne : les KPI niveau 1 reproduisent la feuille de réponses officielle
-- (« corrigé niveau 1 », jeu figé seed 42). Comptages = exacts ;
-- moyennes = tolérance ±0.1 j (arrondi, implémentation de dateDiff).
SELECT 'readmission_30j_numerateur' AS repere, toString(nb_readmissions_30j) AS obtenu, '780' AS attendu
FROM gold.kpi_pilotage_readmission_30j WHERE nb_readmissions_30j != 780
UNION ALL
SELECT 'readmission_30j_denominateur', toString(nb_sejours), '6729'
FROM gold.kpi_pilotage_readmission_30j WHERE nb_sejours != 6729
UNION ALL
SELECT 'prevalence_N39', toString(nb_patients), '2234'
FROM gold.kpi_recherche_prevalence WHERE code_cim10 = 'N39' AND nb_patients != 2234
UNION ALL
SELECT 'prevalence_I50', toString(nb_patients), '2156'
FROM gold.kpi_recherche_prevalence WHERE code_cim10 = 'I50' AND nb_patients != 2156
UNION ALL
SELECT 'prevalence_E11', toString(nb_patients), '2177'
FROM gold.kpi_recherche_prevalence WHERE code_cim10 = 'E11' AND nb_patients != 2177
UNION ALL
SELECT 'dms_REA_nb_sejours', toString(nb_sejours), '423'
FROM gold.kpi_pilotage_dms WHERE service_code = 'REA' AND nb_sejours != 423
UNION ALL
SELECT 'dms_REA_jours', toString(dms_jours), '9.05 (+/-0.1)'
FROM gold.kpi_pilotage_dms WHERE service_code = 'REA' AND abs(dms_jours - 9.05) > 0.1
UNION ALL
SELECT 'dms_NEURO_jours', toString(dms_jours), '7.06 (+/-0.1)'
FROM gold.kpi_pilotage_dms WHERE service_code = 'NEURO' AND abs(dms_jours - 7.06) > 0.1
UNION ALL
SELECT 'alertes_2026_08_01', toString(nb_alertes), '25'
FROM gold.kpi_pilotage_alertes_constantes WHERE jour = '2026-08-01' AND nb_alertes != 25
UNION ALL
SELECT 'releves_2026_08_01', toString(nb_releves), '351'
FROM gold.kpi_pilotage_alertes_constantes WHERE jour = '2026-08-01' AND nb_releves != 351
UNION ALL
SELECT 'urgences_2026_08_01_passages', toString(nb_passages), '46'
FROM gold.kpi_pilotage_urgences_jour WHERE admission_date = '2026-08-01' AND nb_passages != 46;
