-- Green Comtrade Bench v2 — Leaderboard Queries
-- Copy the JSON block below into AgentBeats "Leaderboard Queries" editor.

-- =============================================================================
-- Paste this JSON into AgentBeats Leaderboard Queries editor:
-- =============================================================================
/*
[
  {
    "name": "Overall Performance",
    "query": "SELECT results.participants.\"purple-comtrade-baseline-v2\" AS id, ROUND(AVG(r.score_total), 1) AS \"Score\", COUNT(*) AS \"Tasks\", CASE WHEN AVG(r.score_total) >= 80.0 THEN 'PASS' ELSE 'FAIL' END AS \"Pass\" FROM results CROSS JOIN UNNEST(results.results[1]) AS t(r) GROUP BY results.participants.\"purple-comtrade-baseline-v2\" ORDER BY \"Score\" DESC;"
  },
  {
    "name": "Dimension Scores",
    "query": "SELECT results.participants.\"purple-comtrade-baseline-v2\" AS id, ROUND(AVG(COALESCE(r.score_breakdown.correctness, 0)), 1) AS \"Correctness\", ROUND(AVG(COALESCE(r.score_breakdown.completeness, 0)), 1) AS \"Completeness\", ROUND(AVG(COALESCE(r.score_breakdown.robustness, 0)), 1) AS \"Robustness\", ROUND(AVG(COALESCE(r.score_breakdown.efficiency, 0)), 1) AS \"Efficiency\", ROUND(AVG(COALESCE(r.score_breakdown.data_quality, 0)), 1) AS \"Data Quality\", ROUND(AVG(COALESCE(r.score_breakdown.observability, 0)), 1) AS \"Observability\" FROM results CROSS JOIN UNNEST(results.results[1]) AS t(r) GROUP BY results.participants.\"purple-comtrade-baseline-v2\" ORDER BY AVG(r.score_total) DESC;"
  }
]
*/

-- =============================================================================
-- Readable versions (for reference only):
-- =============================================================================

-- Query 1: Overall Performance
SELECT
    results.participants."purple-comtrade-baseline-v2" AS id,
    ROUND(AVG(r.score_total), 1) AS "Score",
    COUNT(*) AS "Tasks",
    CASE WHEN AVG(r.score_total) >= 80.0 THEN 'PASS' ELSE 'FAIL' END AS "Pass"
FROM results
CROSS JOIN UNNEST(results.results[1]) AS t(r)
GROUP BY results.participants."purple-comtrade-baseline-v2"
ORDER BY "Score" DESC;

-- Query 2: Dimension Scores
SELECT
    results.participants."purple-comtrade-baseline-v2" AS id,
    ROUND(AVG(COALESCE(r.score_breakdown.correctness, 0)), 1) AS "Correctness",
    ROUND(AVG(COALESCE(r.score_breakdown.completeness, 0)), 1) AS "Completeness",
    ROUND(AVG(COALESCE(r.score_breakdown.robustness, 0)), 1) AS "Robustness",
    ROUND(AVG(COALESCE(r.score_breakdown.efficiency, 0)), 1) AS "Efficiency",
    ROUND(AVG(COALESCE(r.score_breakdown.data_quality, 0)), 1) AS "Data Quality",
    ROUND(AVG(COALESCE(r.score_breakdown.observability, 0)), 1) AS "Observability"
FROM results
CROSS JOIN UNNEST(results.results[1]) AS t(r)
GROUP BY results.participants."purple-comtrade-baseline-v2"
ORDER BY AVG(r.score_total) DESC;
