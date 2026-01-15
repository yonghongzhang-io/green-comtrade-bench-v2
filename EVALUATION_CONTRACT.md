# Evaluation Contract Specification

**Version:** 1.0.0  
**Status:** Normative  
**Last Updated:** 2026-01-14

This document defines the **formal evaluation contract** for the Green Agent Comtrade Benchmark (Phase 1). A **Purple agent** must satisfy all requirements herein to be scored. The **Green judge** enforces this contract deterministically and offline.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Definitions](#2-definitions)
3. [Output Requirements](#3-output-requirements)
4. [File Format Specifications](#4-file-format-specifications)
5. [Correctness Criteria](#5-correctness-criteria)
6. [Robustness Criteria](#6-robustness-criteria)
7. [Scoring Breakdown](#7-scoring-breakdown)
8. [Deterministic Hashing Rules](#8-deterministic-hashing-rules)
9. [Logging Requirements](#9-logging-requirements)
10. [Examples](#10-examples)

---

## 1. Overview

### 1.1 Purpose

This benchmark evaluates a Purple agent's ability to:

- Fetch Comtrade-style trade data from a mock HTTP service
- Handle pagination correctly
- Deduplicate records across pages
- Tolerate transient errors (HTTP 429, 500)
- Produce deterministic, verifiable output

### 1.2 Design Principles

| Principle | Description |
|-----------|-------------|
| **Deterministic** | Same input → same score. No randomness in evaluation. |
| **Offline** | No external network calls. All evaluation is local. |
| **Docker-reproducible** | Results must be identical across Docker runs. |
| **Programmatically enforceable** | All rules can be checked by code, not human judgment. |

---

## 2. Definitions

### 2.1 Core Terms

| Term | Definition |
|------|------------|
| **Purple agent** | The autonomous agent under evaluation. May be LLM-based or rule-based. |
| **Green judge** | The deterministic evaluator that scores Purple output. |
| **Task** | A single evaluation scenario with a unique `task_id`. |
| **Row** | A single trade record containing mandatory fields (see §4.1). |
| **Primary Key** | A composite key that uniquely identifies a row for deduplication. |
| **Dedup Key** | The set of fields constituting the primary key, declared in `metadata.json`. |

### 2.2 Record Identity

A **row** is uniquely identified by its **primary key**, which MUST consist of at minimum:

```
(year, reporter, partner, flow, hs, record_id)
```

Where:
- `year`: Integer, trade year (e.g., 2021)
- `reporter`: String, ISO-3166 numeric country code of reporting country
- `partner`: String, ISO-3166 numeric country code of partner country
- `flow`: String, trade flow direction: `"M"` (import) or `"X"` (export)
- `hs`: String, HS commodity code (2-6 digits)
- `record_id`: String, unique row identifier from source

Two rows are considered **duplicates** if and only if all primary key fields match exactly (case-sensitive, type-sensitive).

---

## 3. Output Requirements

### 3.1 Directory Structure

For each task with identifier `<task_id>`, Purple MUST create:

```
_purple_output/
└── <task_id>/
    ├── data.jsonl        # REQUIRED: Output data
    ├── metadata.json     # REQUIRED: Run metadata
    ├── run.log           # REQUIRED: Execution log
    └── manifest.json     # RECOMMENDED: Integrity manifest
```

> [!IMPORTANT]
> The directory name MUST exactly match the `task_id` provided in the task request. Case-sensitive.

### 3.2 Required Files

| File | Required | Purpose |
|------|----------|---------|
| `data.jsonl` | ✅ YES | Deduplicated trade records, one JSON object per line |
| `metadata.json` | ✅ YES | Run metadata, query parameters, statistics |
| `run.log` | ✅ YES | Human-readable execution log |
| `manifest.json` | ⚠️ RECOMMENDED | SHA-256 checksums and file sizes for reproducibility |

### 3.3 Failure Conditions

The Green judge will return a **score of 0** if:

1. Output directory `_purple_output/<task_id>/` does not exist
2. Any of the three required files is missing
3. `metadata.json` is not valid JSON
4. `data.jsonl` contains malformed JSON lines

---

## 4. File Format Specifications

### 4.1 `data.jsonl` Specification

**Encoding:** UTF-8 (no BOM)  
**Format:** JSON Lines (JSONL) — one valid JSON object per line  
**Line terminator:** `\n` (LF)

#### 4.1.1 Mandatory Fields

Each JSON object MUST contain the following fields:

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `year` | integer | Trade year | 4-digit year |
| `reporter` | string | Reporter country code | ISO-3166-1 numeric |
| `partner` | string | Partner country code | ISO-3166-1 numeric |
| `flow` | string | Trade flow | `"M"` or `"X"` only |
| `hs` | string | HS commodity code | 2-6 digits |
| `tradeValue` | integer | Trade value in USD | Non-negative |
| `netWeight` | integer | Net weight in kg | Non-negative |
| `qty` | integer | Quantity | Non-negative |
| `record_id` | string | Unique row identifier | Non-empty |

#### 4.1.2 Optional Fields

Additional fields (e.g., `cmdCode`, `qtAltCode`) MAY be included but will not affect scoring.

#### 4.1.3 Row Order

Row order within `data.jsonl` is **not significant**. The Green judge will sort by primary key before comparison.

#### 4.1.4 Empty Lines

Empty lines (whitespace-only) are ignored and do not count toward row count.

---

### 4.2 `metadata.json` Specification

**Encoding:** UTF-8  
**Format:** Single JSON object (pretty-printed or minified)

#### 4.2.1 Required Fields

| Field | Type | Description | Validation Rule |
|-------|------|-------------|-----------------|
| `task_id` | string | Task identifier | MUST match directory name exactly |
| `query` | object | Query parameters used | MUST match task's expected query keys |
| `row_count` | integer | Number of data rows | MUST equal non-empty line count in `data.jsonl` |
| `schema` | array | List of field names in data | MUST contain ≥ 5 strings |
| `dedup_key` | array | Primary key field names | MUST contain ≥ 3 strings |

#### 4.2.2 Recommended Fields

| Field | Type | Description |
|-------|------|-------------|
| `created_at` | string | ISO-8601 timestamp of run completion |
| `tool_versions` | object | Version info (e.g., `{"python": "3.11", "purple": "1.0.0"}`) |
| `request_stats` | object | HTTP request statistics (see below) |
| `notes` | string | Free-text notes |

#### 4.2.3 `request_stats` Schema (Recommended)

```json
{
  "requests_total": <int>,
  "retries_total": <int>,
  "http_429": <int>,
  "http_500": <int>
}
```

#### 4.2.4 `query` Object Schema

The `query` object MUST contain these keys with values matching the task request:

| Key | Type | Example |
|-----|------|---------|
| `reporter` | string | `"840"` |
| `partner` | string | `"156"` |
| `flow` | string | `"M"` |
| `hs` | string | `"85"` |
| `year` | integer | `2021` |

> [!CAUTION]
> Query field values MUST match exactly. String `"840"` ≠ integer `840`. The Green judge performs strict type-aware comparison.

---

### 4.3 `run.log` Specification

**Encoding:** UTF-8  
**Format:** Line-oriented plain text

#### 4.3.1 Minimum Content

At minimum, `run.log` MUST contain:
- Start marker (e.g., `"INFO start"` or `"[START]"`)
- Finish marker (e.g., `"INFO done"` or `"[COMPLETE]"`)
- Minimum 10 characters of non-whitespace content

#### 4.3.2 Required Evidence by Task Type

| Fault Injection Mode | Required Log Evidence |
|---------------------|----------------------|
| `none` | Start and finish markers |
| `rate_limit` | `"429"` AND (`"retry"` OR `"backoff"`) |
| `duplicates` | Mention of dedup strategy |
| `pagination` | Page count or pagination progress |
| `server_error` | `"500"` AND `"retry"` |
| `page_drift` | Mention of canonical sort or dedup strategy |
| `totals_trap` | Mention dropping totals rows |

> [!NOTE]
> Log pattern matching is **case-insensitive**. Both `"RETRY"` and `"retry"` satisfy the retry evidence requirement.

---

### 4.4 `manifest.json` Specification (Recommended)

**Encoding:** UTF-8  
**Format:** Single JSON object

```json
{
  "files": [
    {
      "path": "<relative_filename>",
      "sha256": "<lowercase_hex_digest>",
      "bytes": <file_size_in_bytes>
    }
  ]
}
```

The manifest enables reproducibility verification but is not required for scoring.

---

## 5. Correctness Criteria

### 5.1 Row Completeness

**Definition:** Every row returned by the mock service (after deduplication) must appear in `data.jsonl`.

**Verification:**
1. Green judge knows the deterministic set of expected rows for each task
2. Purple's output is compared against this expected set
3. Missing rows → partial credit deduction

**Scoring impact:** Part of the Correctness score (see §7).

---

### 5.2 Pagination Completeness

**Definition:** For multi-page responses, Purple must fetch ALL pages until no more rows remain.

**Indicators of failure:**
- Fewer rows than expected `total_rows`
- Only first page retrieved (row count = page_size)

**Verification:**
- `row_count` in metadata compared to expected total
- Row set comparison via primary key

---

### 5.3 Deduplication Correctness

**Definition:** `data.jsonl` MUST NOT contain duplicate rows as defined by the `dedup_key`.

**Verification:**
1. Parse all rows from `data.jsonl`
2. Extract tuple of `dedup_key` fields for each row
3. Count unique vs. total rows
4. If `unique_count < total_count` → duplicates exist → penalty

**Formula:**
```
dedup_score = 1.0 if (unique == total) else 0.0
```

---

### 5.4 Query Parameter Consistency

**Definition:** The `query` object in `metadata.json` MUST match the task's expected query parameters.

**Fields checked:** `reporter`, `partner`, `flow`, `hs`, `year`

**Comparison rules:**
- Exact string matching for string fields
- Type-aware comparison (string `"2021"` ≠ integer `2021`)
- All five keys must be present and match

---

### 5.5 Totals Dimension Trap Handling

**Definition:** The mock service may insert explicit totals rows. Purple MUST drop these rows before writing `data.jsonl`.

**Totals marker (authoritative):**
- `isTotal` is `true`
- `partner` equals `"WLD"`
- `hs` equals `"TOTAL"`

**Correct behavior:**
- Drop any row matching the totals marker
- Report totals handling in `metadata.json.totals_handling`

**Verification:** Judge checks for totals rows in `data.jsonl` and expects `totals_handling.enabled=true`.

---

## 6. Robustness Criteria

### 6.1 Retry Evidence

**Definition:** When the mock service returns 429 or 500, Purple MUST implement retry logic.

**Evidence required in `run.log`:**
- For 429: Strings `"429"` AND (`"retry"` OR `"backoff"`)
- For 500: Strings `"500"` AND `"retry"`

**Scoring:** Binary — either evidence exists (full points) or not (zero points).

---

### 6.2 HTTP 429 Handling (Rate Limit)

**Expected behavior:**
1. Detect 429 response
2. Wait (backoff) before retry
3. Retry the failed request
4. Eventually succeed and continue

**Evidence:** Log must show 429 detection and retry/backoff behavior.

---

### 6.3 HTTP 500 Handling (Server Error)

**Expected behavior:**
1. Detect 500 response
2. Retry with reasonable limit (max 3-5 retries)
3. Log error and continue or fail gracefully

**Evidence:** Log must show 500 detection and retry attempt.

---

### 6.4 Page Drift Tolerance

**Definition:** Same page request may return rows in different order across requests, and some rows may drift across page boundaries.

**Expected behavior:**
- Use `record_id` as stable identifier, not row position
- Deduplicate based on primary key, not array index
- Handle pages returning overlapping rows

**Verification:** Implicit — deduplication correctness confirms this behavior.

---

## 7. Scoring Breakdown

### 7.1 Score Categories

| Category | Max Points | Weight |
|----------|------------|--------|
| Completeness | 30 | 30% |
| Correctness | 50 | 50% |
| Robustness | 20 | 20% |
| **Total** | **100** | **100%** |

---

### 7.2 Completeness Score (30 points)

| Criterion | Points | Condition |
|-----------|--------|-----------|
| Output directory exists | 10 | `_purple_output/<task_id>/` exists |
| `data.jsonl` present | 7 | File exists and is non-empty |
| `metadata.json` present | 7 | File exists and is valid JSON |
| `run.log` present | 6 | File exists and has ≥10 chars |

**Failure mode:** Any missing required file → Completeness = 0

---

### 7.3 Correctness Score (50 points)

| Criterion | Points | Condition |
|-----------|--------|-----------|
| Row count match | 20 | `metadata.row_count` == actual line count |
| Schema validity | 10 | `schema` is array with ≥5 elements |
| Query match | 10 | `query` matches task's expected values |
| Deduplication | 10 | Zero duplicate rows by `dedup_key` |

---

### 7.4 Robustness Score (20 points)

| Task Mode | Criteria | Points |
|-----------|----------|--------|
| `rate_limit` | Log contains "429" AND "retry/backoff" | 20 |
| `server_error` | Log contains "500" AND "retry" | 20 |
| Other modes | Log has meaningful content (>10 chars) | 20 |

---

### 7.5 Partial Credit Rules

| Scenario | Credit |
|----------|--------|
| All required files present but with errors | Completeness: 30, Correctness: varies |
| Row count mismatch | Correctness: -20 |
| Schema too small (<5 fields) | Correctness: -10 |
| Query mismatch | Correctness: -10 |
| Duplicates found | Correctness: -10 |
| No retry evidence on fault task | Robustness: 0 |

---

### 7.6 Score Calculation Formula

```
total_score = completeness + correctness + robustness

where:
  completeness ∈ {0, 30}  # Binary
  correctness ∈ [0, 50]   # Cumulative
  robustness ∈ {0, 20}    # Binary per task type
```

---

## 8. Deterministic Hashing Rules

### 8.1 File Hashing

**Algorithm:** SHA-256  
**Encoding:** File bytes (binary mode)  
**Output:** Lowercase hexadecimal string (64 characters)

```python
import hashlib
sha256 = hashlib.sha256(file_bytes).hexdigest()
```

### 8.2 What Is Hashed

| File | Hashed | Purpose |
|------|--------|---------|
| `data.jsonl` | ✅ | Reproducibility verification |
| `metadata.json` | ✅ | Reproducibility verification |
| `run.log` | ❌ | May vary by run (timing, etc.) |

### 8.3 Row Hashing (for dedup verification)

**Not required** — deduplication is verified by key comparison, not hashing.

---

## 9. Logging Requirements

### 9.1 Minimum Log Structure

```
[TIMESTAMP] [LEVEL] [MESSAGE]
```

Recommended levels: `DEBUG`, `INFO`, `WARN`, `ERROR`

### 9.2 Required Log Events

| Event | When | Example |
|-------|------|---------|
| Start | Task begins | `INFO Starting task T1_single_page` |
| Page fetch | Each page | `INFO Fetched page 3/10, 500 rows` |
| Retry | On 429/500 | `WARN Got 429, retrying with backoff` |
| Dedup | After dedup | `INFO Deduplicated 1050→1000 rows` |
| Finish | Task ends | `INFO Complete. Wrote 1000 rows.` |

### 9.3 Log Evidence Patterns

The Green judge scans for these patterns (case-insensitive):

| Pattern | Regex | Purpose |
|---------|-------|---------|
| 429 detected | `429` | Rate limit hit |
| 500 detected | `500` | Server error |
| Retry | `retry` | Retry attempt |
| Backoff | `backoff` | Exponential backoff |
| Dedup | `dedup` | Deduplication performed |

---

## 10. Examples

### 10.1 Minimal Valid Output Tree

```
_purple_output/
└── T1_single_page/
    ├── data.jsonl
    ├── metadata.json
    └── run.log
```

### 10.2 Minimal Valid `data.jsonl`

```jsonl
{"year":2021,"reporter":"840","partner":"156","flow":"M","hs":"85","tradeValue":123456,"netWeight":1000,"qty":50,"record_id":"seed-0"}
{"year":2021,"reporter":"840","partner":"156","flow":"M","hs":"85","tradeValue":234567,"netWeight":2000,"qty":100,"record_id":"seed-1"}
```

### 10.3 Minimal Valid `metadata.json`

```json
{
  "task_id": "T1_single_page",
  "query": {
    "reporter": "840",
    "partner": "156",
    "flow": "M",
    "hs": "85",
    "year": 2021
  },
  "row_count": 2,
  "schema": ["year", "reporter", "partner", "flow", "hs", "tradeValue", "netWeight", "qty", "record_id"],
  "dedup_key": ["year", "reporter", "partner", "flow", "hs", "record_id"]
}
```

### 10.4 Minimal Valid `run.log`

```
2026-01-14T12:00:00Z INFO Starting task T1_single_page
2026-01-14T12:00:01Z INFO Fetched page 1/1, 2 rows
2026-01-14T12:00:01Z INFO Complete. Wrote 2 rows.
```

### 10.5 Valid `run.log` with Retry Evidence

```
2026-01-14T12:00:00Z INFO Starting task T4_rate_limit_retry
2026-01-14T12:00:01Z INFO Fetched page 1/3, 400 rows
2026-01-14T12:00:02Z WARN HTTP 429 received, applying exponential backoff
2026-01-14T12:00:05Z INFO Retry successful, fetched page 2/3
2026-01-14T12:00:06Z INFO Fetched page 3/3, 400 rows
2026-01-14T12:00:06Z INFO Complete. Wrote 1200 rows.
```

### 10.6 Recommended `manifest.json`

```json
{
  "files": [
    {
      "path": "data.jsonl",
      "sha256": "a1b2c3d4e5f6...",
      "bytes": 52480
    },
    {
      "path": "metadata.json",
      "sha256": "f6e5d4c3b2a1...",
      "bytes": 512
    },
    {
      "path": "run.log",
      "sha256": "1234567890ab...",
      "bytes": 2048
    }
  ]
}
```

---

## Appendix A: Task-Specific Requirements

| Task ID | Fault Mode | Special Requirements |
|---------|------------|---------------------|
| `T1_single_page` | `none` | Basic fetch, single page |
| `T2_multi_page` | `pagination` | Page-based pagination, fetch all pages |
| `T3_duplicates` | `duplicates` | Deduplicate within-page and cross-page duplicates |
| `T4_rate_limit_429` | `rate_limit` | Must handle 429 with backoff |
| `T5_server_error_500` | `server_error` | Must retry on 500 |
| `T6_page_drift` | `page_drift` | Canonical sort + dedup under drift |
| `T7_totals_trap` | `totals_trap` | Drop totals rows marked by `isTotal` |

---

## Appendix B: Error Codes

| Error | Description | Score Impact |
|-------|-------------|--------------|
| `E001` | Missing output directory | Total: 0 |
| `E002` | Missing required file | Completeness: 0 |
| `E003` | Invalid JSON in metadata | Correctness: 0 |
| `E004` | Row count mismatch | Correctness: -20 |
| `E005` | Schema too small | Correctness: -10 |
| `E006` | Query mismatch | Correctness: -10 |
| `E007` | Duplicates found | Correctness: -10 |
| `E008` | No retry evidence | Robustness: 0 |

---

## Appendix C: Future Extensions

The following are **out of scope** for v1.0 but may be added later:

- [ ] Parquet format support as alternative to JSONL
- [ ] Streaming hash verification
- [ ] Multi-query batch tasks
- [ ] Network failure simulation (connection drops)

---

**End of Evaluation Contract Specification**
