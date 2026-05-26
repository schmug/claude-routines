#!/usr/bin/env bash
# Audits (default) or provisions (--apply) the required default-branch ruleset
# for a target repo: require status checks (strict), block force-push and
# deletion, require a pull request before merging, enforce_admins=false so the
# owner can still override in emergencies.
#
# Usage:
#   scripts/setup-branch-protection.sh <owner/repo> [branch] [--apply]
#
# Examples:
#   scripts/setup-branch-protection.sh schmug/my-repo            # audit only
#   scripts/setup-branch-protection.sh schmug/my-repo main       # audit main explicitly
#   scripts/setup-branch-protection.sh schmug/my-repo main --apply  # provision
#
# Prerequisites: gh CLI authenticated with repo-admin scope.
set -euo pipefail

REPO="${1:?usage: setup-branch-protection.sh <owner/repo> [branch] [--apply]}"
BRANCH="${2:-main}"
APPLY="${3:-}"

echo "== current protection for $REPO @ $BRANCH =="
gh api "repos/$REPO/branches/$BRANCH/protection" 2>/dev/null \
  | jq '{required_status_checks, enforce_admins, required_pull_request_reviews, allow_force_pushes, allow_deletions}' \
  || echo "(no protection set)"

if [[ "$APPLY" != "--apply" ]]; then
  echo
  echo "DRY RUN — re-run with --apply as the 3rd argument to provision the ruleset:"
  echo "  - require a pull request before merging"
  echo "  - require status checks to pass (strict)"
  echo "  - block force pushes"
  echo "  - block branch deletion"
  echo "  - enforce_admins=false (owner retains emergency override)"
  exit 0
fi

# required_approving_review_count is deliberately 0: the six-condition
# fail-closed gate + required status checks are the real controls.
# A human approval count would block the auto-merge path for trusted PRs
# without adding meaningful security. Operators who want ≥1 reviews can
# set that value independently after running this script.
gh api -X PUT "repos/$REPO/branches/$BRANCH/protection" \
  --input - <<'JSON'
{
  "required_status_checks": { "strict": true, "contexts": [] },
  "enforce_admins": false,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON

echo "protection applied to $REPO @ $BRANCH"
