# Entrepôt de Données de Santé (EDS) — CHU

Projet fil rouge · **Big Data M2 · Épreuve E05**. Pipeline ELT en patron *médaillon*
(lake → bronze → silver → gold, plus une étape *clean* de quarantaine) sur
**ClickHouse**, piloté par **Python**, restitué dans **Metabase**. Conçu pour tourner
sur un laptop.

**Livrables** — *Partie 1* : dossier d'architecture [`report/dossier.pdf`](report/dossier.pdf)
et 2 dashboards Metabase (pilotage / recherche) avec démonstration du cloisonnement.
*Partie 2* : pipeline planifié, tracé et rejouable (§ [Automatisation](#automatisation-partie-2)).
Doc d'exploitation & reprise sur incident : [`.claude/skills/eds-run/SKILL.md`](.claude/skills/eds-run/SKILL.md).

> Contexte détaillé : [`docs/context/`](docs/context/) — synthèse du sujet, dictionnaire
> des données, KPI, contraintes RGPD, architecture, contrôles qualité, livrables.

## Prérequis

- Docker + Docker Compose
- [`uv`](https://docs.astral.sh/uv/) (Python 3.12)
- Node ≥ 18 (`npx`) — uniquement pour `make schema` / `make report` (régénération des
  schémas mermaid). `make all` n'en a pas besoin.

## Démarrage rapide

```bash
cp .env.example .env      # puis renseigner PSEUDO_SALT (secret)
make install              # dépendances Python
make seed                 # dézippe docs/eds-chu-sujet.zip -> data/source-filestorage/
make up                   # ClickHouse (:8123/play) + Metabase (:3000)
make init-db              # bases médaillon + meta + users RBAC
make ingest               # filestorage -> lake (pseudonymisé, incrémental)
make transform            # bronze -> clean -> silver -> gold (SQL dans ClickHouse)
make verify               # 8 contrôles de fiabilité (réconciliation KPI, k-anonymat)
make dashboards           # provisionne Metabase : connexions, groupes, 2 dashboards
make report               # génère report/dossier.pdf (+ schémas)
```

Ou tout enchaîner : `make all`.

## Accès

| Service | URL | Identifiants |
|---|---|---|
| ClickHouse (console SQL) | <http://localhost:8123/play> | `eds` / `eds` |
| Metabase — admin | <http://localhost:3000> | `admin@chu.local` (cf. `MB_ADMIN_PASSWORD` dans `.env`) |
| Metabase — démo pilotage | idem | `pilote@chu.local` (cf. `.env`) |
| Metabase — démo recherche | idem | `chercheur@chu.local` (cf. `.env`) |

Les mots de passe par défaut sont dans [`.env.example`](.env.example) ; `PSEUDO_SALT` est le seul secret à renseigner soi-même.

## Commandes

| Commande | Effet |
|---|---|
| `make ingest DATE=2026-08-27` | ingère une date précise (incrémental) |
| `make transform` | rejoue toutes les transformations SQL (bronze → clean → silver → gold) |
| `uv run eds run-daily` | traitement quotidien complet (ingest + transform + verify) dans un seul run tracé |
| `make replay DATE=2026-08-27` | **reprise sur incident** : ré-ingère + rejoue une date |
| `make verify` | contrôles de fiabilité — exit ≠ 0 si un chiffre ne se réconcilie pas |
| `make status` | historique des exécutions (`meta.runs`) |
| `make dashboards` | (re)provisionne Metabase — idempotent (voir `dashboards/README.md`) |
| `make schema` / `make report` | schémas mermaid → PNG / dossier PDF |
| `make test` | suite de tests (pseudonymisation, qualité, intégration) |
| `make down` / `make nuke` | arrêt / remise à zéro complète |

## Rejouer & reprise sur incident

Le pipeline est **incrémental et idempotent** :

- `meta.ingested_files` mémorise le hash de chaque fichier écrit dans le lake →
  ré-exécuter `make ingest` ne recopie rien de connu.
- Les transformations font un **rebuild complet** (`TRUNCATE` + `INSERT`) → `make transform`
  est rejouable sans doublon.
- Un run qui échoue est enregistré `status=error` dans `meta.runs` (avec le message).
  Correction puis `make replay DATE=<jour concerné>`.

## Structure

```
docs/context/     notes de contexte tirées des PDF/zip du sujet
pipeline/         CLI `eds` (cli.py) + plomberie (config, clickhouse, observabilite)
pipeline/steps/   les 4 étapes, numérotées : 1_lake, 2_medallion, 3_verify, 4_dashboards
sql/              0_init/ · 1_bronze/ · 2_clean/ · 3_silver/ · 4_gold/ · 5_checks/
dashboards/       README (provisioning Metabase) + captures du cloisonnement
scripts/          seed_filestorage.sh, crontab.example
report/           dossier.md + generate_pdf.py ; schemas/ (mermaid → PNG) → dossier.pdf
tests/            pytest (unitaires + intégration)
```

## Automatisation (Partie 2)

```bash
crontab scripts/crontab.example   # `eds run-daily` chaque jour à 02h15 ; [ALERTE] dans logs/cron.log sur échec
```

`run-daily` = `ingest(jour) + transform + verify` dans un **seul** `meta.runs`, code retour propre.
En cas d'incident : `make status` → identifier le run `error` → corriger → `make replay DATE=<jour>`.

## RGPD

Aucune donnée identifiante n'entre dans l'entrepôt : `patient_id` est haché
(déterministe + salé), `birth_date` réduite à l'année, `nir/nom/prenom` supprimés —
**avant** toute écriture dans le lake. Cloisonnement pilotage / recherche via des
users ClickHouse distincts. Cohortes < 5 patients masquées dans les vues recherche.
Détails : [`docs/context/03-contraintes-rgpd.md`](docs/context/03-contraintes-rgpd.md).
