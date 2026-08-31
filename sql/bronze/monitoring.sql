-- Bronze — monitoring : flux volumineux (constantes au chevet). Parquet, lu nativement.
-- Partitionné par jour : le partition pruning limite la lecture aux jours utiles.

CREATE TABLE IF NOT EXISTS bronze.monitoring
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

TRUNCATE TABLE bronze.monitoring;

INSERT INTO bronze.monitoring
SELECT
    stay_id,
    toDateTime(ts)        AS ts,
    toInt32OrNull(toString(heart_rate)) AS heart_rate,
    toInt32OrNull(toString(spo2))       AS spo2,
    toFloat32OrNull(toString(temp_c))   AS temp_c
FROM file('lake/monitoring/*/monitoring.parquet', 'Parquet');
