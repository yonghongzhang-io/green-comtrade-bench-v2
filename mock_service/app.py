"""
Mock Comtrade-like service (FastAPI).
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="Mock Comtrade Service")

FIXTURES_DIR = Path(__file__).parent / "fixtures"

STATE: Dict[str, Any] = {
    "configured": False,
    "task_id": None,
    "query": {},
    "constraints": {},
    "fault_injection": {"mode": "none"},
    "request_count": 0,
    "faults_seen": set(),
    "last_page_rows": [],
}


class ConfigurePayload(BaseModel):
    task_id: str
    query: Dict[str, Any]
    constraints: Dict[str, Any]
    fault_injection: Dict[str, Any]


@app.post("/configure")
def configure(payload: ConfigurePayload) -> Dict[str, Any]:
    STATE["configured"] = True
    STATE["task_id"] = payload.task_id
    STATE["query"] = payload.query
    STATE["constraints"] = payload.constraints
    STATE["fault_injection"] = payload.fault_injection
    STATE["request_count"] = 0
    STATE["faults_seen"] = set()
    STATE["last_page_rows"] = []
    return {"ok": True, "task_id": payload.task_id, "fault_injection": payload.fault_injection}


def _stable_seed(text: str) -> int:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _load_fixture(task_id: str) -> Optional[List[Dict[str, Any]]]:
    for ext in [".jsonl", ".json"]:
        p = FIXTURES_DIR / f"{task_id}{ext}"
        if not p.exists():
            continue
        if ext == ".jsonl":
            rows: List[Dict[str, Any]] = []
            for idx, raw in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSONL in {p} at line {idx}: {e}") from e
            return rows
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def _generate_rows(task_id: str, q: Dict[str, Any], total_rows: int) -> List[Dict[str, Any]]:
    seed = _stable_seed(f"{task_id}:{q.get('reporter')}:{q.get('partner')}:{q.get('flow')}:{q.get('hs')}:{q.get('year')}")
    rng = random.Random(seed)
    rows = []
    for i in range(total_rows):
        rows.append({
            "year": q.get("year"),
            "reporter": q.get("reporter"),
            "partner": q.get("partner"),
            "flow": q.get("flow"),
            "hs": q.get("hs"),
            "cmdCode": q.get("hs"),
            "tradeValue": int(rng.random() * 1_000_000),
            "netWeight": int(rng.random() * 50_000),
            "qty": int(rng.random() * 10_000),
            "record_id": f"{task_id}-{i:06d}",
        })
    return rows


def _get_base_rows(task_id: str, q: Dict[str, Any], total_rows: int) -> List[Dict[str, Any]]:
    try:
        fixture = _load_fixture(task_id)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if fixture:
        return fixture
    return _generate_rows(task_id, q, total_rows)


def _apply_drift(rows: List[Dict[str, Any]], task_id: str, request_count: int) -> List[Dict[str, Any]]:
    idx = list(range(len(rows)))
    rng = random.Random(_stable_seed(f"{task_id}:drift:{request_count}"))
    rng.shuffle(idx)
    return [rows[i] for i in idx]


def _apply_duplicates(
    page_rows: List[Dict[str, Any]],
    task_id: str,
    request_count: int,
    dup_rate: float,
    cross_dup_rate: float,
) -> List[Dict[str, Any]]:
    if not page_rows:
        return page_rows
    rows = list(page_rows)
    rng = random.Random(_stable_seed(f"{task_id}:dup:{request_count}"))
    within = int(len(rows) * dup_rate)
    for j in range(within):
        src_idx = j % len(rows)
        dst_idx = rng.randrange(0, len(rows))
        rows[dst_idx] = rows[src_idx]
    if STATE["last_page_rows"] and cross_dup_rate > 0:
        cross = int(len(rows) * cross_dup_rate)
        for _ in range(cross):
            src = rng.choice(STATE["last_page_rows"])
            dst_idx = rng.randrange(0, len(rows))
            rows[dst_idx] = src
    return rows


def _make_totals_row(page_rows: List[Dict[str, Any]], task_id: str, page: int, q: Dict[str, Any]) -> Dict[str, Any]:
    trade_value = sum(int(r.get("tradeValue", 0)) for r in page_rows)
    net_weight = sum(int(r.get("netWeight", 0)) for r in page_rows)
    qty = sum(int(r.get("qty", 0)) for r in page_rows)
    return {
        "year": q.get("year"),
        "reporter": q.get("reporter"),
        "partner": "WLD",
        "flow": q.get("flow"),
        "hs": "TOTAL",
        "tradeValue": trade_value,
        "netWeight": net_weight,
        "qty": qty,
        "record_id": f"{task_id}-TOTAL-{page:04d}",
        "isTotal": True,
    }


def _select_page_params(
    page: int,
    offset: Optional[int],
    max_records: Optional[int],
    page_size: Optional[int],
    constraints: Dict[str, Any],
) -> Dict[str, int]:
    per_page = int(max_records or page_size or constraints.get("page_size") or 500)
    if offset is not None:
        start = int(offset)
        page_index = start // per_page + 1
    else:
        page_index = int(page)
        start = (page_index - 1) * per_page
    return {"start": start, "page": page_index, "page_size": per_page}


def _maybe_fault(mode: str) -> None:
    fi = STATE.get("fault_injection") or {}
    fail_on = fi.get("fail_on") or []
    if mode in {"rate_limit", "server_error"} and STATE["request_count"] in fail_on:
        key = (mode, STATE["request_count"])
        if key not in STATE["faults_seen"]:
            STATE["faults_seen"].add(key)
            status = 429 if mode == "rate_limit" else 500
            raise HTTPException(status_code=status, detail=f"Simulated {status} for {mode}")


@app.get("/search")
def search(
    page: int = Query(1, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=5000),
    maxRecords: Optional[int] = Query(None, ge=1, le=10000),
    offset: Optional[int] = Query(None, ge=0),
) -> Dict[str, Any]:
    if not STATE["configured"]:
        raise HTTPException(status_code=400, detail="Not configured. Call POST /configure first.")

    STATE["request_count"] += 1
    fi = STATE.get("fault_injection") or {}
    mode = fi.get("mode", "none")

    if mode == "rate_limit":
        _maybe_fault("rate_limit")
    if mode == "server_error":
        _maybe_fault("server_error")

    constraints = STATE.get("constraints") or {}
    total_rows = int(fi.get("total_rows") or constraints.get("total_rows") or 800)
    q = STATE["query"]

    rows = _get_base_rows(STATE["task_id"], q, total_rows)
    if mode == "page_drift":
        rows = _apply_drift(rows, STATE["task_id"], STATE["request_count"])

    paging = _select_page_params(page, offset, maxRecords, page_size, constraints)
    start = paging["start"]
    end = min(total_rows, start + paging["page_size"])
    page_rows = rows[start:end]

    if mode == "duplicates":
        dup_rate = float(fi.get("duplicate_rate", 0.06))
        cross_rate = float(fi.get("cross_page_duplicate_rate", 0.02))
        page_rows = _apply_duplicates(page_rows, STATE["task_id"], STATE["request_count"], dup_rate, cross_rate)

    if mode == "totals_trap":
        totals_row = _make_totals_row(page_rows, STATE["task_id"], paging["page"], q)
        page_rows = [totals_row] + page_rows

    STATE["last_page_rows"] = page_rows

    return {
        "ok": True,
        "task_id": STATE["task_id"],
        "page": paging["page"],
        "page_size": paging["page_size"],
        "offset": start,
        "total_rows": total_rows,
        "returned_rows": len(page_rows),
        "data": page_rows,
    }


@app.get("/records")
def records(
    page: int = Query(1, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=5000),
    maxRecords: Optional[int] = Query(None, ge=1, le=10000),
    offset: Optional[int] = Query(None, ge=0),
) -> Dict[str, Any]:
    return search(page=page, page_size=page_size, maxRecords=maxRecords, offset=offset)
