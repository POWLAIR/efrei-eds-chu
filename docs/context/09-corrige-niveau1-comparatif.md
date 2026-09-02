# 09 · Corrigé niveau 1 — comparatif avant / après

> Source : `docs/REPONSES-KPI-niveau1.pdf` — *feuille de réponses officielle* des KPI
> (« corrigé niveau 1 », jeu figé **seed 42**, mention « NE PAS DISTRIBUER · usage
> intervenant »). Reçue après la finalisation de la Partie 1.

## Ce que la feuille confirme

Les **points de contrôle silver** de la feuille sont **identiques aux nôtres** — notre jeu
`data/source-filestorage/` **est** le jeu corrigé :

| Table | Bronze | Silver | Écart |
|---|---|---|---|
| `dim_patient` | 18 000 | 6 000 | 12 000 doublons de snapshots |
| `fact_sejour` | 6 797 | 6 729 | 68 (`discharge_ts < admission_ts`) |
| `fact_monitoring` | 41 778 | 40 920 | 858 (capteurs hors plage physiologique) |

## Ce que la feuille corrige — définitions des KPI

La feuille révèle que **plusieurs définitions attendues diffèrent** de notre implémentation
initiale. La Partie 1 a été **réalignée** (code + doc). Tolérance de la feuille : comptages
**exacts**, moyennes **± 0,1** (arrondi, implémentation de `dateDiff`).

| KPI | Définition initiale | Valeur initiale | Définition corrigée (feuille) | Valeur corrigée | Cause de l'écart |
|---|---|---|---|---|---|
| **Réadmission 30 j** | dénominateur = séjours **clos** (6 046) ; prochaine admission **close** uniquement | 10,54 % (637 / 6 046) | dénominateur = **tous** les séjours valides (6 729) ; prochaine admission **quelconque** (close ou en cours) | **11,59 % (780 / 6 729)** | mauvais dénominateur + on ratait les réadmissions vers un séjour encore ouvert |
| **Activité urgences / jour** | `admission_mode = 'urgence'` (tous services) | ≈ 119 / jour | séjours du **service `URGENCES`** par date d'admission | **1 423 sur 28 j** (≈ 51 / jour) ; 2026-08-01 = 46 | « urgences » = le *service*, pas le *mode* d'admission (une admission urgente peut aller en CARDIO, REA…) |
| **Alertes constantes** | FC < 40 ou > 120 · SpO2 < 92 · T° < 35 ou > 38,5 | ≈ 83 / jour | **SpO2 < 92 · FC < 50 ou > 100 · T° > 38,5** | **3 314 / 40 920 = 8,1 %** ; 2026-08-01 = 25 / 351 | seuils cliniques différents (FC resserrée, pas de borne basse de température) |
| **Prévalence par pathologie** | `uniqExact(patient_hash)` sur diagnostic **principal** seul, séjours **clos** | N39 = 847 | `uniqExact(patient_hash)` sur **tous les diagnostics** (principal + associé), y compris ceux des séjours écartés pour dates incohérentes | **N39 = 2 234** · E11 = 2 177 · I50 = 2 156 · J44 = 1 775 | une prévalence épidémiologique compte tout patient *porteur*, pas seulement en diagnostic principal ; et une coquille de date ne doit pas faire disparaître la pathologie du patient |
| **Cohorte** | `age_band × sex`, **global** (10 cellules) ; tranches `0-17 / 18-39 / 40-64 / 65-79 / 80+` | 10 cellules | **par pathologie principale** × tranche d'âge **décennale** × sexe | **89 cellules** diffusées ; E11/40-49 = F 107 · M 160 | granularité et bornes de tranches différentes |
| **DMS par service** | `avg(los_days)`, colonnes `nb_sejours_clos`, `dms_jours` | REA 9,1 j | idem + `dms_heures`, `nb_sejours` | REA **423 / 9,05 j / 217,1 h** (identique au 1/100) | cadrage — la définition de fond était bonne |

### Impact sur la couche silver

Le seul changement silver : **`silver.diagnostics` porte désormais `patient_hash`** et
**conserve les 127 diagnostics** des 68 séjours écartés pour incohérence de dates (l'erreur
est sur les *dates*, pas sur le *codage*). Ces diagnostics restent **exclus de
`gold.fact_sejour`** (durées, DMS) via l'`INNER JOIN silver.sejours`. Aucun autre point de
contrôle silver ne bouge.

## Contrôle automatique de l'alignement

`sql/5_checks/09_corrige_niveau1.sql` (joué par `make verify`) **échoue** si l'un des repères
de la feuille n'est pas atteint : réadmission 780 / 6 729 ; prévalence N39 = 2 234,
E11 = 2 177, I50 = 2 156 ; DMS REA 9,05 · NEURO 7,06 ; alertes 2026-08-01 = 25 / 351 ;
urgences 2026-08-01 = 46.

## k-anonymat — cellules masquées de la feuille

La feuille (usage intervenant) affiche les effectifs < 5 ; les vues `gold.kpi_recherche_*`
exposées à `ro_recherche` les **suppriment** (`HAVING nb_patients >= 5`). Requête **admin**
reproduisant ces cellules (hors périmètre `ro_recherche`) :

```sql
-- Prévalence complète (sans k-anonymat) : E84 = 4, Q90 = 3 → masqués dans la vue
SELECT code_cim10, uniqExact(patient_hash) AS n
FROM silver.diagnostics GROUP BY code_cim10 ORDER BY n DESC;

-- Cohorte principale complète pour les pathologies rares
SELECT d.code_cim10, p.age_band, p.sex, uniqExact(d.patient_hash) AS n
FROM silver.diagnostics d
INNER JOIN gold.dim_patient p ON p.patient_hash = d.patient_hash
WHERE d.type = 'principal' AND d.code_cim10 IN ('E84','Q90','G12')
GROUP BY d.code_cim10, p.age_band, p.sex ORDER BY d.code_cim10, p.age_band, p.sex;
```

Résultat (conforme à la feuille) : `E84` 0-9/F=1, 10-19/M=2, 20-29/F=1 ; `Q90` 0-9/M=1,
10-19/M=1, 30-39/F=1 ; `G12` 8 patients répartis en 7 cellules de 1 à 2 (seule la ligne
agrégée `G12` = 8 franchit le seuil et apparaît en prévalence).
