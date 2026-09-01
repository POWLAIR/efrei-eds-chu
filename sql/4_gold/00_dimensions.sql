-- Gold — dimensions (axes d'analyse) et référentiels.

CREATE TABLE IF NOT EXISTS gold.dim_service
(
    service_code  LowCardinality(String),
    service_label String
)
ENGINE = MergeTree ORDER BY service_code;
TRUNCATE TABLE gold.dim_service;
INSERT INTO gold.dim_service SELECT service_code, service_label FROM bronze.ref_services;

CREATE TABLE IF NOT EXISTS gold.dim_cim10
(
    code_cim10 LowCardinality(String),
    libelle    String
)
ENGINE = MergeTree ORDER BY code_cim10;
TRUNCATE TABLE gold.dim_cim10;
-- dim_cim10 découle de silver.pathologies (codes CIM-10 observés en diagnostics).
INSERT INTO gold.dim_cim10 SELECT code_cim10, libelle FROM silver.pathologies;

-- Patient enrichi : tranche d'âge (calculée sur l'année de naissance — minimisation)
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
    multiIf(age IS NULL, 'inconnu',
            age < 18, '0-17', age < 40, '18-39', age < 65, '40-64',
            age < 80, '65-79', '80+') AS age_band
FROM (
    SELECT patient_hash, sex, region_code,
           (toYear(now()) - birth_year) AS age
    FROM silver.patients
);
