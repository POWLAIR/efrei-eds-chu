# 01 · Dictionnaire des données

> Le CHU dépose chaque jour ses fichiers dans `source-filestorage/<source>/<AAAA-MM-JJ>/`.
> **Accès en lecture seule** : on recopie vers notre lake avant traitement.
> Volumétries ci-dessous = **constatées** dans `docs/eds-chu-sujet.zip` (3 jours : 2026-08-26/27/28).

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

Volumétrie : **4801 / 5401 / 6001** lignes. Le même patient revient d'un jour à l'autre
→ **déduplication** en silver, on garde la version la plus récente.

Exemple brut : `IPP0000000,133129422914332,THOMAS,Manon,1933-12-09,M,94`

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

Volumétrie : **5001** lignes/jour. Exemple : `S00000001,IPP0002155,PEDIA,2026-08-26 17:50:00,2026-09-04 19:50:00,mutation,domicile`

## diagnostics.json — structure imbriquée (un ou plusieurs codes par séjour)

```json
[ { "stay_id": "S00000123",
    "diagnostics": [ { "code_cim10": "...", "type": "principal" },
                     { "code_cim10": "...", "type": "associe" } ] } ]
```
`type` ∈ { `principal`, `associe` }. ~1 Mo/jour.

## monitoring.parquet — flux volumineux (constantes au chevet)

| Colonne | Type |
|---|---|
| `stay_id` | texte |
| `ts` | horodatage |
| `heart_rate` | entier (bpm) |
| `spo2` | entier (%) |
| `temp_c` | décimal (°C) |

~100 Ko/jour compressé ici, mais **c'est le flux qui grossit** : l'architecture doit tenir
la charge (colonne + partitionnement par jour).

## referentiels/ — nomenclatures

- `services.csv` : `service_code → service_label` (ex. `CARDIO,Cardiologie`)
- `cim10.csv` : `code_cim10 → libelle` (ex. `I21,Infarctus aigu du myocarde`)

Déposés **le premier jour uniquement** → l'ingestion ne doit pas s'attendre à les
retrouver chaque jour.
