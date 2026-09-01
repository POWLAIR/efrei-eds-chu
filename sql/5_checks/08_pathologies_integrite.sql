-- OK si 0 ligne : intégrité de la chaîne diagnostics -> pathologies -> référentiel.
--   * tout code_cim10 de silver.diagnostics est présent dans silver.pathologies ;
--   * silver.pathologies est inclus dans le référentiel CIM-10 bronze.
SELECT 'diag_sans_patho' AS anomalie, d.code_cim10 AS code
FROM silver.diagnostics d
LEFT ANTI JOIN silver.pathologies p ON p.code_cim10 = d.code_cim10
UNION ALL
SELECT 'patho_hors_referentiel' AS anomalie, p.code_cim10 AS code
FROM silver.pathologies p
LEFT ANTI JOIN bronze.ref_cim10 r ON r.code_cim10 = p.code_cim10;
