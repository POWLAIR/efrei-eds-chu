-- Gold — fait « actes » : 1 ligne = 1 acte médical valide, avec ses axes et sa mesure.
--   * service_code : porté par le SÉJOUR, résolu en amont dans silver.actes
--     (aucune jointure fact_acte ↔ fact_sejour dans les KPI).
--   * tarif_euros  : mesure dénormalisée depuis dim_ccam (montant facturé T2A).

CREATE TABLE IF NOT EXISTS gold.fact_acte
(
    stay_id      String,
    patient_hash String,
    service_code LowCardinality(String),
    acte_date    Date,
    acte_ts      DateTime,
    code_ccam    LowCardinality(String),
    tarif_euros  UInt32
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(acte_date)
ORDER BY (service_code, acte_date, stay_id);

TRUNCATE TABLE gold.fact_acte;

INSERT INTO gold.fact_acte
SELECT
    a.stay_id,
    a.patient_hash,
    a.service_code,
    a.acte_date,
    a.acte_ts,
    a.code_ccam,
    c.tarif_euros
FROM silver.actes a
LEFT JOIN gold.dim_ccam c ON c.code_ccam = a.code_ccam;
