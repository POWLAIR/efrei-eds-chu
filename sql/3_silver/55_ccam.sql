-- Silver — ccam : le référentiel des actes matérialisé dans le silver.
--   Ce sont les codes CCAM RÉELLEMENT observés dans silver.actes, avec leur
--   libellé et leur tarif canoniques repris du référentiel bronze.
--   Symétrique de silver.pathologies. Alimente gold.dim_ccam.

CREATE TABLE IF NOT EXISTS silver.ccam
(
    code_ccam   LowCardinality(String),
    libelle     String,
    tarif_euros UInt32
)
ENGINE = MergeTree
ORDER BY code_ccam;

TRUNCATE TABLE silver.ccam;

INSERT INTO silver.ccam
SELECT r.code_ccam, r.libelle, r.tarif_euros
FROM bronze.ref_ccam r
WHERE r.code_ccam IN (SELECT DISTINCT code_ccam FROM silver.actes);
