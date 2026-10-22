#!/usr/bin/env bash
# Church Notes site — local build (staged). Currently builds to ./site only.
# No GitHub push / DNS yet. Enable the git block once a repo + host are chosen.
set -euo pipefail

SITE=~/Desktop/Hermes/"Church Site"
cd "$SITE"

echo "[church-site] Building local static site..."
~/.hermes/hermes-agent/venv/bin/python3 build_site.py

echo "[church-site] Done. Output in $SITE/site/ — open site/index.html to preview."
echo "[church-site] NOTE: publishing + DNS not wired up yet (no repo push performed)."
