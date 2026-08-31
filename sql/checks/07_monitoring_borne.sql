-- OK si 0 ligne : aucune constante hors plage physiologique n'a survécu en silver
SELECT stay_id, ts, heart_rate, spo2, temp_c
FROM silver.monitoring
WHERE (heart_rate IS NOT NULL AND heart_rate NOT BETWEEN 20 AND 250)
   OR (spo2       IS NOT NULL AND spo2       NOT BETWEEN 50 AND 100)
   OR (temp_c     IS NOT NULL AND temp_c     NOT BETWEEN 30 AND 45);
