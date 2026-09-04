# Restitution — dashboards Metabase (pilotage · recherche · plateau technique)

Metabase : <http://localhost:3000> · driver ClickHouse **intégré au cœur** (image `v0.63`, aucun JAR).

## Voie automatique (par défaut)

```bash
make up          # ClickHouse + Metabase
make dashboards  # = uv run eds dashboards  — idempotent
```

`pipeline/steps/4_dashboards.py` provisionne **tout** via l'API REST, de façon *find-or-create*
(relancer ne duplique rien). La définition des dashboards — cartes, SQL, disposition —
vit dans les constantes `CARDS` / `DASHBOARDS` de ce fichier : c'est la source de vérité.

| Étape | Détail |
|---|---|
| Compte admin | créé au 1er lancement (`MB_ADMIN_*` dans `.env`) |
| 2 connexions ClickHouse | `EDS — Pilotage` (user `ro_pilotage`) · `EDS — Recherche` (user `ro_recherche`), schéma `gold` |
| 2 groupes | `Pilotage`, `Recherche` — chacun peut interroger **sa** base, pas l'autre ; « All Users » n'interroge aucune EDS |
| 2 utilisateurs de démo | `pilote@chu.local` / `chercheur@chu.local` (mots de passe dans `.env`) |
| 2 collections | `Pilotage` / `Recherche` — lecture réservée au groupe correspondant |
| 13 cartes | 1 requête SQL native par vue `gold.kpi_*` (mises à jour en place si le SQL change) |
| 3 dashboards | **Pilotage hospitalier** (6) · **Pilotage — plateau technique & T2A** (5, évolution) · **Recherche clinique** (2) |
| Nettoyage | base d'exemple supprimée, collection *Examples* archivée |

> Le 3ᵉ dashboard (**plateau technique & T2A** — évolution du sujet) est dans la
> collection *Pilotage* : même public, même `GRANT` `role_pilotage`. Cartes : activité/DMS
> par catégorie, actes par service, actes par type, densité d'actes par lit, montant T2A
> par service.

## Le cloisonnement des droits

Deux niveaux, le second étant la vraie garantie :

1. **Metabase** — permissions de données par groupe + permissions de collections :
   un membre du groupe *Recherche* ne voit ni la base *EDS — Pilotage*, ni la
   collection/dashboard *Pilotage*.
2. **ClickHouse RBAC** (`sql/0_init/00_databases.sql`) — `ro_recherche` n'a de `GRANT SELECT`
   que sur `gold.kpi_recherche_*`. Même en SQL libre via Metabase, une requête sur
   `gold.kpi_pilotage_dms` renvoie `Not enough privileges (ACCESS_DENIED)`.
   Les vues recherche sont `SQL SECURITY DEFINER` → le k-anonymat (`HAVING ≥ 5`)
   s'applique quel que soit l'appelant.

### Captures (livrable) — `captures/`

| Fichier | Ce qu'il prouve |
|---|---|
| `01-cloisonnement-recherche.png` | connecté en `chercheur@chu.local` : seules la base **EDS — Recherche** et la collection **Recherche** sont visibles |
| `02-rbac-clickhouse-denied.png` | `chercheur` lance `SELECT * FROM gold.kpi_pilotage_dms` sur la connexion Recherche → `ro_recherche: Not enough privileges … ACCESS_DENIED` |
| `03-dashboard-pilotage.png` | dashboard Pilotage (DMS 2,15 à 9,05 j, activité urgences/j, réadmission 30 j = 11,59 %, alertes constantes, charge par service, modes de sortie) |
| `04-dashboard-recherche.png` | dashboard Recherche (prévalence par pathologie — 11 diffusées, Q90/E84 masqués k<5 —, cohorte en pyramide âge × sexe, tranches décennales) |
| `05-dashboard-plateau-technique.png` | dashboard **Plateau technique & T2A** (évolution) : activité/DMS par catégorie, actes/service, actes/type, densité actes-lit, montant T2A/service |

## Voie manuelle (repli, si l'API bloque)

1. `Admin → Databases → Add database` → ClickHouse, hôte `clickhouse`, port `8123`,
   base `gold`, user `ro_pilotage` / `ro_recherche`. Une connexion par user.
2. `Admin → People → Groups` → créer `Pilotage`, `Recherche`.
3. `Admin → Permissions → Data` → chaque groupe : *Query builder and native* sur SA
   base, *No* sur l'autre ; `All Users` : *No* sur les deux.
4. `Admin → Permissions → Collections` → collection `Pilotage` visible par le groupe
   `Pilotage` seulement (idem `Recherche`).
5. Créer les 13 questions SQL (cf. `CARDS` dans `pipeline/steps/4_dashboards.py`) puis les 3 dashboards.

## Reproductibilité

Sur un Metabase vierge, `make dashboards` recrée l'ensemble à l'identique depuis
`CARDS` / `DASHBOARDS`. Les captures de `captures/` figent le rendu et la preuve
du cloisonnement à la remise.
