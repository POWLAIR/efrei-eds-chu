-- Traçabilité & incrémental

-- Historique de chaque exécution du pipeline
CREATE TABLE IF NOT EXISTS meta.runs
(
    run_id        String,
    action        LowCardinality(String),   -- ingest | transform | verify | replay | run-daily
    layer         LowCardinality(String),   -- lake | bronze | clean | silver | gold | all
    business_date Nullable(Date),
    started_at    DateTime,
    finished_at   DateTime,
    status        LowCardinality(String),   -- running | success | error
    error         String
)
ENGINE = MergeTree
ORDER BY (started_at, run_id);

-- Fichiers déjà ingérés dans le lake (idempotence : hash du contenu écrit)
CREATE TABLE IF NOT EXISTS meta.ingested_files
(
    path          String,
    sha256        String,
    source        LowCardinality(String),
    business_date Date,
    rows          UInt64,
    ingested_at   DateTime
)
ENGINE = MergeTree
ORDER BY (source, business_date, sha256);
