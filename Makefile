# Entrepôt de Données de Santé (EDS) — CHU · pipeline ELT médaillon
# Usage : make <cible>   (voir `make help`)

SHELL := /bin/bash
DATES ?= 2026-08-26 2026-08-27 2026-08-28
RUN   := uv run eds

.DEFAULT_GOAL := help

.PHONY: help
help: ## Liste les cibles
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

## --- Environnement ---------------------------------------------------------
.PHONY: install
install: ## Installe les dépendances Python (uv)
	uv sync --extra dev

.PHONY: seed
seed: ## Dézippe le dépôt CHU dans data/source-filestorage/
	bash scripts/seed_filestorage.sh

.PHONY: up
up: ## Démarre ClickHouse + Metabase (attend que ClickHouse soit prêt)
	mkdir -p data/lake logs
	docker compose up -d clickhouse
	@for i in $$(seq 1 40); do \
		[ "$$(docker inspect eds-clickhouse --format '{{.State.Health.Status}}' 2>/dev/null)" = healthy ] && break; \
		sleep 2; done
	docker compose up -d
	@echo "ClickHouse : http://localhost:8123/play   Metabase : http://localhost:3000"

.PHONY: down
down: ## Arrête les conteneurs (garde les volumes)
	docker compose down

.PHONY: nuke
nuke: ## Arrête et SUPPRIME les volumes (remise à zéro totale)
	docker compose down -v

.PHONY: init-db
init-db: ## Crée les bases médaillon, meta et les users RBAC
	$(RUN) run --sql-only sql/0_init/00_databases.sql sql/0_init/01_meta.sql

## --- Pipeline -------------------------------------------------------------
DATE_ARGS = $(if $(DATE),--date $(DATE),$(foreach d,$(DATES),--date $(d)))

.PHONY: ingest
ingest: ## Ingère filestorage -> lake (incrémental). Ex: make ingest DATE=2026-08-27
	$(RUN) ingest $(DATE_ARGS)

.PHONY: transform
transform: ## Rejoue bronze -> silver -> gold (SQL dans ClickHouse)
	$(RUN) transform

.PHONY: all
all: seed up init-db ## Chaîne complète : seed + up + init-db + ingest + transform + verify + dashboards
	$(RUN) ingest $(foreach d,$(DATES),--date $(d))
	$(RUN) transform
	$(RUN) verify
	$(RUN) dashboards

.PHONY: verify
verify: ## Contrôles de fiabilité (réconciliation KPI, k-anonymat, cohérence)
	$(RUN) verify

.PHONY: replay
replay: ## Rejoue une date (reprise sur incident). Ex: make replay DATE=2026-08-27
	$(RUN) replay --date $(DATE)

.PHONY: status
status: ## Affiche l'historique des runs (meta.runs)
	$(RUN) status

## --- Restitution & qualité ----------------------------------------------
.PHONY: dashboards
dashboards: ## Provisionne Metabase : connexions, groupes, permissions, 2 dashboards (idempotent)
	$(RUN) dashboards

.PHONY: test
test: ## Tests unitaires (pseudonymisation, règles qualité)
	uv run pytest -q

## --- Dossier de rendu -------------------------------------------------------
MMDC = npx --yes @mermaid-js/mermaid-cli

.PHONY: schema
schema: ## Exporte les schémas mermaid en PNG (report/schemas/*.png)
	$(MMDC) -i report/schemas/architecture.mmd -o report/schemas/architecture.png -b white -w 1600
	$(MMDC) -i report/schemas/bronze.mmd       -o report/schemas/bronze.png       -b white -w 1500
	$(MMDC) -i report/schemas/silver.mmd       -o report/schemas/silver.png       -b white -w 1500
	$(MMDC) -i report/schemas/etoile.mmd       -o report/schemas/etoile.png       -b white -w 1400

.PHONY: report
report: schema ## Génère report/dossier.pdf depuis report/dossier.md (design corporate)
	uv run python report/generate_pdf.py
