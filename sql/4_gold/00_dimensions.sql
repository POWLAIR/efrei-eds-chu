-- Gold — dimensions (axes d'analyse) et référentiels.

-- dim_service ENRICHIE (évolution 2026-08-29) : catégorie, capacité en lits, pôle.
-- Source = silver.services (référentiel promu + description jointe). Non-régression :
-- les vues existantes ne lisent que service_label. CREATE OR REPLACE : schéma élargi.
CREATE OR REPLACE TABLE gold.dim_service
(
    service_code  LowCardinality(String),
    service_label String,
    categorie     LowCardinality(String),
    capacite_lits Nullable(UInt16),
    pole          LowCardinality(String),
    is_described  UInt8
)
ENGINE = MergeTree ORDER BY service_code;
TRUNCATE TABLE gold.dim_service;
INSERT INTO gold.dim_service
SELECT service_code, service_label, categorie, capacite_lits, pole, is_described
FROM silver.services;

CREATE TABLE IF NOT EXISTS gold.dim_cim10
(
    code_cim10 LowCardinality(String),
    libelle    String
)
ENGINE = MergeTree ORDER BY code_cim10;
TRUNCATE TABLE gold.dim_cim10;
-- dim_cim10 découle de silver.pathologies (codes CIM-10 observés en diagnostics).
INSERT INTO gold.dim_cim10 SELECT code_cim10, libelle FROM silver.pathologies;

-- dim_ccam découle de silver.ccam (codes CCAM observés en actes) — évolution 2026-08-29.
CREATE TABLE IF NOT EXISTS gold.dim_ccam
(
    code_ccam   LowCardinality(String),
    libelle     String,
    tarif_euros UInt32
)
ENGINE = MergeTree ORDER BY code_ccam;
TRUNCATE TABLE gold.dim_ccam;
INSERT INTO gold.dim_ccam SELECT code_ccam, libelle, tarif_euros FROM silver.ccam;

-- Patient enrichi : tranche d'âge (calculée sur l'année de naissance — minimisation)
--   * Tranches DÉCENNALES (0-9 … 90-99 / 100+ / inconnu) — cf. feuille de réponses
--     officielle des KPI (corrigé niveau 1).
--   * Année de référence FIGÉE = année du dernier séjour observé (jeu « data figée »,
--     seed 42) → âge reproductible, indépendant de la date d'exécution.
CREATE TABLE IF NOT EXISTS gold.dim_patient
(
    patient_hash String,
    sex          LowCardinality(String),
    region_code  LowCardinality(String),
    age_years    Nullable(UInt16),
    age_band     LowCardinality(String)
)
ENGINE = MergeTree ORDER BY patient_hash;
TRUNCATE TABLE gold.dim_patient;
INSERT INTO gold.dim_patient
SELECT
    patient_hash, sex, region_code,
    age,
    multiIf(age IS NULL,  'inconnu',
            age < 10,  '0-9',   age < 20,  '10-19', age < 30,  '20-29',
            age < 40,  '30-39', age < 50,  '40-49', age < 60,  '50-59',
            age < 70,  '60-69', age < 80,  '70-79', age < 90,  '80-89',
            age < 100, '90-99', '100+') AS age_band
FROM (
    SELECT patient_hash, sex, region_code,
           ((SELECT toYear(max(admission_ts)) FROM silver.sejours) - birth_year) AS age
    FROM silver.patients
);
