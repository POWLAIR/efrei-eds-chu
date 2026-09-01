# 05 · Contrôles qualité (silver) & journal de quarantaine (clean)

> « Les données brutes reflètent la vraie vie » — pas forcément propres ni cohérentes.
> Le traitement attendu est **simple** : on **écarte** les lignes concernées (et on
> déduplique les patients), et **on trace ce qu'on écarte** dans `clean.rejects` —
> une **étape *clean* distincte** de la base analytique silver (journal opérationnel,
> pas une table d'analyse).
> Seule exception : un séjour **sans date de sortie** n'est pas une anomalie.

## Contrôles imposés par le sujet

| Domaine | Contrôle | Règle / borne | Fichier SQL | Règle `clean.rejects` |
|---|---|---|---|---|
| patients | doublons (retour quotidien du même patient) | dédupliquer, garder la version la plus récente | `3_silver/10_patients.sql` | *(pas un rejet : fusion)* |
| sejours | cohérence temporelle | écarter si `discharge_ts < admission_ts` | `3_silver/20_sejours.sql` | `sortie_avant_admission` |
| sejours | séjour en cours | `discharge_ts` vide = **légitime**, conservé | `3_silver/20_sejours.sql` | — |
| monitoring | valeurs hors plage physiologique | FC 20–250 · SpO2 50–100 · temp 30–45 | `3_silver/30_monitoring.sql` | `hors_plage_physiologique` |
| tous | valeurs manquantes / formats | dates valides, sexe normalisé M/F | `3_silver/10`,`20` | `admission_ts_invalide`, `sex_non_normalise` |

## Contrôles ajoutés (repérés en explorant — à défendre dans le dossier)

| Domaine | Contrôle | Fichier SQL | Règle `clean.rejects` |
|---|---|---|---|
| diagnostics | diagnostic rattaché à un séjour inconnu / écarté | `3_silver/40_diagnostics.sql` | `sejour_inconnu` |
| diagnostics | `code_cim10` absent du référentiel | `3_silver/40_diagnostics.sql` | `code_cim10_hors_referentiel` |
| sejours | durée > 180 j (sans être négative) | `3_silver/20_sejours.sql` | `duree_sejour_aberrante` |
| sejours | `service_code` absent du référentiel `services` | `3_silver/20_sejours.sql` | `service_hors_referentiel` |
| patients | `birth_year` dans le futur ou < 1900 → NULL, tracé | `3_silver/10_patients.sql` | `birth_year_aberrant` |
| diagnostics → pathologies | tout `code_cim10` de `silver.diagnostics` ∈ `silver.pathologies` ⊆ référentiel | `5_checks/08_pathologies_integrite.sql` | *(contrôle `verify`, pas un rejet)* |

## Choix : `monitoring` = flux autonome

`silver.monitoring` n'est **plus** contraint à `silver.sejours` : un relevé au
`stay_id` inconnu est **conservé** (télémétrie réelle, flux volumineux traité
indépendamment). Le taux d'orphelins devient un **signal à remonter au CHU**, pas
une exclusion silver. Seules les bornes physiologiques restent appliquées.

## Pistes d'exploration supplémentaires (non implémentées)

- Doublons de `stay_id` entre deux dépôts avec valeurs divergentes.
- `admission_mode` / `discharge_mode` hors nomenclature.

## Suivi

Après `make transform` :

```sql
SELECT source, rule, count() AS n
FROM clean.rejects
GROUP BY source, rule
ORDER BY n DESC;
```

Ce tableau alimente la section « qualité des traitements » du dossier.
