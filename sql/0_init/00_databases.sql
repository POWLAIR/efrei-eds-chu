-- Bases du médaillon + cloisonnement RBAC (RGPD : pilotage ≠ recherche)
-- Idempotent : rejouable sans risque. Rejoué par `make init-db`.
--
-- Cloisonnement (le vrai, physique — cf. dossier § 9) :
--   role_pilotage  -> SELECT sur gold.kpi_pilotage_*  uniquement
--   role_recherche -> SELECT sur gold.kpi_recherche_* uniquement (k-anonymat déjà dans la vue)
--   ro_pilotage / ro_recherche : users lecture seule, un par public, utilisés par Metabase
--
-- Vérifier :  SHOW GRANTS FOR ro_pilotage;   SHOW GRANTS FOR ro_recherche;
-- Test négatif (doit échouer « Not enough privileges ») :
--   docker exec -it eds-clickhouse clickhouse-client -u ro_recherche --password recherche \
--     --query "SELECT * FROM gold.kpi_pilotage_dms"

CREATE DATABASE IF NOT EXISTS meta;
CREATE DATABASE IF NOT EXISTS bronze;
CREATE DATABASE IF NOT EXISTS clean;    -- étape de nettoyage : journal de quarantaine (clean.rejects)
CREATE DATABASE IF NOT EXISTS silver;
CREATE DATABASE IF NOT EXISTS gold;

-- `clean` n'a ni rôle ni GRANT : artefact opérationnel d'audit, aucun consommateur
-- Metabase / RBAC. Seul l'utilisateur `eds` (admin) y accède.

-- --- Utilisateurs lecture seule, un par public --------------------------------
CREATE USER IF NOT EXISTS ro_pilotage  IDENTIFIED WITH plaintext_password BY 'pilotage';
CREATE USER IF NOT EXISTS ro_recherche IDENTIFIED WITH plaintext_password BY 'recherche';

CREATE ROLE IF NOT EXISTS role_pilotage;
CREATE ROLE IF NOT EXISTS role_recherche;

-- Pilotage : accès aux marts de pilotage uniquement
GRANT SELECT ON gold.kpi_pilotage_dms                  TO role_pilotage;
GRANT SELECT ON gold.kpi_pilotage_urgences_jour        TO role_pilotage;
GRANT SELECT ON gold.kpi_pilotage_readmission_30j      TO role_pilotage;
GRANT SELECT ON gold.kpi_pilotage_alertes_constantes   TO role_pilotage;
GRANT SELECT ON gold.kpi_pilotage_mode_sortie          TO role_pilotage;
GRANT SELECT ON gold.kpi_pilotage_charge_service       TO role_pilotage;

-- Recherche : accès aux vues recherche (k-anonymat déjà appliqué dans la vue)
GRANT SELECT ON gold.kpi_recherche_prevalence          TO role_recherche;
GRANT SELECT ON gold.kpi_recherche_cohorte_age_sexe    TO role_recherche;

GRANT role_pilotage  TO ro_pilotage;
GRANT role_recherche TO ro_recherche;
