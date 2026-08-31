-- Bronze — diagnostics : JSON imbriqué [{stay_id, diagnostics:[{code_cim10, type}]}]
-- JSONAsString rend 1 ligne par objet du tableau ; on aplatit ensuite le sous-tableau
-- `diagnostics` avec ARRAY JOIN. 1 ligne finale = 1 (stay_id, code_cim10, type).

CREATE TABLE IF NOT EXISTS bronze.diagnostics
(
    stay_id    String,
    code_cim10 LowCardinality(String),
    type       LowCardinality(String)   -- principal | associe
)
ENGINE = MergeTree
ORDER BY (stay_id, code_cim10);

TRUNCATE TABLE bronze.diagnostics;

INSERT INTO bronze.diagnostics
SELECT
    JSONExtractString(raw, 'stay_id')     AS stay_id,
    JSONExtractString(diag, 'code_cim10') AS code_cim10,
    JSONExtractString(diag, 'type')       AS type
FROM file('lake/diagnostics/*/diagnostics.json', 'JSONAsString', 'raw String')
ARRAY JOIN JSONExtractArrayRaw(raw, 'diagnostics') AS diag;
