-- Bronze — séjours : 1 séjour = 1 passage à l'hôpital. discharge_ts peut être vide.

CREATE TABLE IF NOT EXISTS bronze.sejours
(
    stay_id        String,
    patient_hash   String,
    service_code   LowCardinality(String),
    admission_ts   Nullable(DateTime),
    discharge_ts   Nullable(DateTime),
    admission_mode LowCardinality(String),
    discharge_mode LowCardinality(String)
)
ENGINE = MergeTree
ORDER BY stay_id;

TRUNCATE TABLE bronze.sejours;

INSERT INTO bronze.sejours
SELECT
    stay_id,
    patient_hash,
    service_code,
    parseDateTimeBestEffortOrNull(admission_ts)  AS admission_ts,
    parseDateTimeBestEffortOrNull(discharge_ts)  AS discharge_ts,
    admission_mode,
    discharge_mode
FROM file('lake/sejours/*/sejours.csv', 'CSVWithNames',
          'stay_id String, patient_hash String, service_code String, admission_ts String, discharge_ts String, admission_mode String, discharge_mode String');
