# 06 · Livrables & liste de contrôle

## Partie 1 — Interface d'analyse

- [x] **Dossier** : `report/dossier.md` (17 sections — Partie I § 1-11, Partie II § 12-17)
      → `report/dossier.pdf` via `make report` (design corporate repris du skill
      `rapport-performance-pdf`) ; schémas mermaid dans `report/schemas/` — `architecture` ·
      `bronze` · `silver` · `etoile` · `silver-v2` · `etoile-v2` (`make schema`)
- [x] **Interface** : 2 dashboards Metabase Partie I (+ 1 dashboard évolution, cf. plus bas),
      provisionnés par `make dashboards` (idempotent)
  - [x] Dashboard **Pilotage** (6 cartes) : DMS, activité urgences/jour, réadmission 30 j,
        alertes constantes, charge par service, modes de sortie
  - [x] Dashboard **Recherche** : prévalence par pathologie, cohorte pathologie × âge × sexe
  - [x] **Démonstration du cloisonnement** : `dashboards/captures/01-*` (base/collection),
        `02-*` (RBAC ClickHouse `ACCESS_DENIED`) ; détails `dashboards/README.md`
  - [x] Reproductible : définition dans `CARDS` / `DASHBOARDS` (`pipeline/steps/4_dashboards.py`),
        rejouée à l'identique par `make dashboards`

## Partie 2 — Automatisation

- [x] Pipeline planifié (`scripts/crontab.example`) : `eds run-daily` (ingest + transform + verify)
- [x] Gestion des erreurs : run en échec → `error` dans `meta.runs` + ligne `[ALERTE]` cron ; `make replay DATE=…`
- [x] Journalisation : `logs/pipeline-*.log`
- [x] Traçabilité : `meta.runs`, `meta.ingested_files`
- [x] **Contrôle de fiabilité** : `eds verify` — 12 contrôles de réconciliation (`sql/5_checks/`)
- [x] **Doc d'utilisation et de maintenance** : `README.md` + `.claude/skills/eds-run/SKILL.md`

## ★ Bonus — anonymisation à l'entrée du lake

- [x] Hachage déterministe salé de `patient_id`
- [x] `birth_date` → année
- [x] Suppression `nir`, `nom`, `prenom`
- [x] Aucune donnée identifiante n'atteint l'entrepôt

## ★ Évolution du sujet (dépôt 2026-08-29)

> Contexte : `07-evolution-contexte.md` · conception : `08-evolution-silver-kpi.md` ·
> comparatif corrigé niveau 1 : `09-corrige-niveau1-comparatif.md` ·
> dossier : `report/dossier.md` **Partie II** (§ 12-17).

- [x] **Ingestion incrémentale** du nouveau dépôt (`actes/`, `description_service.csv`,
      `ccam.csv`) — 6ᵉ source `actes` dans `pipeline/config.py`, aucune ré-ingestion de l'existant
- [x] **`dim_service` complétée** : `categorie`, `capacite_lits`, `pole` (via `silver.services`)
- [x] **`dim_ccam`** ajoutée (via `silver.ccam`, codes observés)
- [x] **`fact_acte`** ajoutée (grain = 1 acte ; `service_code` résolu dans `silver.actes`)
- [x] **5 KPI évolution** (`gold.kpi_pilotage_{activite_categorie, actes_service, actes_type,
      densite_actes_lit, montant_t2a}`) + `GRANT` `role_pilotage`
- [x] **3ᵉ dashboard** Metabase *« Pilotage — plateau technique & T2A »* (`make dashboards`)
- [x] **Piège 1** (service non décrit NEURO) : conservé, `(non décrit)`, tracé `clean.rejects`
- [x] **Piège 2** (service porté par le séjour) : résolu en silver, contrôle `11`
- [x] **Non-régression** : `fact_sejour` = 6 729 inchangé ; contrôles `10-12` ajoutés
- [x] **KPI niveau 1 réalignés** sur la feuille de réponses officielle + contrôle `09`

## Liste de contrôle avant remise

- [x] Le dépôt Git contient le code du pipeline (ingestion → transfos) + SQL versionné
      (`sql/` : `0_init/`, `1_bronze/`, `2_clean/`, `3_silver/`, `4_gold/`, `5_checks/`)
      **+ le jeu synthétique** `data/source-filestorage/` (exécutable sans import)
- [x] Les dashboards sont documentés et reproductibles (`dashboards/README.md` + captures)
- [x] `README.md` : comment lancer & rejouer
- [x] `make all` fonctionne à froid (up + init-db + ingest + transform + verify + dashboards)
- [x] `uv run pytest` au vert (17 tests) ; `make verify` 12/12
- [x] Le rapport PDF + les schémas (PNG) sont dans `report/`
- [x] **Premier commit Git** (`.env` et `data/lake/` non committés — `.gitignore` OK ;
      jeu source synthétique versionné volontairement)
