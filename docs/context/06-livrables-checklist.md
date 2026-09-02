# 06 · Livrables & liste de contrôle

## Partie 1 — Interface d'analyse

- [x] **Dossier** : `report/dossier.md` (11 sections) → `report/dossier.pdf` via `make report`
      (design corporate repris du skill `rapport-performance-pdf`) ; schémas mermaid dans
      `report/schemas/` — `bronze` · `architecture` · `silver` · `etoile` (`make schema`)
- [x] **Interface** : 2 dashboards Metabase, provisionnés par `make dashboards` (idempotent)
  - [x] Dashboard **Pilotage** (6 cartes) : DMS, urgences/jour, réadmission 30 j, alertes
        constantes, charge par service, modes de sortie
  - [x] Dashboard **Recherche** : prévalence par pathologie, cohorte âge × sexe
  - [x] **Démonstration du cloisonnement** : `dashboards/captures/01-*` (base/collection),
        `02-*` (RBAC ClickHouse `ACCESS_DENIED`) ; détails `dashboards/README.md`
  - [x] Reproductible : définition dans `CARDS` / `DASHBOARDS` (`pipeline/steps/4_dashboards.py`),
        rejouée à l'identique par `make dashboards`

## Partie 2 — Automatisation

- [x] Pipeline planifié (`scripts/crontab.example`) : `eds run-daily` (ingest + transform + verify)
- [x] Gestion des erreurs : run en échec → `error` dans `meta.runs` + ligne `[ALERTE]` cron ; `make replay DATE=…`
- [x] Journalisation : `logs/pipeline-*.log`
- [x] Traçabilité : `meta.runs`, `meta.ingested_files`
- [x] **Contrôle de fiabilité** : `eds verify` — 8 contrôles de réconciliation (`sql/5_checks/`)
- [x] **Doc d'utilisation et de maintenance** : `README.md` + `.claude/skills/eds-run/SKILL.md`

## ★ Bonus — anonymisation à l'entrée du lake

- [x] Hachage déterministe salé de `patient_id`
- [x] `birth_date` → année
- [x] Suppression `nir`, `nom`, `prenom`
- [x] Aucune donnée identifiante n'atteint l'entrepôt

## Liste de contrôle avant remise

- [x] Le dépôt Git contient le code du pipeline (ingestion → transfos) + SQL versionné
      (`sql/` : `0_init/`, `1_bronze/`, `2_clean/`, `3_silver/`, `4_gold/`, `5_checks/`)
      **+ le jeu synthétique** `data/source-filestorage/` (exécutable sans import)
- [x] Les dashboards sont documentés et reproductibles (`dashboards/README.md` + captures)
- [x] `README.md` : comment lancer & rejouer
- [x] `make all` fonctionne à froid (up + init-db + ingest + transform + verify + dashboards)
- [x] `uv run pytest` au vert (12 tests)
- [x] Le rapport PDF + les schémas (PNG) sont dans `report/`
- [x] **Premier commit Git** (`.env` et `data/lake/` non committés — `.gitignore` OK ;
      jeu source synthétique versionné volontairement)
