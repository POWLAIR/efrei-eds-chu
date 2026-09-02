# 03 · Contraintes — RGPD, gouvernance, technique

| Contrainte | Ce qu'on attend | Où c'est traité dans ce repo |
|---|---|---|
| **Incrémental** | ingérer chaque jour les nouveaux fichiers, sans retraiter ni dupliquer | `meta.ingested_files` (hash du contenu) + `pipeline/steps/1_lake.py` |
| **Volume** | le monitoring est bien plus gros que le reste | ClickHouse colonne + `PARTITION BY toYYYYMMDD(ts)` sur `bronze/silver.monitoring` |
| **RGPD — pseudonymisation** | aucune donnée identifiante ne doit entrer dans l'entrepôt ; pseudonyme **stable** (jointures préservées) | `pipeline/steps/1_lake.py`, appliqué **avant** écriture dans le lake |
| **RGPD — minimisation** | ne conserver que ce qui est utile | `nir/nom/prenom` supprimés ; `birth_date → birth_year` ; âge en tranches |
| **RGPD — cloisonnement** | pilotage et recherche ne voient pas les mêmes données → droits distincts | users ClickHouse `ro_pilotage` / `ro_recherche` + rôles (`sql/0_init/00_databases.sql`) ; 2 connexions Metabase |
| **RGPD — petits effectifs** | ne pas diffuser les cohortes de moins de 5 patients | `HAVING … >= 5` **dans les vues** `gold.kpi_recherche_*` |
| **Traçabilité** | savoir d'où vient chaque donnée et quand elle a été traitée | `meta.runs` + `meta.ingested_files` + logs `logs/pipeline-*.log` |

## Pseudonymisation — détail (★ bonus)

À l'ingestion, `pipeline/steps/1_lake.py` (section « Pseudonymisation RGPD ») :

1. `patient_id` → `patient_hash = sha256(PSEUDO_SALT + ":" + patient_id)[:16]`
   → **déterministe** (même entrée ⇒ même sortie ⇒ jointures OK) et **non réversible**.
2. `birth_date` → `birth_year` (généralisation).
3. `nir`, `nom`, `prenom` → **supprimés** du fichier écrit dans le lake.
4. `sejours.csv` : `patient_id` remplacé par le **même** `patient_hash` → lien patient↔séjour conservé.
5. `region_code` conservé (donnée utile aux cohortes, pas un identifiant direct).

Le sel `PSEUDO_SALT` vit dans `.env` (jamais committé). **Sa perte = perte des
jointures historiques** → à sauvegarder hors dépôt.

## Ce que la conformité n'empêche pas de faire

- Les identifiants réels ne sont lus qu'**en transit**, en mémoire, le temps de hacher —
  ils ne sont jamais écrits sur disque dans le lake ni dans ClickHouse.
- Le jeu `data/source-filestorage/` est **100 % synthétique** (noms/NIR fabriqués) : il
  est **versionné** pour que l'intervenant exécute le pipeline sans import. En
  conditions réelles, ce dépôt (identité en clair) resterait hors Git et hors
  périmètre de l'entrepôt ; seul `data/lake/` (pseudonymisé) est déjà `.gitignore`.
