#!/usr/bin/env bash
# Read-only Snowflake query helper for TakeThesis (GAUNTLET_SANDBOX.SOURCE).
# Password is read from the SNOWFLAKE_PASSWORD env var only — never argv, never disk.
#
# Usage:
#   export SNOWFLAKE_PASSWORD='<correct password>'
#   ./connect.sh "SELECT CURRENT_VERSION() AS version, CURRENT_ROLE() AS role;"
#
# Discipline (see ~/.claude/plans plan): one query per call, read the output before the
# next call, never SELECT * or unbounded-scan KLAVIYO_EVENTS (102M rows / 22 GB).
set -euo pipefail

if [[ -z "${SNOWFLAKE_PASSWORD:-}" ]]; then
  echo "SNOWFLAKE_PASSWORD is not set. Run: export SNOWFLAKE_PASSWORD='...'" >&2
  exit 1
fi
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 \"<SQL query>\"" >&2
  exit 1
fi

readonly ACCOUNT=CSB35864
readonly USERNAME=GAUNTLET_USER
readonly WAREHOUSE=GAUNTLET_WH
readonly DATABASE=GAUNTLET_SANDBOX
readonly SCHEMA=SOURCE

snow sql -x \
  --account "$ACCOUNT" \
  --user "$USERNAME" \
  --warehouse "$WAREHOUSE" \
  --database "$DATABASE" \
  --schema "$SCHEMA" \
  -q "$1"
