-- Bronze — patients : CSV pseudonymisé du lake -> table typée.
-- Le lake est monté dans ClickHouse sous user_files/lake/.
-- Retour quotidien du même patient => on conserve ici toutes les versions
-- (avec leur date de dépôt) ; la déduplication se fait en silver.

CREATE TABLE IF NOT EXISTS bronze.patients
(
    patient_hash  String,
    birth_year    Nullable(UInt16),
    sex           LowCardinality(String),
    region_code   LowCardinality(String),
    business_date Date
)
ENGINE = MergeTree
ORDER BY (patient_hash, business_date);

-- Rebuild complet depuis le lake : garantit l'idempotence de `make transform`.
TRUNCATE TABLE bronze.patients;

INSERT INTO bronze.patients (patient_hash, birth_year, sex, region_code, business_date)
SELECT
    patient_hash,
    toUInt16OrNull(birth_year) AS birth_year,
    sex,
    region_code,
    toDate(extract(_path, '(\\d{4}-\\d{2}-\\d{2})')) AS business_date
FROM file('lake/patients/*/patients.csv', 'CSVWithNames',
          'patient_hash String, birth_year String, sex String, region_code String');
