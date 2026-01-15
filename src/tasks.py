"""
Task definitions for Green Comtrade Bench.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Task:
    task_id: str
    description: str
    query: Dict[str, Any]
    constraints: Dict[str, Any]
    fault_injection: Dict[str, Any]


def get_tasks() -> List[Task]:
    return [
        Task(
            task_id="T1_single_page",
            description="Single query, single page. Validate schema + row count.",
            query={"reporter": "840", "partner": "156", "flow": "M", "hs": "85", "year": 2021},
            constraints={"paging_mode": "page", "page_size": 1000, "max_requests": 5, "rate_limit_qps": 5, "total_rows": 800},
            fault_injection={"mode": "none"},
        ),
        Task(
            task_id="T2_multi_page",
            description="Multi-page fetch (page+maxRecords). Must fetch all pages and merge.",
            query={"reporter": "276", "partner": "250", "flow": "X", "hs": "84", "year": 2022},
            constraints={"paging_mode": "page", "page_size": 500, "max_requests": 50, "rate_limit_qps": 5, "total_rows": 2345},
            fault_injection={"mode": "pagination"},
        ),
        Task(
            task_id="T3_duplicates",
            description="Duplicates within and across pages: must deduplicate by primary key.",
            query={"reporter": "392", "partner": "410", "flow": "M", "hs": "87", "year": 2020},
            constraints={"paging_mode": "offset", "page_size": 10, "max_requests": 50, "rate_limit_qps": 5, "total_rows": 25},
            fault_injection={"mode": "duplicates", "duplicate_rate": 0.08, "cross_page_duplicate_rate": 0.03},
        ),
        Task(
            task_id="T4_rate_limit_429",
            description="Occasional 429: must backoff + retry and still finish.",
            query={"reporter": "724", "partner": "826", "flow": "X", "hs": "30", "year": 2019},
            constraints={"paging_mode": "page", "page_size": 10, "max_requests": 60, "rate_limit_qps": 3, "total_rows": 30},
            fault_injection={"mode": "rate_limit", "fail_on": [2]},
        ),
        Task(
            task_id="T5_server_error_500",
            description="Occasional 500: must retry and still finish.",
            query={"reporter": "124", "partner": "36", "flow": "M", "hs": "12", "year": 2023},
            constraints={"paging_mode": "page", "page_size": 10, "max_requests": 60, "rate_limit_qps": 3, "total_rows": 30},
            fault_injection={"mode": "server_error", "fail_on": [2]},
        ),
        Task(
            task_id="T6_page_drift",
            description="Same page may return different ordering/rows; must canonicalize + dedup.",
            query={"reporter": "356", "partner": "704", "flow": "X", "hs": "09", "year": 2018},
            constraints={"paging_mode": "page", "page_size": 12, "max_requests": 60, "rate_limit_qps": 5, "total_rows": 36},
            fault_injection={"mode": "page_drift"},
        ),
        Task(
            task_id="T7_totals_trap",
            description="Totals rows included with marker; must drop totals rows.",
            query={"reporter": "826", "partner": "372", "flow": "M", "hs": "27", "year": 2017},
            constraints={"paging_mode": "offset", "page_size": 250, "max_requests": 60, "rate_limit_qps": 5, "total_rows": 750},
            fault_injection={"mode": "totals_trap"},
        ),
    ]


def get_task(task_id: str) -> Optional[Task]:
    for t in get_tasks():
        if t.task_id == task_id:
            return t
    return None
