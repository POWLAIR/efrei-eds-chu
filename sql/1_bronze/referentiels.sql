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
