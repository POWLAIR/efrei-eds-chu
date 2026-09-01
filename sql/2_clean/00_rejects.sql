-- Étape « clean » — journal de quarantaine : lignes écartées par les contrôles qualité.
-- Artefact OPÉRATIONNEL (audit / traçabilité), hors base analytique silver.
-- La couche clean *possède* cette table ; les transformations silver l'alimentent
-- au fil de leur filtrage (INSERT INTO clean.rejects dans sql/silver/*.sql).

CREATE DATABASE IF NOT EXISTS clean;
CREATE DATABASE IF NOT EXISTS silver;     -- garde-fou avant le DROP de migration
DROP TABLE IF EXISTS silver.rejects;      -- migration : l'ancienne table quitte silver

CREATE TABLE IF NOT EXISTS clean.rejects
(
    source      LowCardinality(String),   -- patients | sejours | monitoring | diagnostics
    natural_key String,                   -- stay_id / patient_hash / ...
    rule        LowCardinality(String),   -- code de la règle violée
    detail      String,
    detected_at DateTime DEFAULT now()
)
ENGINE = MergeTree
ORDER BY (source, rule, detected_at);

-- Rebuild complet à chaque `transform` (cohérent avec les autres tables ; un journal
-- append-only avec run_id serait une évolution possible — cf. dossier § 5).
TRUNCATE TABLE clean.rejects;
