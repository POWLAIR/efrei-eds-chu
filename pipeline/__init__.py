"""Pipeline ELT médaillon de l'Entrepôt de Données de Santé du CHU.

Python *pilote* uniquement : il recopie les fichiers du filestorage vers le lake
(en pseudonymisant à l'entrée) puis envoie le SQL à ClickHouse. Aucune
transformation métier n'est faite en mémoire (pas de pandas) — tout se passe
dans l'entrepôt, en SQL.
"""

__version__ = "0.1.0"
