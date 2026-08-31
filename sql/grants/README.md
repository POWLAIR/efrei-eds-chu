# Cloisonnement RBAC

Les GRANT sont définis dans [`../00_databases.sql`](../00_databases.sql) et rejoués
par `make init-db`.

- `role_pilotage` → `SELECT` sur `gold.kpi_pilotage_*` uniquement
- `role_recherche` → `SELECT` sur `gold.kpi_recherche_*` uniquement (k-anonymat déjà dans la vue)
- `ro_pilotage`, `ro_recherche` : users lecture seule, un par public, utilisés par Metabase

Vérifier :

```sql
SHOW GRANTS FOR ro_pilotage;
SHOW GRANTS FOR ro_recherche;
```

Test négatif (doit échouer avec « Not enough privileges ») :

```bash
docker exec -it eds-clickhouse clickhouse-client -u ro_recherche --password recherche \
  --query "SELECT * FROM gold.kpi_pilotage_dms"
```
