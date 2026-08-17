# Green Comtrade Bench v2

[![CI](https://github.com/yonghongzhang-io/green-comtrade-bench-v2/actions/workflows/ci.yml/badge.svg)](https://github.com/yonghongzhang-io/green-comtrade-bench-v2/actions/workflows/ci.yml)

> **Supporting benchmark infrastructure for ComtradeBench.** For the current flagship 10-task OpenEnv benchmark, cross-model evaluation, and training results, see **[comtrade-openenv](https://github.com/yonghongzhang-io/comtrade-openenv)**.

Green Comtrade Bench v2 is a deterministic, offline benchmark and scoring judge for evaluating agents under Comtrade-like API conditions. It uses a configurable mock service so that pagination, duplicates, transient failures, page drift, and totals handling can be tested reproducibly.

The repository originated as the **Green-agent evaluation side** of the AgentBeats workflow and now serves as a transparent reference implementation of the benchmark contract and judge.

## What it evaluates

The benchmark tests whether an agent can complete data-retrieval workflows correctly when the API is not perfectly clean.

| Task | Fault mode | What it tests |
|---|---|---|
| `T1_single_page` | none | baseline schema and metadata |
| `T2_multi_page` | none | pagination correctness |
| `T3_duplicates` | duplicates | de-duplication under `dedup_key` |
| `T4_rate_limit_429` | rate limit | retry/backoff on HTTP 429 |
| `T5_server_error_500` | server error | retry on HTTP 500 |
| `T6_page_drift` | page drift | canonical sorting and convergence |
| `T7_totals_trap` | totals trap | filtering totals rows and reporting handling |

Authoritative task definitions live in `src/tasks.py`.

## Scoring

Each task is scored across six dimensions for a total of 100 points.

| Dimension | Points | Signal |
|---|---:|---|
| **Correctness** | 30 | data accuracy, query match, row count, schema, deduplication |
| **Completeness** | 15 | required files and metadata are present |
| **Robustness** | 15 | appropriate handling of 429/500 and other faults |
| **Efficiency** | 15 | request discipline relative to task-specific baselines |
| **Data quality** | 15 | type consistency, integrity, and valid outputs |
| **Observability** | 10 | traceable execution fields and useful audit logs |

The scoring implementation is in [`src/judge.py`](src/judge.py).

### Governance rules

The judge is designed to discourage gaming and reward complete, traceable execution.

- **Completeness gate:** incomplete required outputs receive no efficiency credit.
- **Correctness gate:** low correctness caps efficiency and observability credit.
- **Efficiency is task-aware:** pagination-heavy tasks are compared with task-specific request baselines.
- **Observability means traceability, not verbosity:** longer logs do not receive more points unless they contain the fields needed to reconstruct execution.

## Quick start

### Install

```bash
pip install -e .
```

`pyproject.toml` is the canonical dependency source.

### Run the benchmark locally

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

Useful local endpoints:

- Mock service / Swagger UI: `http://localhost:8000/docs`
- Green agent card: `http://localhost:9009/agent-card`
- Assessment endpoint: `http://localhost:9009/assess`

## Evaluation contract

The authoritative output and scoring contract is defined in **[EVALUATION_CONTRACT.md](EVALUATION_CONTRACT.md)** together with the judge implementation.

Purple agents write:

```text
_purple_output/<task_id>/data.jsonl
_purple_output/<task_id>/metadata.json
_purple_output/<task_id>/run.log
```

Key requirements include:

- deterministic output ordering and de-duplication under `dedup_key`
- task-query consistency in `metadata.json`
- retry/backoff evidence for injected fault tasks
- explicit totals handling for totals-trap tasks
- traceable run logs suitable for debugging and audit

## Reference baseline

The repository contains a deterministic reference Purple implementation in `baseline_purple/`.

It demonstrates that the benchmark is fundamentally about **robust execution**, not about requiring an LLM. A well-engineered rule-based client can perform strongly when it handles pagination, retries, deduplication, and data-quality checks correctly.

A standalone reference implementation is also available at **[purple-comtrade-baseline-v2](https://github.com/yonghongzhang-io/purple-comtrade-baseline-v2)**.

## Offline validation

The benchmark includes an offline validator for checking Purple outputs before evaluation.

Example:

```bash
python scripts/validate_purple_output.py _purple_output/T1_single_page \
  --task-query '{"reporter":"840","partner":"156","flow":"M","hs":"85","year":2021}' \
  --fault-mode none
```

The validator checks, among other things:

- required output files
- valid JSON / JSONL
- mandatory metadata fields and types
- row-count consistency
- required schema fields
- task-query consistency
- duplicate records
- totals filtering
- fault-handling evidence in logs

JSON schemas are available in `schemas/`.

## Reproducibility

The CI workflow runs the benchmark from a clean environment using Docker Compose and the same deterministic mock-service/judge logic used locally.

Typical pipeline:

```text
clean → start services → health checks → stage fixtures → evaluate → cleanup
```

See `.github/workflows/ci.yml` and the CI badge above for the current state.

## A2A / AgentBeats integration

The Green agent exposes A2A-compatible endpoints including:

- `GET /.well-known/agent.json`
- `POST /a2a/rpc`
- `GET /healthz`

The A2A assessment path delegates to the same underlying evaluation logic as the local benchmark so the scoring contract remains consistent across execution modes.

## Demo

[![Green Comtrade Bench Demo](https://img.youtube.com/vi/JPap8xPvRL4/maxresdefault.jpg)](https://www.youtube.com/watch?v=JPap8xPvRL4)

The demo walks through repository structure, containerized execution, an example benchmark task, and the evaluation workflow.

## Repository layout

```text
green-comtrade-bench/
├── mock_service/          # deterministic Comtrade-like API + fixtures
├── src/                   # Green agent, tasks, and scoring judge
├── scripts/               # local execution and validation utilities
├── schemas/               # output schemas
├── baseline_purple/       # reference Purple implementation
├── _purple_output/        # staged agent outputs
├── docker-compose.yml
├── Makefile
└── EVALUATION_CONTRACT.md
```

## Related repositories

- **[ComtradeBench / OpenEnv](https://github.com/yonghongzhang-io/comtrade-openenv)** — current flagship research repository and 10-task benchmark
- **[Purple Comtrade Baseline v2](https://github.com/yonghongzhang-io/purple-comtrade-baseline-v2)** — standalone deterministic reference agent
- **[AgentBeats Leaderboard v2](https://github.com/yonghongzhang-io/agentbeats-leaderboard-v2)** — competition and submission infrastructure

---

This repository is maintained as a reproducible benchmark-infrastructure component of the broader **ComtradeBench** project.
