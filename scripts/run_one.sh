#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <task_id>" >&2
  exit 2
fi

TASK_ID="$1"
curl -sS -X POST http://localhost:9009/assess -H 'Content-Type: application/json' -d "{\"task_id\":\"$TASK_ID\"}"
