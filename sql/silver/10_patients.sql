-- Silver — patients : déduplication (garder la version la plus récente),
-- normalisation du sexe, contrôle de l'année de naissance.

CREATE TABLE IF NOT EXISTS silver.patients
(
    patient_hash String,
    birth_year   Nullable(UInt16),           -- NULL si absente ou aberrante
    sex          LowCardinality(String),     -- M | F | (vide si non normalisable)
    region_code  LowCardinality(String)
)
ENGINE = MergeTree
ORDER BY patient_hash;

TRUNCATE TABLE silver.patients;

-- 1 ligne par patient : on prend la valeur du dépôt le plus récent (business_date).
INSERT INTO silver.patients
WITH dedup AS
(
    SELECT
        patient_hash,
        argMax(birth_year, business_date)  AS birth_year_raw,
        argMax(
            multiIf(upper(sex) IN ('M', 'F'),            upper(sex),
                    upper(sex) IN ('H', 'HOMME', 'MALE'), 'M',
                    upper(sex) IN ('FEMME', 'FEMALE'),    'F',
                    ''),
            business_date)                  AS sex,
        argMax(region_code, business_date)  AS region_code
    FROM bronze.patients
    GROUP BY patient_hash
)
SELECT
    patient_hash,
    -- année de naissance plausible uniquement (sinon NULL -> cohorte "âge inconnu")
    if(birth_year_raw BETWEEN 1900 AND toYear(now()), birth_year_raw, NULL) AS birth_year,
    sex,
    region_code
FROM dedup;

-- Traces (journal de quarantaine — étape clean, hors silver)
INSERT INTO clean.rejects (source, natural_key, rule, detail)
SELECT 'patients', patient_hash, 'sex_non_normalise', 'sexe vide après normalisation'
FROM silver.patients WHERE sex = '';

INSERT INTO clean.rejects (source, natural_key, rule, detail)
SELECT 'patients', patient_hash, 'birth_year_aberrant', concat('birth_year=', toString(birth_year_raw))
FROM
(
    SELECT patient_hash, argMax(birth_year, business_date) AS birth_year_raw
    FROM bronze.patients GROUP BY patient_hash
)
WHERE birth_year_raw IS NOT NULL AND birth_year_raw NOT BETWEEN 1900 AND toYear(now());
