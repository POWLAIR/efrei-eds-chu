-- Journal des lignes écartées par les contrôles qualité (traçabilité : on trace ce qu'on écarte).

CREATE TABLE IF NOT EXISTS silver.rejects
(
    source      LowCardinality(String),   -- patients | sejours | monitoring | diagnostics
    natural_key String,                   -- stay_id / patient_hash / ...
    rule        LowCardinality(String),   -- code de la règle violée
    detail      String,
    detected_at DateTime DEFAULT now()
)
ENGINE = MergeTree
ORDER BY (source, rule, detected_at);

TRUNCATE TABLE silver.rejects;
