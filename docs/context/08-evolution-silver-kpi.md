# 08 · Évolution — conception du silver à partir des KPI

> Principe de la démarche : **on part des KPI à produire**, on en déduit les tables
> silver/gold strictement nécessaires, et chaque table est justifiée par un KPI.

## Du KPI à la table

| KPI | Donnée nécessaire | Table créée / étendue | Rôle |
|---|---|---|---|
| E1 · Activité + DMS par catégorie | `categorie` du service | **`silver.services`** (référentiel promu + enrichi) → `gold.dim_service` | dimension à 3 niveaux (`service_label` → `categorie` → `pole`) |
| E2 · Actes par service + moyenne / séjour | actes reliés au **service du séjour** | **`silver.actes`** (service résolu ici) → **`gold.fact_acte`** | fait « acte », grain = 1 acte |
| E3 · Actes par type | libellé de l'acte | **`silver.ccam`** → **`gold.dim_ccam`** | dimension « nature de l'acte » |
| E4 · Densité d'actes par lit | `capacite_lits` | `silver.services.capacite_lits` → `gold.dim_service` | mesure de dénominateur |
| E5 · Montant T2A par service | `tarif_euros` × actes | `tarif_euros` porté en **mesure** sur `gold.fact_acte` | montant facturé |

Rien de plus : pas de `dim_pole` séparée (le pôle est un attribut de `dim_service`,
pas un axe distinct), pas de `fact_facturation` (le montant est une mesure de `fact_acte`).

## `silver.services` — le référentiel promu, comme `silver.pathologies`

Le dossier § 11 recommandait déjà de matérialiser le référentiel `services` en silver
« pour rendre la chaîne symétrique ». L'évolution le rend nécessaire : la description
(catégorie, capacité, pôle) doit être **nettoyée et complétée** avant d'alimenter le gold.

- **Liste autoritaire = `bronze.ref_services`** (8 services). La description
  (`bronze.ref_service_desc`, 7 lignes) est jointe en **LEFT JOIN**.
- Un service **non décrit** (NEURO) est **conservé**, `categorie` / `pole` = `'(non décrit)'`,
  `capacite_lits` = `NULL`, `is_described = 0`, tracé dans `clean.rejects`
  (règle `service_sans_description` — **audit, pas exclusion**).

### Piège 1 — service non décrit : le choix

| Option | Conséquence | Retenu ? |
|---|---|---|
| **Exclure NEURO** de `dim_service` | on perd 1 208 séjours et 1 471 actes des analyses « par catégorie / par pôle » ; les totaux ne réconcilient plus avec `fact_sejour` | ❌ |
| **Conserver NEURO, catégorie « (non décrit) »** | KPI E1 affiche un groupe `(non décrit)` explicite ; KPI E4 densité = `NULL` pour NEURO (pas de capacité connue) ; le trou est **visible et tracé** | ✅ |
| Deviner la catégorie (Neurologie → medecine ?) | on **invente** une donnée absente de la source — contraire à l'esprit RGPD / qualité du projet | ❌ |

Le trou de référentiel devient un **signal à remonter au CHU**, pas une perte silencieuse.

## `silver.actes` — le service vient du séjour (piège 2)

Le sujet insiste : « le service est porté par le **séjour**, pas par l'acte —
récupérez-le **sans** relier deux tables de faits entre elles ».

- Le `service_code` (et le `patient_hash`) sont résolus **une seule fois**, dans
  `silver.actes`, par jointure `bronze.actes → bronze.sejours`.
- `gold.fact_acte` **hérite** de ce `service_code` **dénormalisé** → **aucune vue gold
  ne joint `fact_acte` à `fact_sejour`**. Le contrôle `11_actes_service_provenance`
  vérifie l'égalité `fact_acte.service_code == service du séjour` (0 écart).
- Pourquoi pas une jointure `fact_acte ⋈ fact_sejour` dans les KPI : joindre deux tables
  de faits de grains différents (acte / séjour) fait **exploser les lignes** (produit
  cartésien acte × séjour du même patient) et fausse tous les comptages. La règle du
  schéma en étoile : un fait ne se joint qu'à des **dimensions**.

### Rétention des actes des séjours écartés

Même principe que `silver.diagnostics` (cf. `09-corrige-niveau1-comparatif.md`) : un acte
porté par un séjour écarté pour **dates incohérentes** reste un acte **réel et facturable**
— on le **conserve** (82 actes sur ce dépôt), service et patient pris dans `bronze.sejours`.
On n'écarte que l'acte au `stay_id` totalement inconnu ou au `code_ccam` hors référentiel
(0 cas sur ce dépôt).

## `silver.ccam` — référentiel matérialisé (miroir de `silver.pathologies`)

Codes CCAM **réellement observés** dans `silver.actes`, avec libellé + tarif canoniques de
`bronze.ref_ccam`. Alimente `gold.dim_ccam`. Contrôle `12_ccam_integrite` : tout code de
`silver.actes` ∈ `silver.ccam` ⊆ référentiel.

## Gold — 1 fait, 2 dimensions, 5 vues

- `gold.dim_service` **étendue** (`categorie`, `capacite_lits`, `pole`, `is_described`) —
  source `silver.services`. Non-régression : les vues existantes ne lisent que `service_label`.
- `gold.dim_ccam` **nouvelle** — source `silver.ccam`.
- `gold.fact_acte` **nouveau** — `stay_id, patient_hash, service_code, acte_date, acte_ts,
  code_ccam, tarif_euros`. `PARTITION BY toYYYYMM(acte_date)` (comme le monitoring, le flux grossira).
- `gold.kpi_pilotage_{activite_categorie, actes_service, actes_type, densite_actes_lit, montant_t2a}`
  — 5 vues `SQL SECURITY DEFINER`, `GRANT SELECT … TO role_pilotage` (même public).
