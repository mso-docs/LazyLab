#!/usr/bin/env bash
# Scan all locally available refs with current or older Gitleaks releases.
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v gitleaks >/dev/null 2>&1; then
  echo 'Gitleaks is not installed. See docs/security.md for installation instructions.' >&2
  exit 127
fi
mkdir -p artifacts/security
if gitleaks git --help >/dev/null 2>&1; then
  gitleaks git . --log-opts=--all --redact --report-format=json --report-path=artifacts/security/history.json
else
  gitleaks detect --source . --log-opts=--all --redact --report-format=json --report-path=artifacts/security/history.json
fi
