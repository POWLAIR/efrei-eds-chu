-- OK si 0 ligne : le service d'un acte = le service de SON séjour (piège du sujet :
-- le service est porté par le séjour, jamais par l'acte).
SELECT a.stay_id, a.service_code AS service_acte, f.service_code AS service_sejour
FROM gold.fact_acte a
INNER JOIN gold.fact_sejour f ON f.stay_id = a.stay_id
WHERE a.service_code != f.service_code;
