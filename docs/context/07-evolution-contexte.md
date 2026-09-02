# 07 · Évolution du sujet — contexte

> Source : `docs/SUJET-EVOLUTION-nouvelles-kpi.pdf` — *« Faites évoluer votre entrepôt —
> sans tout refaire, sans rien casser »*. Reçue après la finalisation de la Partie 1.
> Nouveau dépôt : `data/source-evolution.zip` → extrait dans `data/source-filestorage/`.

## Ce que le CHU ajoute

L'EDS tourne. Le CHU **ajoute des données** (il n'en modifie aucune) :

1. les **services** sont désormais **décrits plus finement** (catégorie, capacité en lits, pôle) ;
2. un **nouveau flux de faits** arrive : les **actes médicaux** (CCAM), avec leur tarif (T2A).

Un **nouveau dépôt** est livré à la date **2026-08-29** :

```
referentiels/2026-08-29/description_service.csv   CSV  — enrichit la description des services
referentiels/2026-08-29/ccam.csv                 CSV  — nomenclature des actes
actes/2026-08-29/actes.parquet                   Parquet — nouveau flux de faits (8 112 actes)
```

### `description_service.csv` — hiérarchie, pas redondance

| Colonne | Type | Description |
|---|---|---|
| `service_code` | texte | clé de jointure avec le service |
| `categorie` | texte | type de service, **regroupe plusieurs services** (`medecine`, `chirurgie`, `reanimation`, `urgences`…) |
| `capacite_lits` | entier | nombre de lits du service |
| `pole` | texte | pôle hospitalier, **regroupe plusieurs catégories** |

`service_label` → `categorie` → `pole` = **trois niveaux d'agrégation croissants** du même
axe « service ». Ils servent à analyser à différentes mailles, pas à répéter l'information.

### `ccam.csv` — nomenclature des actes

| Colonne | Type | Description |
|---|---|---|
| `code_ccam` | texte | code de l'acte médical |
| `libelle` | texte | libellé de l'acte |
| `tarif_euros` | entier | tarif de l'acte en euros (facturation T2A) |

### `actes.parquet` — nouveau flux de faits

| Colonne | Type | Description |
|---|---|---|
| `stay_id` | texte | référence au séjour |
| `code_ccam` | texte | acte réalisé (voir référentiel) |
| `acte_ts` | horodatage | date/heure de l'acte |

## Ce qu'on nous demande

1. **Ingérer** le nouveau dépôt via le pipeline **incrémental** (sans retraiter l'existant).
2. **Compléter** `dim_service` avec la description (catégorie, capacité, pôle).
3. **Ajouter** une dimension `dim_ccam` (nomenclature des actes).
4. **Ajouter** une table de faits `fact_acte`.
5. **Non-régression** : les KPI existants (DMS, urgences, prévalence…) doivent continuer à fonctionner.

## Les 5 KPI demandés (liés à l'évolution)

| # | KPI | Exploite |
|---|---|---|
| E1 | Activité et **DMS par catégorie de service** | `categorie` de `dim_service` |
| E2 | Nombre d'**actes par service** + nombre moyen d'actes par séjour | `fact_acte` (service via le séjour) |
| E3 | Nombre d'**actes par type d'acte** (les plus fréquents) | `fact_acte` + `dim_ccam` |
| E4 | **Densité d'actes par lit** (intensité du plateau technique) | `capacite_lits` de `dim_service` |
| E5 | **Montant facturé par service** (T2A) | `tarif_euros` de `dim_ccam` |

## Les 2 pièges (à justifier — cf. `08-evolution-silver-kpi.md`)

1. **Le référentiel de description peut être incomplet** : que faire d'un service **non décrit** ?
   → Sur ce dépôt, **NEURO** (Neurologie) n'est **pas** dans `description_service.csv`.
2. **« Actes par service »** : le service est porté par le **séjour**, pas par l'acte
   → il faut le récupérer **sans relier deux tables de faits entre elles**.
