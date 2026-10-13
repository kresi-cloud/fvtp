#!/usr/bin/env bash
# Napi frissítés: portáladatok → build → git push (a Vercel a GitHub-repóból automatikusan újratelepít).
# Ütemezett Claude-feladatból vagy kézzel futtatható. Feltétel: a repo klónja a REPO mappában, push-jog.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${PORTAL_DATA:-$HERE/../portal-data}"
REPO="${FVTP_REPO:-$HERE}"
python3 "$HERE/build.py" --data "$DATA" || true
cd "$REPO"
git add -A public/data public/index.html public/belepes.html
if git diff --cached --quiet; then echo "nincs változás"; exit 0; fi
git -c user.name="fvtp-bot" -c user.email="fvtp-bot@users.noreply.github.com" commit -q -m "napi frissítés $(date -u +%Y-%m-%d\ %H:%M)Z"
git push -q
echo "feltöltve"
