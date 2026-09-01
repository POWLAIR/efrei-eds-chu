-- Silver — monitoring : flux de faits AUTONOME (non rattaché à silver.sejours).
--   Plausibilité physiologique uniquement : FC 20–250 bpm · SpO2 50–100 % · temp 30–45 °C
--   Une ligne est écartée si AU MOINS une constante renseignée est hors borne.
--   Le monitoring est un flux volumineux traité indépendamment : un relevé dont le
--   stay_id est absent de silver.sejours est CONSERVÉ (télémétrie réelle) ; le taux
--   d'orphelins est un signal de qualité à remonter au CHU (cf. dossier § 11).

CREATE TABLE IF NOT EXISTS silver.monitoring
(
    stay_id    String,
    ts         DateTime,
    heart_rate Nullable(Int32),
    spo2       Nullable(Int32),
    temp_c     Nullable(Float32)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(ts)
ORDER BY (stay_id, ts);

TRUNCATE TABLE silver.monitoring;

INSERT INTO silver.monitoring
SELECT m.stay_id, m.ts, m.heart_rate, m.spo2, m.temp_c
FROM bronze.monitoring m
WHERE (m.heart_rate IS NULL OR m.heart_rate BETWEEN 20 AND 250)
  AND (m.spo2       IS NULL OR m.spo2       BETWEEN 50 AND 100)
  AND (m.temp_c     IS NULL OR m.temp_c     BETWEEN 30 AND 45);

-- Traces (journal de quarantaine — étape clean, hors silver)
INSERT INTO clean.rejects (source, natural_key, rule, detail)
SELECT 'monitoring', concat(stay_id, '@', toString(ts)), 'hors_plage_physiologique',
       concat('hr=', toString(heart_rate), ' spo2=', toString(spo2), ' temp=', toString(temp_c))
FROM bronze.monitoring
WHERE (heart_rate IS NOT NULL AND heart_rate NOT BETWEEN 20 AND 250)
   OR (spo2       IS NOT NULL AND spo2       NOT BETWEEN 50 AND 100)
   OR (temp_c     IS NOT NULL AND temp_c     NOT BETWEEN 30 AND 45);
