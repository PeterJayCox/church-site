#!/usr/bin/env bash
# Church Notes site — local build (staged). Currently builds to ./site only.
# No GitHub push / DNS yet. Enable the git block once a repo + host are chosen.
set -euo pipefail

SITE=~/Desktop/Hermes/"Church Site"
cd "$SITE"

echo "[church-site] Building local static site..."
~/.hermes/hermes-agent/venv/bin/python3 build_site.py

echo "[church-site] Done. Output in $SITE/docs/ — preview with scripts/serve-local.sh."
echo "[church-site] NOTE: this only builds locally. To publish, run:"
echo "[church-site]       bash ~/.hermes/scripts/church-site-deploy.sh"
