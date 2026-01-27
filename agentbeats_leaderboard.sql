-- Green Comtrade Bench v2 — Leaderboard Queries
-- Copy the JSON block below into AgentBeats "Leaderboard Queries" editor.
--
-- IMPORTANT: Use table alias `r` to avoid name collision between
--   the table `results` and the column `results`.

-- =============================================================================
-- Paste this JSON into AgentBeats Leaderboard Queries editor:
-- =============================================================================
/*
[
  {
    "name": "Overall Performance",
    "query": "SELECT r.participants.\"purple-comtrade-baseline-v2\" AS \"Agent\", ROUND(AVG(t.score_total), 1) AS \"Score\", COUNT(*) AS \"Tasks\", CASE WHEN AVG(t.score_total) >= 90.0 THEN 'PASS' ELSE 'FAIL' END AS \"Pass\" FROM results r, UNNEST(r.results[1]) AS t GROUP BY ALL ORDER BY \"Score\" DESC"
  },
  {
    "name": "Section Breakdown",
    "query": "SELECT r.participants.\"purple-comtrade-baseline-v2\" AS \"Agent\", ROUND(AVG(COALESCE(t.score_breakdown.correctness, 0)), 1) AS \"Correctness\", ROUND(AVG(COALESCE(t.score_breakdown.completeness, 0)), 1) AS \"Completeness\", ROUND(AVG(COALESCE(t.score_breakdown.robustness, 0)), 1) AS \"Robustness\", ROUND(AVG(COALESCE(t.score_breakdown.efficiency, 0)), 1) AS \"Efficiency\", ROUND(AVG(COALESCE(t.score_breakdown.data_quality, 0)), 1) AS \"Data Quality\", ROUND(AVG(COALESCE(t.score_breakdown.observability, 0)), 1) AS \"Observability\" FROM results r, UNNEST(r.results[1]) AS t GROUP BY ALL ORDER BY AVG(t.score_total) DESC"
  }
]
*/

-- =============================================================================
-- Readable versions (for reference only):
-- =============================================================================

-- Query 1: Overall Performance
SELECT
    r.participants."purple-comtrade-baseline-v2" AS "Agent",
    ROUND(AVG(t.score_total), 1) AS "Score",
    COUNT(*) AS "Tasks",
    CASE WHEN AVG(t.score_total) >= 90.0 THEN 'PASS' ELSE 'FAIL' END AS "Pass"
FROM results r, UNNEST(r.results[1]) AS t
GROUP BY ALL
ORDER BY "Score" DESC;

-- Query 2: Section Breakdown
SELECT
    r.participants."purple-comtrade-baseline-v2" AS "Agent",
    ROUND(AVG(COALESCE(t.score_breakdown.correctness, 0)), 1) AS "Correctness",
    ROUND(AVG(COALESCE(t.score_breakdown.completeness, 0)), 1) AS "Completeness",
    ROUND(AVG(COALESCE(t.score_breakdown.robustness, 0)), 1) AS "Robustness",
    ROUND(AVG(COALESCE(t.score_breakdown.efficiency, 0)), 1) AS "Efficiency",
    ROUND(AVG(COALESCE(t.score_breakdown.data_quality, 0)), 1) AS "Data Quality",
    ROUND(AVG(COALESCE(t.score_breakdown.observability, 0)), 1) AS "Observability"
FROM results r, UNNEST(r.results[1]) AS t
GROUP BY ALL
ORDER BY AVG(t.score_total) DESC;
