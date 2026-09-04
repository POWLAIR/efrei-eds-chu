# 02 · Besoins métier & définition des indicateurs

Chaque chiffre doit être **fiable, cohérent avec les sources, et justifiable**.
Table de fait centrale : `gold.fact_sejour` (1 ligne = 1 séjour valide).

## Pilotage hospitalier

| KPI | Vue Gold | Définition de calcul |
|---|---|---|
| **DMS par service** | `kpi_pilotage_dms` | moyenne de `(discharge_ts - admission_ts)` en jours (et en heures), **séjours clos uniquement**, `GROUP BY service_code` |
| **Activité des urgences / jour** | `kpi_pilotage_urgences_jour` | nb de séjours du **service `URGENCES`** par date d'admission (+ `nb_encore_presents`, `duree_moy_heures`). ⚠️ le *service* URGENCES, pas le *mode* d'admission `urgence` (qui alimente aussi CARDIO, REA…) |
| **Taux de réadmission à 30 j** | `kpi_pilotage_readmission_30j` | séjours clos suivis d'une **nouvelle admission du même `patient_hash` ≤ 30 jours** après la sortie ; **dénominateur = tous les séjours valides** (`count(silver.sejours)`) |
| **Relevés de constantes en alerte / jour** | `kpi_pilotage_alertes_constantes` | nb de relevés `silver.monitoring` franchissant une **borne d'alerte clinique** (**SpO2 < 92 · FC < 50 ou > 100 · T° > 38.5**, au moins un seuil), `GROUP BY jour` |
| *Toute autre vue d'activité pertinente* | — | ex. taux d'occupation, mode de sortie `deces` par service… |

> ⚠️ **Bornes d'alerte ≠ bornes de plausibilité.** Le silver écarte l'impossible
> (FC 20–250, SpO2 50–100, temp 30–45). Le gold compte l'anormal *plausible*.
> Les seuils d'alerte ci-dessus sont ceux de la **feuille de réponses officielle**
> (cf. `09-corrige-niveau1-comparatif.md`).

## Recherche clinique

| KPI | Vue Gold | Définition |
|---|---|---|
| **Prévalence par pathologie** | `kpi_recherche_prevalence` | `uniqExact(patient_hash)` par `code_cim10`, **tous diagnostics** (principal + associé — prévalence épidémiologique), `HAVING cohorte ≥ 5` |
| **Description de cohorte** | `kpi_recherche_cohorte_age_sexe` | `uniqExact(patient_hash)` par `code_cim10` **principal** × tranche d'âge × `sex`, `HAVING nb ≥ 5` |

Âge calculé sur `birth_year` uniquement (minimisation), année de référence figée à l'année
du dernier séjour observé (jeu « data figée »). Tranches **décennales** :
`0-9 / 10-19 / … / 90-99 / 100+ / inconnu` (feuille de réponses officielle).

## Modélisation (rappel théorie — schéma en étoile)

- **Fait** = événement mesurable qu'on agrège → `fact_sejour` (mesure : `los_days`, comptages).
- **Dimension** = axe d'analyse (le « par… ») → `dim_service`, `dim_cim10`, `dim_patient`, la date.
- **Référentiel** = dimension `code → libellé` → `services`, `cim10`.
- Règle : dans « KPI par X », X est une dimension ; le KPI sort du fait. On ne crée jamais un « fact_patient ».
