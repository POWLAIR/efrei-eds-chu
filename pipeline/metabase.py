"""Provisioning Metabase via l'API REST — idempotent.

`uv run eds dashboards` :
  - crée le compte admin au 1er lancement
  - crée 2 connexions ClickHouse cloisonnées (ro_pilotage / ro_recherche)
  - crée 2 groupes + permissions de données (chaque groupe ne voit que SA base)
  - crée 1 utilisateur de démo par groupe
  - crée 2 collections + 2 dashboards (6 cartes SQL natives sur les vues gold)
  - exporte les dashboards dans dashboards/*.json

Toutes les opérations sont « find-or-create » : relancer ne duplique rien.
"""

from __future__ import annotations

import contextlib
import json
import time
from typing import Any

import httpx

from pipeline.config import settings
from pipeline.logging_conf import get_logger

log = get_logger("eds.metabase")

DB_PILOTAGE = "EDS — Pilotage"
DB_RECHERCHE = "EDS — Recherche"
GROUP_PILOTAGE = "Pilotage"
GROUP_RECHERCHE = "Recherche"

# --- Définition des cartes -----------------------------------------------------
# (nom, base, requête SQL sur la vue gold, type de graphe, visualization_settings)
CARDS: list[dict[str, Any]] = [
    {
        "name": "DMS par service (jours)",
        "db": DB_PILOTAGE,
        "sql": "SELECT service_label, dms_jours FROM gold.kpi_pilotage_dms ORDER BY dms_jours DESC",
        "display": "bar",
        "viz": {"graph.dimensions": ["service_label"], "graph.metrics": ["dms_jours"]},
    },
    {
        "name": "Passages aux urgences par jour",
        "db": DB_PILOTAGE,
        "sql": (
            "SELECT jour, passages_urgence, admissions_totales "
            "FROM gold.kpi_pilotage_urgences_jour ORDER BY jour"
        ),
        "display": "line",
        "viz": {
            "graph.dimensions": ["jour"],
            "graph.metrics": ["passages_urgence", "admissions_totales"],
        },
    },
    {
        "name": "Taux de réadmission à 30 jours (%)",
        "db": DB_PILOTAGE,
        "sql": "SELECT taux_pct FROM gold.kpi_pilotage_readmission_30j",
        "display": "scalar",
        "viz": {},
    },
    {
        "name": "Relevés de constantes en alerte par jour",
        "db": DB_PILOTAGE,
        "sql": (
            "SELECT jour, alertes_fc, alertes_spo2, alertes_temp "
            "FROM gold.kpi_pilotage_alertes_constantes ORDER BY jour"
        ),
        "display": "bar",
        "viz": {
            "graph.dimensions": ["jour"],
            "graph.metrics": ["alertes_fc", "alertes_spo2", "alertes_temp"],
            "stackable.stack_type": "stacked",
        },
    },
    {
        "name": "Charge par service (patients-jours)",
        "db": DB_PILOTAGE,
        "sql": (
            "SELECT service_label, admissions, patients_jours "
            "FROM gold.kpi_pilotage_charge_service ORDER BY patients_jours DESC"
        ),
        "display": "bar",
        "viz": {"graph.dimensions": ["service_label"], "graph.metrics": ["patients_jours"]},
    },
    {
        "name": "Répartition des modes de sortie",
        "db": DB_PILOTAGE,
        "sql": "SELECT mode_sortie, nb_sejours FROM gold.kpi_pilotage_mode_sortie ORDER BY nb_sejours DESC",
        "display": "pie",
        "viz": {"pie.dimension": "mode_sortie", "pie.metric": "nb_sejours"},
    },
    {
        "name": "Prévalence par pathologie (cohortes ≥ 5)",
        "db": DB_RECHERCHE,
        "sql": (
            "SELECT libelle, cohorte_patients FROM gold.kpi_recherche_prevalence "
            "ORDER BY cohorte_patients DESC LIMIT 15"
        ),
        "display": "row",
        "viz": {"graph.dimensions": ["libelle"], "graph.metrics": ["cohorte_patients"]},
    },
    {
        "name": "Description de cohorte : âge × sexe",
        "db": DB_RECHERCHE,
        "sql": (
            "SELECT age_band, sex, nb_patients FROM gold.kpi_recherche_cohorte_age_sexe "
            "ORDER BY age_band, sex"
        ),
        "display": "bar",
        "viz": {"graph.dimensions": ["age_band", "sex"], "graph.metrics": ["nb_patients"]},
    },
]

DASHBOARDS = [
    ("Pilotage hospitalier", GROUP_PILOTAGE, [c["name"] for c in CARDS if c["db"] == DB_PILOTAGE]),
    ("Recherche clinique", GROUP_RECHERCHE, [c["name"] for c in CARDS if c["db"] == DB_RECHERCHE]),
]


# --- Client HTTP -------------------------------------------------------------
class MB:
    def __init__(self) -> None:
        self.base = settings.mb_url.rstrip("/")
        self.http = httpx.Client(base_url=self.base, timeout=60.0)
        self.session: str | None = None

    def _headers(self) -> dict[str, str]:
        return {"X-Metabase-Session": self.session} if self.session else {}

    def req(self, method: str, path: str, **kw: Any) -> Any:
        r = self.http.request(method, path, headers=self._headers(), **kw)
        if r.status_code >= 300:
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:400]}")
        if r.headers.get("content-type", "").startswith("application/json"):
            return r.json()
        return r.text

    def get(self, path: str, **kw: Any) -> Any:
        return self.req("GET", path, **kw)

    def post(self, path: str, body: Any) -> Any:
        return self.req("POST", path, json=body)

    def put(self, path: str, body: Any) -> Any:
        return self.req("PUT", path, json=body)

    @staticmethod
    def rows(payload: Any) -> list[dict]:
        """Tolère les réponses `[...]` et `{"data": [...]}`."""
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload


# --- Étapes ------------------------------------------------------------------
def wait_ready(mb: MB, timeout: int = 240) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with contextlib.suppress(Exception):
            if mb.get("/api/health").get("status") == "ok":
                log.info("Metabase prêt")
                return
        time.sleep(3)
    raise RuntimeError("Metabase n'a pas démarré à temps")


def bootstrap_session(mb: MB) -> None:
    props = mb.get("/api/session/properties")
    if not props.get("has-user-setup"):
        token = props["setup-token"]
        log.info("1er lancement : création du compte admin %s", settings.mb_admin_email)
        res = mb.post(
            "/api/setup",
            {
                "token": token,
                "user": {
                    "first_name": settings.mb_admin_first_name,
                    "last_name": settings.mb_admin_last_name,
                    "email": settings.mb_admin_email,
                    "password": settings.mb_admin_password,
                    "site_name": "EDS CHU",
                },
                "prefs": {"site_name": "EDS CHU", "allow_tracking": False},
            },
        )
        mb.session = res["id"]
    else:
        res = mb.post(
            "/api/session",
            {"username": settings.mb_admin_email, "password": settings.mb_admin_password},
        )
        mb.session = res["id"]
    log.info("session ouverte")


def ensure_database(mb: MB, name: str, ch_user: str, ch_password: str) -> int:
    for db in mb.rows(mb.get("/api/database")):
        if db["name"] == name:
            log.info("DB '%s' existe (id=%s)", name, db["id"])
            return db["id"]
    body = {
        "name": name,
        "engine": "clickhouse",
        "details": {
            "host": settings.mb_ch_host,
            "port": settings.mb_ch_port,
            "user": ch_user,
            "password": ch_password,
            "dbname": "gold",
            "scan-all-databases": False,
            "ssl": False,
        },
    }
    db = mb.post("/api/database", body)
    log.info("DB '%s' créée (id=%s) — synchronisation…", name, db["id"])
    _wait_sync(mb, db["id"])
    return db["id"]


def _wait_sync(mb: MB, db_id: int, timeout: int = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        db = mb.get(f"/api/database/{db_id}")
        if db.get("initial_sync_status") == "complete":
            meta = mb.get(f"/api/database/{db_id}/metadata")
            tables = [t["name"] for t in meta.get("tables", [])]
            log.info("  sync OK — tables vues : %s", tables)
            return
        time.sleep(3)
    log.warning("  sync non terminée (on continue)")


def ensure_group(mb: MB, name: str) -> int:
    for g in mb.get("/api/permissions/group"):
        if g["name"] == name:
            return g["id"]
    g = mb.post("/api/permissions/group", {"name": name})
    log.info("groupe '%s' créé (id=%s)", name, g["id"])
    return g["id"]


def set_data_permissions(mb: MB, mapping: dict[int, int]) -> None:
    """mapping = {group_id: db_id_autorisée}.

    Metabase OSS ne propose pas le blocage fin de « view data » (feature EE). On agit
    donc sur `create-queries` : chaque groupe peut interroger SA base (builder + SQL),
    pas l'autre ; « All Users » n'interroge aucune des deux. Le vrai cloisonnement
    physique est porté par le RBAC ClickHouse (`ro_pilotage` / `ro_recherche`) + les
    permissions de collections.
    """
    GRANT = {"view-data": "unrestricted", "create-queries": "query-builder-and-native"}
    DENY = {"view-data": "unrestricted", "create-queries": "no"}
    all_eds_dbs = set(mapping.values())

    graph = mb.get("/api/permissions/graph")
    groups = graph["groups"]

    for gid, allowed_db in mapping.items():
        gperm = groups.setdefault(str(gid), {})
        for db_id in all_eds_dbs:
            gperm[str(db_id)] = dict(GRANT if db_id == allowed_db else DENY)

    au = groups.setdefault("1", {})  # "All Users"
    for db_id in all_eds_dbs:
        au[str(db_id)] = dict(DENY)

    mb.put("/api/permissions/graph", {"revision": graph["revision"], "groups": groups})
    log.info("permissions de données appliquées (create-queries cloisonné par groupe)")


def ensure_user(mb: MB, email: str, password: str, group_id: int) -> int:
    uid = None
    for u in mb.rows(mb.get("/api/user", params={"include_deactivated": "true"})):
        if u["email"] == email:
            uid = u["id"]
            break
    if uid is None:
        u = mb.post(
            "/api/user",
            {
                "first_name": email.split("@")[0].capitalize(),
                "last_name": "EDS",
                "email": email,
                "password": password,
            },
        )
        uid = u["id"]
        log.info("utilisateur '%s' créé (id=%s)", email, uid)

    # /api/permissions/membership est indexé par user_id
    memberships = mb.get("/api/permissions/membership")
    already = any(m["group_id"] == group_id for m in memberships.get(str(uid), []))
    if not already:
        mb.post("/api/permissions/membership", {"group_id": group_id, "user_id": uid})
        log.info("  '%s' ajouté au groupe %s", email, group_id)
    return uid


def ensure_collection(mb: MB, name: str) -> int:
    for c in mb.rows(mb.get("/api/collection")):
        if c.get("name") == name and not c.get("archived"):
            return c["id"]
    c = mb.post("/api/collection", {"name": name, "parent_id": None})
    log.info("collection '%s' créée (id=%s)", name, c["id"])
    return c["id"]


def restrict_collection(mb: MB, coll_id: int, owner_group_id: int, all_group_ids: list[int]) -> None:
    """Seul le groupe propriétaire voit la collection (les Admins gardent tout accès)."""
    graph = mb.get("/api/collection/graph")
    groups = graph["groups"]
    for gid in all_group_ids:
        if gid == 2:  # Administrators
            continue
        perm = "read" if gid == owner_group_id else "none"
        groups.setdefault(str(gid), {})[str(coll_id)] = perm
    mb.put("/api/collection/graph", {"revision": graph["revision"], "groups": groups})
    log.info("collection %s : lecture réservée au groupe %s", coll_id, owner_group_id)


def cleanup_defaults(mb: MB) -> None:
    """Retire le bruit par défaut (base d'exemple, collection Examples) des vues utilisateurs."""
    for db in mb.rows(mb.get("/api/database")):
        if db.get("is_sample"):
            with contextlib.suppress(Exception):
                mb.req("DELETE", f"/api/database/{db['id']}")
                log.info("base d'exemple supprimée")
    for c in mb.rows(mb.get("/api/collection")):
        if c.get("name") == "Examples" and not c.get("archived"):
            with contextlib.suppress(Exception):
                mb.put(f"/api/collection/{c['id']}", {"archived": True})
                log.info("collection 'Examples' archivée")


def ensure_card(mb: MB, spec: dict, db_ids: dict[str, int], coll_ids: dict[str, int]) -> int:
    existing = {c["name"]: c["id"] for c in mb.rows(mb.get("/api/card"))}
    if spec["name"] in existing:
        return existing[spec["name"]]
    coll_name = GROUP_PILOTAGE if spec["db"] == DB_PILOTAGE else GROUP_RECHERCHE
    body = {
        "name": spec["name"],
        "display": spec["display"],
        "visualization_settings": spec["viz"],
        "collection_id": coll_ids[coll_name],
        "dataset_query": {
            "type": "native",
            "native": {"query": spec["sql"], "template-tags": {}},
            "database": db_ids[spec["db"]],
        },
    }
    card = mb.post("/api/card", body)
    log.info("carte '%s' créée (id=%s)", spec["name"], card["id"])
    return card["id"]


def ensure_dashboard(mb: MB, name: str, coll_id: int, card_ids: list[int]) -> int:
    dash_id = None
    for d in mb.rows(mb.get("/api/dashboard")):
        if d.get("name") == name and not d.get("archived"):
            dash_id = d["id"]
            break
    if dash_id is None:
        dash_id = mb.post("/api/dashboard", {"name": name, "collection_id": coll_id})["id"]
        created = True
    else:
        created = False

    # État courant des cartes du dashboard (pour rester idempotent)
    dash = mb.get(f"/api/dashboard/{dash_id}")
    existing = {dc.get("card_id"): dc for dc in dash.get("dashcards", [])}
    if not created and set(existing) >= set(card_ids):
        log.info("dashboard '%s' existe (id=%s, à jour)", name, dash_id)
        return dash_id

    dashcards = []
    for i, cid in enumerate(card_ids):
        prev = existing.get(cid, {})
        dashcards.append(
            {
                "id": prev.get("id", -(i + 1)),
                "card_id": cid,
                "row": prev.get("row", (i // 2) * 8),
                "col": prev.get("col", (i % 2) * 12),
                "size_x": prev.get("size_x", 12),
                "size_y": prev.get("size_y", 8),
                "parameter_mappings": [],
                "visualization_settings": {},
            }
        )
    mb.put(f"/api/dashboard/{dash_id}", {"dashcards": dashcards})
    log.info("dashboard '%s' %s (id=%s, %d cartes)", name,
             "créé" if created else "mis à jour", dash_id, len(card_ids))
    return dash_id


def export_dashboard(mb: MB, dash_id: int, filename: str) -> None:
    dash = mb.get(f"/api/dashboard/{dash_id}")
    out = settings.dashboards_dir / filename
    out.write_text(json.dumps(dash, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("export -> %s", out)


# --- Orchestration ---------------------------------------------------------
def provision(export: bool = True) -> None:
    mb = MB()
    wait_ready(mb)
    bootstrap_session(mb)

    db_ids = {
        DB_PILOTAGE: ensure_database(
            mb, DB_PILOTAGE, settings.ch_ro_pilotage_user, settings.ch_ro_pilotage_password
        ),
        DB_RECHERCHE: ensure_database(
            mb, DB_RECHERCHE, settings.ch_ro_recherche_user, settings.ch_ro_recherche_password
        ),
    }

    gid_pilotage = ensure_group(mb, GROUP_PILOTAGE)
    gid_recherche = ensure_group(mb, GROUP_RECHERCHE)
    set_data_permissions(
        mb, {gid_pilotage: db_ids[DB_PILOTAGE], gid_recherche: db_ids[DB_RECHERCHE]}
    )

    ensure_user(
        mb, settings.mb_pilotage_user_email, settings.mb_pilotage_user_password, gid_pilotage
    )
    ensure_user(
        mb, settings.mb_recherche_user_email, settings.mb_recherche_user_password, gid_recherche
    )

    all_gids = [g["id"] for g in mb.get("/api/permissions/group")]
    coll_ids = {
        GROUP_PILOTAGE: ensure_collection(mb, GROUP_PILOTAGE),
        GROUP_RECHERCHE: ensure_collection(mb, GROUP_RECHERCHE),
    }
    restrict_collection(mb, coll_ids[GROUP_PILOTAGE], gid_pilotage, all_gids)
    restrict_collection(mb, coll_ids[GROUP_RECHERCHE], gid_recherche, all_gids)

    card_ids = {spec["name"]: ensure_card(mb, spec, db_ids, coll_ids) for spec in CARDS}

    dash_ids = {}
    for name, group, card_names in DASHBOARDS:
        dash_ids[group] = ensure_dashboard(
            mb, name, coll_ids[group], [card_ids[n] for n in card_names]
        )

    cleanup_defaults(mb)

    if export:
        export_dashboard(mb, dash_ids[GROUP_PILOTAGE], "pilotage.json")
        export_dashboard(mb, dash_ids[GROUP_RECHERCHE], "recherche.json")

    log.info("✓ Metabase provisionné — %s", settings.mb_url)
