-- Silver — diagnostics : on ne garde que les diagnostics rattachés à un séjour valide
-- et à un code CIM-10 connu du référentiel.
-- Les codes conservés ici alimentent silver.pathologies (50_pathologies.sql).

CREATE TABLE IF NOT EXISTS silver.diagnostics
(
    stay_id    String,
    code_cim10 LowCardinality(String),
    type       LowCardinality(String)
)
ENGINE = MergeTree
ORDER BY (stay_id, code_cim10);

TRUNCATE TABLE silver.diagnostics;

INSERT INTO silver.diagnostics
SELECT d.stay_id, d.code_cim10, d.type
FROM bronze.diagnostics d
INNER JOIN silver.sejours s ON s.stay_id = d.stay_id
WHERE d.code_cim10 IN (SELECT code_cim10 FROM bronze.ref_cim10);

-- Traces (journal de quarantaine — étape clean, hors silver)
INSERT INTO clean.rejects (source, natural_key, rule, detail)
SELECT 'diagnostics', d.stay_id, 'sejour_inconnu', d.code_cim10
FROM bronze.diagnostics d
LEFT ANTI JOIN silver.sejours s ON s.stay_id = d.stay_id;

INSERT INTO clean.rejects (source, natural_key, rule, detail)
SELECT 'diagnostics', d.stay_id, 'code_cim10_hors_referentiel', d.code_cim10
FROM bronze.diagnostics d
WHERE d.code_cim10 NOT IN (SELECT code_cim10 FROM bronze.ref_cim10);
