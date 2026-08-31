---
name: eds-run
description: Lancer, rejouer et repriser le pipeline de l'Entrepôt de Données de Santé du CHU (ingestion, transformations médaillon ClickHouse, reprise sur incident). À utiliser pour toute demande d'exécution, de relance quotidienne ou de dépannage du pipeline EDS.
---

# Exécuter le pipeline EDS du CHU

Pipeline ELT médaillon : `source-filestorage` → lake (pseudonymisé) → bronze → silver → gold (ClickHouse) → Metabase.
Python **pilote** uniquement ; toutes les transformations sont en SQL dans `sql/`.

## Prérequis

1. `.env` présent (`cp .env.example .env`) avec **`PSEUDO_SALT`** renseigné (secret, non committé).
2. `make install` (dépendances `uv`).
3. `make up` — ClickHouse (`:8123/play`) + Metabase (`:3000`) démarrés et *healthy* (`docker compose ps`).
4. `make init-db` — crée `meta`, `bronze`, `silver`, `gold` + users `ro_pilotage` / `ro_recherche`.

## Exécution nominale (dépôt quotidien)

```bash
make seed                       # une seule fois : dézippe le dépôt CHU
uv run eds run-daily            # ingest(jour) + transform + verify, dans UN seul meta.runs
make status                     # vérifier meta.runs : dernier run = success
```

`run-daily` est ce que le cron exécute. Pour une date précise : `uv run eds run-daily --date 2026-08-27`.
Étapes séparées si besoin : `make ingest DATE=…`, `make transform`, `make verify`.
Plusieurs jours : `uv run eds ingest --date 2026-08-26 --date 2026-08-27 --date 2026-08-28`.

Chaîne complète à froid : `make all` (seed + up + init-db + ingest + transform + verify + dashboards).

## Vérifications rapides (SQL, via `:8123/play` ou `uv run eds`)

```sql
SELECT count() FROM bronze.patients;                    -- 16200 sur les 3 jours
SELECT count() FROM silver.patients;                    -- 6000 (déduplication)
SELECT count() FROM silver.sejours;                     -- 14864 (= gold.fact_sejour)
SELECT source, rule, count() FROM silver.rejects GROUP BY 1,2 ORDER BY 3 DESC;
SELECT * FROM gold.kpi_recherche_prevalence;            -- aucune cohorte < 5
```

Ou, plus simple : `make verify` — 7 contrôles de réconciliation, exit ≠ 0 si un chiffre ne colle pas.

## Reprise sur incident

1. Identifier le run en échec : `make status` (colonne `status=error`, colonne `error`).
2. Corriger la cause (fichier source mal formé, ClickHouse arrêté, SQL cassé…).
3. Rejouer **la date concernée** :
   ```bash
   make replay DATE=2026-08-27
   ```
   `replay` ré-ingère (l'incrémental évite les doublons) puis rejoue toutes les transformations.
4. Confirmer : `make status` → nouveau run `replay` en `success`.

Remise à zéro totale si nécessaire : `make nuke && make all`.

## Planification

`crontab scripts/crontab.example` — `eds run-daily` chaque jour à 02h15. En cas d'échec
(ingestion, transfo ou `verify`), une ligne `[ALERTE]` est écrite dans `logs/cron.log`
et le run est marqué `error` dans `meta.runs`. Surveillance : `grep ALERTE logs/cron.log`.

## Dossier de rendu

`make schema` régénère `report/architecture.png` / `report/etoile.png` depuis les `.mmd`.
`make report` régénère `report/dossier.pdf` depuis `report/dossier.md`
(`report/generate_pdf.py` — QA visuelle avec `--qa` : PNG par page, à supprimer ensuite).

## Points d'attention

- **Ne jamais** committer `data/lake/`, `data/source-filestorage/`, `.env` (déjà dans `.gitignore`).
- La perte de `PSEUDO_SALT` casse toutes les jointures patient historiques → le sauvegarder hors dépôt.
- Les référentiels (`services`, `cim10`) ne sont déposés que le **premier jour** : ne pas
  traiter leur absence les jours suivants comme une erreur.
- `make transform` fait un `TRUNCATE`+`INSERT` par table : c'est voulu (idempotence), pas un bug.
- Metabase (image `v0.63`) : 1ᵉʳ boot lent (~3 min) ; `make dashboards` attend qu'il soit prêt.
- **Ne pas `rm -rf data/lake`** pendant que ClickHouse tourne : le bind-mount se casse
  (le conteneur voit un dossier vide → `file()` échoue en code 636). Pour repartir de zéro :
  `rm -rf data/lake/*` puis re-`ingest`, ou `docker compose restart clickhouse`.
- Les tests d'intégration utilisent le **`.env` réel** (même sel) et ne touchent jamais le lake.
