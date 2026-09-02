-- Silver — diagnostics : on garde tout diagnostic rattaché à un séjour RÉEL
-- (présent dans bronze.sejours) et à un code CIM-10 connu du référentiel.
--
-- Choix (aligné sur la feuille de réponses officielle des KPI recherche) :
--   un séjour peut être écarté de `silver.sejours` pour incohérence TEMPORELLE
--   (discharge_ts < admission_ts) — c'est une erreur de saisie sur les DATES, pas
--   sur le codage. Le diagnostic reste une information clinique valide : le patient
--   est bien porteur de la pathologie. On CONSERVE donc ces diagnostics ici (ils
--   alimentent la prévalence et les cohortes de recherche), tout en les EXCLUANT
--   de `gold.fact_sejour` (durées / DMS) via l'INNER JOIN sur `silver.sejours`.
--   `patient_hash` est récupéré depuis `bronze.sejours` → chaîne patient ↔ pathologie
--   complète même pour ces séjours.
--
-- Les codes conservés ici alimentent silver.pathologies (50_pathologies.sql).

-- CREATE OR REPLACE : la table a gagné `patient_hash` par rapport à la v1 du modèle.
CREATE OR REPLACE TABLE silver.diagnostics
(
    stay_id      String,
    patient_hash String,
    code_cim10   LowCardinality(String),
    type         LowCardinality(String)
)
ENGINE = MergeTree
ORDER BY (stay_id, code_cim10);

INSERT INTO silver.diagnostics
SELECT d.stay_id, b.patient_hash, d.code_cim10, d.type
FROM bronze.diagnostics d
INNER JOIN bronze.sejours b ON b.stay_id = d.stay_id
WHERE d.code_cim10 IN (SELECT code_cim10 FROM bronze.ref_cim10);

-- Traces (journal de quarantaine — étape clean, hors silver)
INSERT INTO clean.rejects (source, natural_key, rule, detail)
SELECT 'diagnostics', d.stay_id, 'sejour_inconnu', d.code_cim10
FROM bronze.diagnostics d
LEFT ANTI JOIN bronze.sejours b ON b.stay_id = d.stay_id;

INSERT INTO clean.rejects (source, natural_key, rule, detail)
SELECT 'diagnostics', d.stay_id, 'code_cim10_hors_referentiel', d.code_cim10
FROM bronze.diagnostics d
WHERE d.code_cim10 NOT IN (SELECT code_cim10 FROM bronze.ref_cim10);
