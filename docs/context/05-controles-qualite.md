# 05 · Contrôles qualité (couche silver)

> « Les données brutes reflètent la vraie vie » — pas forcément propres ni cohérentes.
> Le traitement attendu est **simple** : on **écarte** les lignes concernées (et on
> déduplique les patients), et **on trace ce qu'on écarte** dans `silver.rejects`.
> Seule exception : un séjour **sans date de sortie** n'est pas une anomalie.

## Contrôles imposés par le sujet

| Domaine | Contrôle | Règle / borne | Fichier SQL | Règle `rejects` |
|---|---|---|---|---|
| patients | doublons (retour quotidien du même patient) | dédupliquer, garder la version la plus récente | `silver/10_patients.sql` | *(pas un rejet : fusion)* |
| sejours | cohérence temporelle | écarter si `discharge_ts < admission_ts` | `silver/20_sejours.sql` | `sortie_avant_admission` |
| sejours | séjour en cours | `discharge_ts` vide = **légitime**, conservé | `silver/20_sejours.sql` | — |
| monitoring | valeurs hors plage physiologique | FC 20–250 · SpO2 50–100 · temp 30–45 | `silver/30_monitoring.sql` | `hors_plage_physiologique` |
| tous | valeurs manquantes / formats | dates valides, sexe normalisé M/F | `silver/10`,`20` | `admission_ts_invalide`, `sex_non_normalise` |

## Contrôles ajoutés (repérés en explorant — à défendre dans le dossier)

| Domaine | Contrôle | Fichier SQL | Règle `rejects` |
|---|---|---|---|
| diagnostics | diagnostic rattaché à un séjour inconnu / écarté | `silver/40_diagnostics.sql` | `sejour_inconnu` |
| diagnostics | `code_cim10` absent du référentiel | `silver/40_diagnostics.sql` | `code_cim10_hors_referentiel` |

## Pistes d'exploration supplémentaires (non implémentées)

- Séjours dont la durée est aberrante (> N mois) sans être négative.
- Patients avec `birth_year` dans le futur ou < 1900.
- `service_code` de séjour absent du référentiel `services`.
- Doublons de `stay_id` entre deux dépôts avec valeurs divergentes.
- Relevés `monitoring` dont le `stay_id` ne correspond à aucun séjour.

## Suivi

Après `make transform` :

```sql
SELECT source, rule, count() AS n
FROM silver.rejects
GROUP BY source, rule
ORDER BY n DESC;
```
Ce tableau alimente la section « qualité des traitements » du dossier.
