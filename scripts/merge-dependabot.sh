#!/usr/bin/env bash
# Merge Dependabot pull requests safely: never on a stale green tick.
#
#   scripts/merge-dependabot.sh 18 19        # in this order
#   scripts/merge-dependabot.sh --yes 18     # skip the confirmation for breaking-looking jumps
#
# For each PR: refuse anything not opened by Dependabot; list its updates and ask before any
# major jump (or minor jump of a 0.x package); bring it up to date with main; wait for the new
# commit and its checks; merge exactly that commit. Stops at the first problem.
set -euo pipefail

assume_yes=false
if [ "${1:-}" = "--yes" ]; then assume_yes=true; shift; fi
if [ "$#" -eq 0 ]; then
  echo "usage: $0 [--yes] <pr-number> [<pr-number> ...]" >&2
  echo "open Dependabot pull requests:" >&2
  gh pr list --author "app/dependabot" --json number,title -q '.[] | "  #\(.number)  \(.title)"' >&2
  exit 2
fi

repo="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
fail() { echo "✗ $*" >&2; exit 1; }

breaking_jumps() {  # prints any update whose version jump may break things
  gh pr view "$1" --json body -q .body \
    | grep -oE 'Updates `[^`]+` from [0-9][^ ]* to [0-9][^ ]*' \
    | while read -r _ name _ from _ to; do
        IFS=. read -r fmaj fmin _ <<< "$from"
        IFS=. read -r tmaj tmin _ <<< "$to"
        if [ "$fmaj" != "$tmaj" ] || { [ "$fmaj" = 0 ] && [ "$fmin" != "$tmin" ]; }; then
          echo "    ${name//\`/} $from → $to"
        fi
      done
}

merge_fresh() {
  local pr="$1" author before head result
  author="$(gh pr view "$pr" --json author -q .author.login)"
  case "$author" in
    dependabot|app/dependabot|dependabot\[bot\]) ;;
    *) fail "#$pr was opened by $author, not Dependabot: merge it by hand" ;;
  esac

  echo "== #$pr: $(gh pr view "$pr" --json title -q .title)"
  gh pr view "$pr" --json body -q .body | grep -E '^Updates `' | sed 's/^/   /' || true
  local jumps
  jumps="$(breaking_jumps "$pr")"
  if [ -n "$jumps" ]; then
    echo "   ⚠ these may include breaking changes:"
    echo "$jumps"
    if ! $assume_yes; then
      read -r -p "   merge #$pr anyway, if its checks pass? [y/N] " answer
      [ "$answer" = y ] || [ "$answer" = Y ] || fail "#$pr skipped at your request"
    fi
  fi

  before="$(gh pr view "$pr" --json headRefOid -q .headRefOid)"
  if result="$(gh api -X PUT "repos/$repo/pulls/$pr/update-branch" 2>&1)"; then
    echo "   updated with today's main; waiting for the new commit"
    head="$before"
    for _ in $(seq 1 30); do
      sleep 10
      head="$(gh pr view "$pr" --json headRefOid -q .headRefOid)"
      [ "$head" != "$before" ] && break
    done
    [ "$head" != "$before" ] || fail "#$pr: the updated commit did not appear within 5 minutes"
  elif grep -qi "no new commits" <<< "$result"; then
    echo "   already up to date with main"
    head="$before"
  else
    fail "#$pr could not be updated: $result"
  fi

  echo "   checking ${head:0:7}"
  sleep 30  # let the new checks register before watching them
  gh pr checks "$pr" --watch --interval 20 || fail "#$pr: checks failed on ${head:0:7}, not merged"
  gh pr merge "$pr" --squash --delete-branch --match-head-commit "$head" \
    || fail "#$pr: merge refused (main may have moved again): rerun the script"
  echo "✓ #$pr merged at ${head:0:7}"
}

for pr in "$@"; do merge_fresh "$pr"; done
git pull --ff-only
echo
echo "Merged: $*. Watch Render and Vercel deploy, then on this machine:"
echo "  (cd backend && pip install -r requirements.txt -r requirements-dev.txt)"
echo "  (cd frontend && npm ci && npx playwright install chromium)"
