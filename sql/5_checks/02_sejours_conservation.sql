-- OK si 0 ligne : tout stay_id de silver.sejours provient bien de bronze.sejours,
-- et aucun stay_id conservé n'a par ailleurs été écarté par un contrôle silver.
SELECT s.stay_id
FROM silver.sejours s
LEFT ANTI JOIN bronze.sejours b ON b.stay_id = s.stay_id
UNION ALL
SELECT s.stay_id
FROM silver.sejours s
WHERE s.stay_id IN (
    SELECT natural_key FROM clean.rejects
    WHERE source = 'sejours'
      AND rule IN ('sortie_avant_admission', 'admission_ts_invalide',
                   'duree_sejour_aberrante', 'service_hors_referentiel')
);
