-- Silver — services : le référentiel des services promu en silver et ENRICHI
-- par la description (catégorie, capacité en lits, pôle) — évolution 2026-08-29.
--
-- Liste autoritaire = `bronze.ref_services` (8 services). La description
-- (`bronze.ref_service_desc`) est jointe en LEFT JOIN : un service non décrit
-- (ici NEURO) est CONSERVÉ, marqué `is_described = 0`, avec `categorie` / `pole`
-- à '(non décrit)' et `capacite_lits` à NULL. Choix : on ne perd aucun service
-- d'une analyse « par catégorie / par pôle » ; le trou est explicite et tracé.
--
-- Alimente gold.dim_service (enrichie). Symétrique de silver.pathologies.

CREATE TABLE IF NOT EXISTS silver.services
(
    service_code  LowCardinality(String),
    service_label String,
    categorie     LowCardinality(String),
    capacite_lits Nullable(UInt16),
    pole          LowCardinality(String),
    is_described  UInt8
)
ENGINE = MergeTree
ORDER BY service_code;

TRUNCATE TABLE silver.services;

INSERT INTO silver.services
SELECT
    s.service_code,
    s.service_label,
    if(d.service_code = '', '(non décrit)', d.categorie)  AS categorie,
    if(d.service_code = '', NULL, d.capacite_lits)        AS capacite_lits,
    if(d.service_code = '', '(non décrit)', d.pole)       AS pole,
    d.service_code != ''                                  AS is_described
FROM bronze.ref_services s
LEFT JOIN bronze.ref_service_desc d ON d.service_code = s.service_code;

-- Trace (journal de quarantaine — audit, PAS une exclusion)
INSERT INTO clean.rejects (source, natural_key, rule, detail)
SELECT 'referentiels', service_code, 'service_sans_description',
       'service absent de description_service.csv — conservé, catégorie/pôle « (non décrit) »'
FROM silver.services
WHERE is_described = 0;
