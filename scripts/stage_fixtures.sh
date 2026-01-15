#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-_purple_output}"
SERVICE="${SERVICE:-green-agent}"

if [ ! -d "$ROOT" ]; then
  echo "missing fixtures dir: $ROOT" >&2
  exit 1
fi

for dir in "$ROOT"/*; do
  [ -d "$dir" ] || continue
  task_id="$(basename "$dir")"
  docker compose exec -T "$SERVICE" sh -c "mkdir -p /workspace/purple_output/$task_id"
  for file in data.jsonl metadata.json run.log manifest.json; do
    if [ -f "$dir/$file" ]; then
      docker compose exec -T "$SERVICE" sh -c "cat > /workspace/purple_output/$task_id/$file" < "$dir/$file"
    fi
  done
done
