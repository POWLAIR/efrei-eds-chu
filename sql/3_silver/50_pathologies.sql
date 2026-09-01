-- Silver — pathologies : le référentiel CIM-10 matérialisé dans le silver.
--   « De diagnostics en découle une table pathologies » : on ne garde que les codes
--   CIM-10 réellement observés dans silver.diagnostics, avec leur libellé canonique
--   repris du référentiel bronze (source de vérité).
--   Chaîne : patients -> sejours -> diagnostics -> pathologies.
--   Alimente gold.dim_cim10.

CREATE TABLE IF NOT EXISTS silver.pathologies
(
    code_cim10 LowCardinality(String),
    libelle    String
)
ENGINE = MergeTree
ORDER BY code_cim10;

TRUNCATE TABLE silver.pathologies;

INSERT INTO silver.pathologies
SELECT r.code_cim10, r.libelle
FROM bronze.ref_cim10 r
WHERE r.code_cim10 IN (SELECT DISTINCT code_cim10 FROM silver.diagnostics);
