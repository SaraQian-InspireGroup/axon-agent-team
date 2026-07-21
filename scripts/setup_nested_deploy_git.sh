#!/usr/bin/env bash
# One-time migration: give backend/ and frontend/ their own .git remotes
# to abigail830 deploy repos (as originally requested).
#
# Before: monorepo tracks backend/ + frontend/; _deploy/ held mirror clones.
# After:  backend/.git → agent-team-backend
#         frontend/.git → agent-team-frontend
#         monorepo tracks them as git submodules (optional pointer commits).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_REMOTE="git@github.com:abigail830/agent-team-backend.git"
FRONTEND_REMOTE="git@github.com:abigail830/agent-team-frontend.git"

say() { printf '==> %s\n' "$*"; }

if [[ -d "$ROOT/backend/.git" && -d "$ROOT/frontend/.git" ]]; then
  say "backend/.git and frontend/.git already exist."
  (cd "$ROOT/backend" && git remote -v)
  (cd "$ROOT/frontend" && git remote -v)
  exit 0
fi

say "This will:"
say "  1) Stop monorepo from tracking backend/ and frontend/ as plain folders"
say "  2) Attach deploy-repo .git into backend/ and frontend/"
say "  3) Register git submodules in axon-agent-team"
echo ""
read -r -p "Continue? [y/N] " ans
[[ "${ans:-}" == "y" || "${ans:-}" == "Y" ]] || exit 1

cd "$ROOT"

# Prefer existing _deploy clones (preserve history); else clone fresh.
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

clone_or_reuse() {
  local name="$1" remote="$2" src="$3" dest="$4"
  if [[ -d "$src/.git" ]]; then
    say "Reuse _deploy/$name"
    rsync -a --exclude .git "$src/" "$tmpdir/$name/"
    cp -R "$src/.git" "$tmpdir/$name/.git"
  else
    say "Clone $remote"
    git clone "$remote" "$tmpdir/$name"
    rsync -a --delete \
      --exclude .git --exclude node_modules --exclude dist --exclude .run \
      --exclude .env --exclude .env.local --exclude __pycache__ \
      --exclude .pytest_cache --exclude .venv --exclude .venv-test \
      --exclude 'data/proposal-artifacts' --exclude 'data/chat-attachments' \
      "$dest/" "$tmpdir/$name/"
  fi
  (cd "$tmpdir/$name" && git remote set-url origin "$remote")
}

clone_or_reuse "agent-team-backend" "$BACKEND_REMOTE" \
  "$ROOT/_deploy/agent-team-backend" "$ROOT/backend"
clone_or_reuse "agent-team-frontend" "$FRONTEND_REMOTE" \
  "$ROOT/_deploy/agent-team-frontend" "$ROOT/frontend"

say "Unlink backend/frontend from monorepo index (files stay on disk)"
git rm -r --cached backend frontend 2>/dev/null || true

say "Install nested .git directories"
rm -rf "$ROOT/backend/.git" "$ROOT/frontend/.git"
mv "$tmpdir/agent-team-backend/.git" "$ROOT/backend/.git"
mv "$tmpdir/agent-team-frontend/.git" "$ROOT/frontend/.git"

say "Register submodules in monorepo"
git submodule absorbgitdirs backend frontend 2>/dev/null || {
  if [[ ! -f .gitmodules ]]; then
    git submodule add -f "$BACKEND_REMOTE" backend
    git submodule add -f "$FRONTEND_REMOTE" frontend
  fi
}

say "Status backend:"
(cd "$ROOT/backend" && git status -sb && git remote -v)
say "Status frontend:"
(cd "$ROOT/frontend" && git status -sb && git remote -v)
say "Status monorepo:"
git status -sb

cat <<'EOF'

Next steps (manual):
  1) cd backend  → review changes → commit → git push origin main
  2) cd frontend → review changes → commit → git push origin main
  3) cd ..       → git add .gitmodules backend frontend → commit monorepo submodule pointers
  4) Optional: rm -rf _deploy/   (no longer needed)

EOF
