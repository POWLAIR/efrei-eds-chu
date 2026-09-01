-- Gold — fait central : 1 ligne = 1 séjour valide, avec ses mesures.

CREATE TABLE IF NOT EXISTS gold.fact_sejour
(
    stay_id           String,
    patient_hash      String,
    service_code      LowCardinality(String),
    admission_date    Date,
    admission_ts      DateTime,
    discharge_ts      Nullable(DateTime),
    admission_mode    LowCardinality(String),
    discharge_mode    LowCardinality(String),
    los_hours         Nullable(Float64),
    los_days          Nullable(Float64),
    is_closed         UInt8,
    is_urgence        UInt8,
    diag_principal    LowCardinality(String)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(admission_date)
ORDER BY (service_code, admission_date, stay_id);

TRUNCATE TABLE gold.fact_sejour;

INSERT INTO gold.fact_sejour
SELECT
    s.stay_id,
    s.patient_hash,
    s.service_code,
    toDate(s.admission_ts)                       AS admission_date,
    s.admission_ts,
    s.discharge_ts,
    s.admission_mode,
    s.discharge_mode,
    s.los_hours,
    round(s.los_hours / 24, 2)                   AS los_days,
    s.discharge_ts IS NOT NULL                   AS is_closed,
    s.admission_mode = 'urgence'                 AS is_urgence,
    any(if(d.type = 'principal', d.code_cim10, NULL)) AS diag_principal
FROM silver.sejours s
LEFT JOIN silver.diagnostics d ON d.stay_id = s.stay_id
GROUP BY s.stay_id, s.patient_hash, s.service_code, s.admission_ts, s.discharge_ts,
         s.admission_mode, s.discharge_mode, s.los_hours;
