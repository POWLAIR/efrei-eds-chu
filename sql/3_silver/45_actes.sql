-- Silver — actes : flux de faits « actes médicaux » (CCAM) — évolution 2026-08-29.
--
-- ⚠ Piège du sujet : « nb d'actes PAR SERVICE » — le service est porté par le
-- SÉJOUR, pas par l'acte. On le résout ICI, une seule fois, par jointure
-- `bronze.actes → bronze.sejours`. `gold.fact_acte` héritera de ce `service_code`
-- dénormalisé → AUCUNE vue gold ne reliera deux tables de faits entre elles.
--
-- Rétention (même principe que silver.diagnostics) : un acte porté par un séjour
-- écarté de `silver.sejours` pour incohérence de DATES reste un acte réel et
-- facturable — le codage du service est valide. On le CONSERVE (service_code et
-- patient_hash pris dans `bronze.sejours`). On n'écarte que :
--   * l'acte dont le `stay_id` est TOTALEMENT inconnu (absent de bronze.sejours)
--   * l'acte dont le `code_ccam` est hors référentiel

CREATE TABLE IF NOT EXISTS silver.actes
(
    stay_id      String,
    patient_hash String,
    service_code LowCardinality(String),
    code_ccam    LowCardinality(String),
    acte_ts      DateTime,
    acte_date    Date
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(acte_date)
ORDER BY (service_code, acte_date, stay_id);

TRUNCATE TABLE silver.actes;

INSERT INTO silver.actes
SELECT
    a.stay_id,
    b.patient_hash,
    b.service_code,
    a.code_ccam,
    a.acte_ts,
    toDate(a.acte_ts) AS acte_date
FROM bronze.actes a
INNER JOIN bronze.sejours b ON b.stay_id = a.stay_id
WHERE a.code_ccam IN (SELECT code_ccam FROM bronze.ref_ccam);

-- Traces (journal de quarantaine — étape clean, hors silver)
INSERT INTO clean.rejects (source, natural_key, rule, detail)
SELECT 'actes', a.stay_id, 'sejour_inconnu', a.code_ccam
FROM bronze.actes a
LEFT ANTI JOIN bronze.sejours b ON b.stay_id = a.stay_id;

INSERT INTO clean.rejects (source, natural_key, rule, detail)
SELECT 'actes', a.stay_id, 'code_ccam_hors_referentiel', a.code_ccam
FROM bronze.actes a
WHERE a.code_ccam NOT IN (SELECT code_ccam FROM bronze.ref_ccam);
