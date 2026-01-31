#!/usr/bin/env bash
set -euo pipefail

TASKS=(
  T1_single_page
  T2_multi_page
  T3_duplicates
  T4_rate_limit_429
  T5_server_error_500
  T6_page_drift
  T7_totals_trap
)

fail=0
for task in "${TASKS[@]}"; do
  resp=""
  for _ in 1 2 3 4 5; do
    resp="$(curl -sS -X POST http://localhost:9009/assess -H 'Content-Type: application/json' -d "{\"task_id\":\"$task\"}" || true)"
    if [ -n "$resp" ]; then
      break
    fi
    sleep 1
  done
  if [ -z "$resp" ]; then
    echo "$task score_total=ERROR empty_response"
    fail=1
    continue
  fi
  score="$(python3 -c 'import json,sys; 
try:
    data=json.loads(sys.stdin.read()); 
    print(data.get("score_total", 0))
except Exception:
    print(0)
' <<<"$resp")"
  echo "$task score_total=$score"
  if python3 -c 'import sys; score=float(sys.argv[1]); sys.exit(0 if score >= 70 else 1)' "$score"; then
    :
  else
    fail=1
  fi
done

if [ "$fail" -ne 0 ]; then
  exit 1
fi
