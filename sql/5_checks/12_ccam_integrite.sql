-- OK si 0 ligne : tout code CCAM de silver.actes est dans silver.ccam,
-- elle-même incluse dans le référentiel bronze (miroir de 08_pathologies).
SELECT 'acte_sans_ccam' AS anomalie, a.code_ccam AS code
FROM silver.actes a
LEFT ANTI JOIN silver.ccam c ON c.code_ccam = a.code_ccam
UNION ALL
SELECT 'ccam_hors_referentiel' AS anomalie, c.code_ccam AS code
FROM silver.ccam c
LEFT ANTI JOIN bronze.ref_ccam r ON r.code_ccam = c.code_ccam;
