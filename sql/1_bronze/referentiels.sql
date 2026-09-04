-- Bronze — référentiels (nomenclatures) : déposés le premier jour uniquement.

CREATE TABLE IF NOT EXISTS bronze.ref_services
(
    service_code  LowCardinality(String),
    service_label String
)
ENGINE = MergeTree ORDER BY service_code;

CREATE TABLE IF NOT EXISTS bronze.ref_cim10
(
    code_cim10 LowCardinality(String),
    libelle    String
)
ENGINE = MergeTree ORDER BY code_cim10;

TRUNCATE TABLE bronze.ref_services;
INSERT INTO bronze.ref_services
SELECT service_code, service_label
FROM file('lake/referentiels/*/services.csv', 'CSVWithNames',
          'service_code String, service_label String');

TRUNCATE TABLE bronze.ref_cim10;
INSERT INTO bronze.ref_cim10
SELECT code_cim10, libelle
FROM file('lake/referentiels/*/cim10.csv', 'CSVWithNames',
          'code_cim10 String, libelle String');

-- --- Évolution (dépôt 2026-08-29) -------------------------------------------

-- Description enrichie des services : catégorie, capacité en lits, pôle.
-- ⚠ ce référentiel peut être INCOMPLET (un service peut ne pas y figurer).
CREATE TABLE IF NOT EXISTS bronze.ref_service_desc
(
    service_code  LowCardinality(String),
    categorie     LowCardinality(String),
    capacite_lits UInt16,
    pole          LowCardinality(String)
)
ENGINE = MergeTree ORDER BY service_code;

TRUNCATE TABLE bronze.ref_service_desc;
INSERT INTO bronze.ref_service_desc
SELECT service_code, categorie, capacite_lits, pole
FROM file('lake/referentiels/*/description_service.csv', 'CSVWithNames',
          'service_code String, categorie String, capacite_lits UInt16, pole String');

-- Nomenclature des actes (CCAM) : libellé + tarif (facturation T2A).
CREATE TABLE IF NOT EXISTS bronze.ref_ccam
(
    code_ccam   LowCardinality(String),
    libelle     String,
    tarif_euros UInt32
)
ENGINE = MergeTree ORDER BY code_ccam;

TRUNCATE TABLE bronze.ref_ccam;
INSERT INTO bronze.ref_ccam
SELECT code_ccam, libelle, tarif_euros
FROM file('lake/referentiels/*/ccam.csv', 'CSVWithNames',
          'code_ccam String, libelle String, tarif_euros UInt32');
