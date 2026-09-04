-- Bronze — actes : flux de faits ajouté par l'évolution (dépôt 2026-08-29).
-- Parquet, lu nativement. 1 ligne = 1 acte médical (CCAM) réalisé pendant un séjour.
-- Comme le monitoring, partitionné par jour d'acte (le flux grossira).

CREATE TABLE IF NOT EXISTS bronze.actes
(
    stay_id   String,
    code_ccam LowCardinality(String),
    acte_ts   DateTime
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(acte_ts)
ORDER BY (stay_id, acte_ts);

TRUNCATE TABLE bronze.actes;

INSERT INTO bronze.actes
SELECT
    stay_id,
    code_ccam,
    toDateTime(acte_ts) AS acte_ts
FROM file('lake/actes/*/actes.parquet', 'Parquet');
