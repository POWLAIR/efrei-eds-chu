# 02 · Besoins métier & définition des indicateurs

Chaque chiffre doit être **fiable, cohérent avec les sources, et justifiable**.
Table de fait centrale : `gold.fact_sejour` (1 ligne = 1 séjour valide).

## Pilotage hospitalier

| KPI | Vue Gold | Définition de calcul |
|---|---|---|
| **DMS par service** | `kpi_pilotage_dms` | moyenne de `(discharge_ts - admission_ts)` en jours, **séjours clos uniquement**, `GROUP BY service_code` |
| **Activité des urgences / jour** | `kpi_pilotage_urgences_jour` | nb de séjours avec `admission_mode = 'urgence'`, `GROUP BY toDate(admission_ts)` |
| **Taux de réadmission à 30 j** | `kpi_pilotage_readmission_30j` | part des sorties suivies d'une **nouvelle admission du même `patient_hash` ≤ 30 jours** après la sortie |
| **Relevés de constantes en alerte / jour** | `kpi_pilotage_alertes_constantes` | nb de relevés `silver.monitoring` franchissant une **borne d'alerte clinique** (FC <40 ou >120 · SpO2 <92 · temp <35 ou >38.5), `GROUP BY jour` |
| *Toute autre vue d'activité pertinente* | — | ex. taux d'occupation, mode de sortie `deces` par service… |

> ⚠️ **Bornes d'alerte ≠ bornes de plausibilité.** Le silver écarte l'impossible
> (FC 20–250, SpO2 50–100, temp 30–45). Le gold compte l'anormal *plausible*.

## Recherche clinique

| KPI | Vue Gold | Définition |
|---|---|---|
| **Prévalence par pathologie** | `kpi_recherche_prevalence` | `uniqExact(patient_hash)` par `code_cim10` **principal**, `HAVING cohorte ≥ 5` |
| **Description de cohorte (âge × sexe)** | `kpi_recherche_cohorte_age_sexe` | nb de patients par `age_band` × `sex`, `HAVING nb ≥ 5` |

Âge calculé sur `birth_year` uniquement (minimisation). Tranches : `0-17 / 18-39 / 40-64 / 65-79 / 80+ / inconnu`.

## Modélisation (rappel théorie — schéma en étoile)

- **Fait** = événement mesurable qu'on agrège → `fact_sejour` (mesure : `los_days`, comptages).
- **Dimension** = axe d'analyse (le « par… ») → `dim_service`, `dim_cim10`, `dim_patient`, la date.
- **Référentiel** = dimension `code → libellé` → `services`, `cim10`.
- Règle : dans « KPI par X », X est une dimension ; le KPI sort du fait. On ne crée jamais un « fact_patient ».
