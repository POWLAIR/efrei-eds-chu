-- Silver — séjours : cohérence temporelle + intégrité référentielle.
--   * on écarte  discharge_ts < admission_ts (on ne sait pas quelle date est fausse)
--   * on conserve discharge_ts NULL (séjour en cours = légitime)
--   * on écarte  admission_ts NULL (date d'admission invalide)
--   * on écarte  service_code absent du référentiel
--   * on écarte  durée de séjour aberrante (> 180 j) — probable erreur de saisie

CREATE TABLE IF NOT EXISTS silver.sejours
(
    stay_id        String,
    patient_hash   String,
    service_code   LowCardinality(String),
    admission_ts   DateTime,
    discharge_ts   Nullable(DateTime),
    admission_mode LowCardinality(String),
    discharge_mode LowCardinality(String),
    los_hours      Nullable(Float64)   -- durée de séjour (NULL si en cours)
)
ENGINE = MergeTree
ORDER BY stay_id;

TRUNCATE TABLE silver.sejours;

INSERT INTO silver.sejours
SELECT
    b.stay_id, b.patient_hash, b.service_code,
    b.admission_ts, b.discharge_ts, b.admission_mode, b.discharge_mode,
    if(b.discharge_ts IS NULL, NULL, dateDiff('hour', b.admission_ts, b.discharge_ts)) AS los_hours
FROM bronze.sejours b
WHERE b.admission_ts IS NOT NULL
  AND (b.discharge_ts IS NULL OR b.discharge_ts >= b.admission_ts)
  AND (b.discharge_ts IS NULL OR dateDiff('day', b.admission_ts, b.discharge_ts) <= 180)
  AND b.service_code IN (SELECT service_code FROM bronze.ref_services);

-- Traces
INSERT INTO silver.rejects (source, natural_key, rule, detail)
SELECT 'sejours', stay_id, 'admission_ts_invalide', 'date/heure admission illisible'
FROM bronze.sejours WHERE admission_ts IS NULL;

INSERT INTO silver.rejects (source, natural_key, rule, detail)
SELECT 'sejours', stay_id, 'sortie_avant_admission',
       concat('discharge=', toString(discharge_ts), ' < admission=', toString(admission_ts))
FROM bronze.sejours
WHERE admission_ts IS NOT NULL AND discharge_ts IS NOT NULL AND discharge_ts < admission_ts;

INSERT INTO silver.rejects (source, natural_key, rule, detail)
SELECT 'sejours', stay_id, 'duree_sejour_aberrante',
       concat('los=', toString(dateDiff('day', admission_ts, discharge_ts)), ' j')
FROM bronze.sejours
WHERE admission_ts IS NOT NULL AND discharge_ts IS NOT NULL
  AND discharge_ts >= admission_ts
  AND dateDiff('day', admission_ts, discharge_ts) > 180;

INSERT INTO silver.rejects (source, natural_key, rule, detail)
SELECT 'sejours', stay_id, 'service_hors_referentiel', service_code
FROM bronze.sejours
WHERE admission_ts IS NOT NULL
  AND service_code NOT IN (SELECT service_code FROM bronze.ref_services);
