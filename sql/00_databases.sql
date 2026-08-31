-- Bases du médaillon + cloisonnement RBAC (RGPD : pilotage ≠ recherche)
-- Idempotent : rejouable sans risque.

CREATE DATABASE IF NOT EXISTS meta;
CREATE DATABASE IF NOT EXISTS bronze;
CREATE DATABASE IF NOT EXISTS silver;
CREATE DATABASE IF NOT EXISTS gold;

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
