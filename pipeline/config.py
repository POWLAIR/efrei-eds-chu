"""Configuration du pipeline — lue depuis .env (ou l'environnement)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

load_dotenv(ROOT / ".env")

# Sources attendues dans le filestorage et format de dépôt
SOURCES = ("patients", "sejours", "diagnostics", "monitoring", "referentiels")

# Sources contenant de l'identité patient -> pseudonymisation obligatoire à l'entrée du lake
IDENTIFYING_SOURCES = ("patients", "sejours")


@dataclass(frozen=True)
class Settings:
    ch_host: str = os.getenv("CH_HOST", "localhost")
    ch_http_port: int = int(os.getenv("CH_HTTP_PORT", "8123"))
    ch_user: str = os.getenv("CH_USER", "eds")
    ch_password: str = os.getenv("CH_PASSWORD", "eds")
    ch_database: str = os.getenv("CH_DATABASE", "default")

    pseudo_salt: str = os.getenv("PSEUDO_SALT", "")
    k_anon_min: int = int(os.getenv("K_ANON_MIN", "5"))

    # Users ClickHouse lecture seule (cloisonnement) — utilisés par les connexions Metabase
    ch_ro_pilotage_user: str = os.getenv("CH_RO_PILOTAGE_USER", "ro_pilotage")
    ch_ro_pilotage_password: str = os.getenv("CH_RO_PILOTAGE_PASSWORD", "pilotage")
    ch_ro_recherche_user: str = os.getenv("CH_RO_RECHERCHE_USER", "ro_recherche")
    ch_ro_recherche_password: str = os.getenv("CH_RO_RECHERCHE_PASSWORD", "recherche")

    # Metabase
    mb_url: str = os.getenv("MB_URL", "http://localhost:3000")
    mb_admin_email: str = os.getenv("MB_ADMIN_EMAIL", "admin@chu.local")
    mb_admin_password: str = os.getenv("MB_ADMIN_PASSWORD", "metabaseadmin1")
    mb_admin_first_name: str = os.getenv("MB_ADMIN_FIRST_NAME", "Admin")
    mb_admin_last_name: str = os.getenv("MB_ADMIN_LAST_NAME", "EDS")
    mb_pilotage_user_email: str = os.getenv("MB_PILOTAGE_USER_EMAIL", "pilote@chu.local")
    mb_pilotage_user_password: str = os.getenv("MB_PILOTAGE_USER_PASSWORD", "pilote-demo-1")
    mb_recherche_user_email: str = os.getenv("MB_RECHERCHE_USER_EMAIL", "chercheur@chu.local")
    mb_recherche_user_password: str = os.getenv("MB_RECHERCHE_USER_PASSWORD", "chercheur-demo-1")
    mb_ch_host: str = os.getenv("MB_CH_HOST", "clickhouse")
    mb_ch_port: int = int(os.getenv("MB_CH_PORT", "8123"))

    source_filestorage: Path = ROOT / os.getenv(
        "SOURCE_FILESTORAGE", "data/source-filestorage"
    ).removeprefix("./")
    lake_dir: Path = ROOT / os.getenv("LAKE_DIR", "data/lake").removeprefix("./")
    sql_dir: Path = ROOT / "sql"
    logs_dir: Path = ROOT / "logs"
    dashboards_dir: Path = ROOT / "dashboards"

    def require_salt(self) -> str:
        if not self.pseudo_salt or self.pseudo_salt.startswith("change-me"):
            raise SystemExit(
                "PSEUDO_SALT non défini dans .env — la pseudonymisation RGPD est obligatoire "
                "avant toute écriture dans le lake."
            )
        return self.pseudo_salt


settings = Settings()
