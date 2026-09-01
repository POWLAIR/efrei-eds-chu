-- OK si 0 ligne : aucune incohérence temporelle n'a survécu au nettoyage silver
SELECT stay_id, admission_ts, discharge_ts, los_hours
FROM silver.sejours
WHERE los_hours < 0
   OR (discharge_ts IS NOT NULL AND discharge_ts < admission_ts);
