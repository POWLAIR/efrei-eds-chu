# 01 · Dictionnaire des données

> Le CHU dépose chaque jour ses fichiers dans `source-filestorage/<source>/<AAAA-MM-JJ>/`.
> **Accès en lecture seule** : on recopie vers notre lake avant traitement.
> Volumétries ci-dessous = **constatées** dans `data/source-filestorage/` : 28 jours
> d'activité (2026-08-01 → 28) pour `sejours` / `diagnostics` / `monitoring` ;
> `patients` en 3 instantanés complets (2026-08-26/27/28) ; `referentiels` déposés le
> 1ᵉʳ jour (2026-08-01).

```
source-filestorage/
├── patients/<date>/patients.csv            CSV   ⚠ identité RÉELLE
├── sejours/<date>/sejours.csv              CSV
├── diagnostics/<date>/diagnostics.json     JSON  (imbriqué)
├── monitoring/<date>/monitoring.parquet    Parquet · volumineux
└── referentiels/<date>/{services,cim10}.csv CSV  (déposés le 1er jour uniquement)
```

## patients.csv — ⚠ contient l'identité réelle des patients

| Colonne | Type | Description | Traitement à l'entrée du lake |
|---|---|---|---|
| `patient_id` | texte | IPP — identifiant interne en clair. Clé de jointure avec `sejours` | → `patient_hash` (SHA-256 salé, 16 hex) |
| `nir` | texte | ⚠ N° sécurité sociale — directement identifiant | **supprimé** |
| `nom` | texte | ⚠ directement identifiant | **supprimé** |
| `prenom` | texte | ⚠ directement identifiant | **supprimé** |
| `birth_date` | date | date de naissance complète | → `birth_year` (année seule) |
| `sex` | texte | M / F | conservé, normalisé en silver |
| `region_code` | texte | département de résidence | conservé (utile cohortes, non directement identifiant) |

Volumétrie : **6 000 lignes** par instantané (3 instantanés → 18 000 lignes brutes).
Le même patient est présent dans chaque instantané → **déduplication** en silver, on
garde la version la plus récente (6 000 patients distincts).

Exemple brut : `IPP0000000,117049375510508,FOURNIER,Pierre,2019-04-07,M,93`

## sejours.csv — un séjour = un passage à l'hôpital

| Colonne | Type | Description |
|---|---|---|
| `stay_id` | texte | identifiant du séjour |
| `patient_id` | texte | référence patient → pseudonymisé comme `patient_hash` |
| `service_code` | texte | service d'hospitalisation (cf. référentiel `services`) |
| `admission_ts` | horodatage | date/heure d'admission |
| `discharge_ts` | horodatage | date/heure de sortie — **peut être vide** (séjour en cours = légitime) |
| `admission_mode` | texte | `urgence`, `programme`, `mutation` |
| `discharge_mode` | texte | `domicile`, `mutation`, `transfert`, `deces`… |

Volumétrie : **6 797 séjours** au total sur 28 jours (≈ 40 à 310/jour ; les 3 derniers
jours sont partiels). Exemple : `S00000017,IPP0000016,CARDIO,2026-08-01 06:23:00,2026-08-07 13:23:00,mutation,domicile`

## diagnostics.json — structure imbriquée (un ou plusieurs codes par séjour)

```json
[ { "stay_id": "S00000123",
    "diagnostics": [ { "code_cim10": "...", "type": "principal" },
                     { "code_cim10": "...", "type": "associe" } ] } ]
```
`type` ∈ { `principal`, `associe` }. ~40 Ko/jour ; 12 720 lignes au total (6 797 `principal` + 5 923 `associe`).

## monitoring.parquet — flux volumineux (constantes au chevet)

| Colonne | Type |
|---|---|
| `stay_id` | texte |
| `ts` | horodatage |
| `heart_rate` | entier (bpm) |
| `spo2` | entier (%) |
| `temp_c` | décimal (°C) |

~15-25 Ko/jour compressé ici (41 778 relevés au total), mais **c'est le flux qui
grossit** : l'architecture doit tenir la charge (colonne + partitionnement par jour).

## referentiels/ — nomenclatures

- `services.csv` : `service_code → service_label` (ex. `CARDIO,Cardiologie`) — **8 services**
- `cim10.csv` : `code_cim10 → libelle` (ex. `I21,Infarctus aigu du myocarde`) — **13 codes**

Déposés **le premier jour uniquement** (2026-08-01) → l'ingestion ne doit pas s'attendre
à les retrouver chaque jour.
