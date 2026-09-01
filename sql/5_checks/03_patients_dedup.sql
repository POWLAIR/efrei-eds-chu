-- OK si 0 ligne : 1 ligne silver.patients par patient distinct du bronze
SELECT
    (SELECT uniqExact(patient_hash) FROM bronze.patients) AS bronze_distinct,
    (SELECT count() FROM silver.patients)                 AS silver_patients
WHERE bronze_distinct != silver_patients;
