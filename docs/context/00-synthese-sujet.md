# 00 · Synthèse du sujet — EDS du CHU

> Source : `docs/FICHE-SUJET.pdf` (épreuve **Big Data M2 · E05**) + `docs/SLIDES-THEORIE.pdf`.
> Données : jeu synthétique **versionné** dans `data/source-filestorage/` (le pipeline
> s'exécute sans import — cf. `03-contraintes-rgpd.md`).

## Contexte métier

Le CHU veut se doter d'un **Entrepôt de Données de Santé (EDS)**. Ses données sont
aujourd'hui éparpillées (dossier patient, urgences, laboratoire, monitoring des chambres)
et exportées **chaque jour** sous forme de fichiers, dans des **formats différents**
(CSV, JSON, Parquet). Deux usages visés :

| Public | Ce qu'il veut |
|---|---|
| **Pilotage hospitalier** | DMS par service, activité des urgences, réadmission à 30 j, alertes constantes |
| **Recherche clinique** | prévalence par pathologie (cohortes), description de cohorte (âge × sexe) |

⚠️ **Données de santé = catégorie particulière (RGPD art. 9).** La conformité est une
**contrainte de conception** présente à chaque étape (cf. `03-contraintes-rgpd.md`).

## La mission en 4 temps

1. **Récupérer** — automatiser la collecte des fichiers déposés chaque jour.
2. **Fiabiliser** — structurer des données hétérogènes en informations exploitables.
3. **Restituer** — produire des indicateurs via des dashboards.
4. **Automatiser** — rejouer le traitement seul, de façon fiable et tracée.

## Livrables (cf. `06-livrables-checklist.md`)

- **Partie 1 — Interface d'analyse** : un dossier (besoin, sources, archi justifiée,
  traitements, indicateurs, visualisations, limites & reco) + une interface ≥ 2 dashboards
  (pilotage + recherche) avec **démonstration du cloisonnement des droits**.
- **Partie 2 — Automatisation** : pipeline planifié (collecte + transformation) avec
  gestion des erreurs, journalisation, traçabilité + une **doc d'utilisation et de
  maintenance** (lancement, reprise sur incident).
- **★ Bonus fortement valorisé** : anonymisation automatisée à l'entrée du lake
  (hachage déterministe salé de l'identifiant patient, date de naissance → année,
  suppression des identifiants directs). → **implémenté** ici dès le départ.
- **★ Évolution du sujet** (dépôt 2026-08-29) : actes médicaux (CCAM / T2A) +
  description fine des services → `dim_service` enrichie, `dim_ccam`, `fact_acte`,
  5 KPI, 3ᵉ dashboard. Dossier **Partie II § 12-17** ; contexte `07` à `09`.

## Barème (indicatif, /20)

| Critère | Ce qu'on regarde |
|---|---|
| Analyse du besoin | compréhension de ce que veut l'hôpital |
| Architecture | choix cohérents et justifiés, schéma clair |
| Qualité des traitements | anomalies détectées et traitées, données fiables |
| Fiabilité des indicateurs | chiffres justes, cohérents, reproductibles |
| Restitution | dashboards lisibles, adaptés aux deux publics |
| Automatisation | rejouable, incrémentale, robuste aux erreurs |
| RGPD / gouvernance | pseudonymisation, cloisonnement, petits effectifs, traçabilité |
| Documentation | claire, suffisante pour reprendre le projet |
