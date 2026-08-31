#!/usr/bin/env bash
# Dézippe le dépôt quotidien du CHU dans data/source-filestorage/
# (simule l'espace de stockage en lecture seule où le CHU dépose ses fichiers)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ZIP="$ROOT/docs/eds-chu-sujet.zip"
DEST="$ROOT/data/source-filestorage"

[[ -f "$ZIP" ]] || { echo "Introuvable : $ZIP" >&2; exit 1; }

mkdir -p "$DEST"
find "$DEST" -type f -exec chmod u+w {} + 2>/dev/null || true   # réinscriptible si déjà seedé
# Le zip contient source-filestorage/... -> on extrait à la racine de data/
unzip -o "$ZIP" 'source-filestorage/*' -d "$ROOT/data" >/dev/null

# Lecture seule : on ne peut que lire ce que le CHU dépose (fichiers seulement,
# pour garder les dossiers manipulables : make nuke / rm)
find "$DEST" -type f -exec chmod a-w {} + 2>/dev/null || true

echo "Dépôt CHU prêt dans : $DEST"
find "$DEST" -maxdepth 2 -type d | sort
