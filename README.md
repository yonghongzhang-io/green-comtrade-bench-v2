# green-comtrade-bench

Deterministic, offline Comtrade-like benchmark (Green agent) with a configurable mock service and a scoring judge. It is designed to evaluate Purple agents on pagination, de-duplication, retries (429/500), page drift, and totals handling.

## Quickstart

```bash
make clean
make up
make fixtures
make test
```

Run one task:

```bash
make test-one TASK=T6_page_drift
```

Endpoints:
- Mock service (Swagger UI): http://localhost:8000/docs
- Green agent card:         http://localhost:9009/agent-card
- Assess endpoint:          http://localhost:9009/assess

## AgentBeats Submission

This Green bench provides deterministic offline evaluation with a mock Comtrade API and automated scoring. Purple agents submit file-based outputs under `_purple_output/<task_id>/`.

**A2A Endpoints:**
- `GET /.well-known/agent.json` — Agent discovery
- `POST /a2a/rpc` — JSON-RPC 2.0 (methods: tasks/send, tasks/get, tasks/cancel, tasks/sendSubscribe)
- `GET /healthz` — Health check

**A2A Mapping:** The `tasks/send` method calls the same internal logic as `POST /assess`. Example:

```bash
curl -X POST http://localhost:9009/a2a/rpc -H 'Content-Type: application/json' -d '{
  "jsonrpc": "2.0", "id": "1", "method": "tasks/send",
  "params": {"task": {"input": {"type": "object", "content": {"task_id": "T6_page_drift"}}}}
}'
```

Response includes `result.task.output.content` with `score_total`, `score_breakdown`, `errors`, and `details`.

## Layout

```text
green-comtrade-bench/
  mock_service/           # FastAPI mock Comtrade-like API
  mock_service/fixtures/  # Optional file-backed datasets (*.jsonl)
  src/                    # Green agent + judge
  scripts/                # dev_up/stage_fixtures/run_one/run_all
  _purple_output/         # Fixture source directory staged into /workspace/purple_output
  docker-compose.yml
  Makefile
  EVALUATION_CONTRACT.md
```

## Tasks (T1–T7)

| task_id             | fault mode   | what it tests                         |
|---------------------|--------------|-------------------------------------|
| T1_single_page       | none         | baseline schema/metadata             |
| T2_multi_page        | none         | pagination correctness               |
| T3_duplicates       | duplicates   | de-dup under `dedup_key`             |
| T4_rate_limit_429    | rate_limit   | retry/backoff on 429                 |
| T5_server_error_500  | server_error | retry on 500                        |
| T6_page_drift        | page_drift   | canonical sort + convergence         |
| T7_totals_trap       | totals_trap  | drop totals rows + report totals_handling |

Authoritative task definitions live in `src/tasks.py`.

## Evaluation contract

The authoritative scoring/output contract is in **EVALUATION_CONTRACT.md**. Purple agents must write:

- `_purple_output/<task_id>/data.jsonl`
- `_purple_output/<task_id>/metadata.json`
- `_purple_output/<task_id>/run.log`

Key requirements (summary):
- Deterministic `data.jsonl` ordering (stable sort) and de-dup under `dedup_key`.
- `metadata.json.query` must match task query keys.
- Fault tasks must show retry/backoff evidence in `run.log`.
- Totals tasks must drop totals rows and report `totals_handling`.

See **EVALUATION_CONTRACT.md** for the full schema, stop reasons, and scoring breakdown.

## Troubleshooting

- **Check staged outputs:** `docker compose exec -T green-agent ls -lah /workspace/purple_output`
- **macOS Docker file sharing (Errno 35 / deadlock):** avoid bind-mounting Purple output directories. This repo uses a named Docker volume for `/workspace/purple_output` and stages files via `make stage`.
- **If scores/timeouts look wrong:** run a clean reset:

```bash
make clean
make up
make fixtures
make test
```

- **View logs:**

```bash
make logs
# or
docker compose logs -f --tail=200
```
