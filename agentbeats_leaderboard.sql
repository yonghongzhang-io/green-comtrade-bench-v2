-- Green Comtrade Bench v2 — Leaderboard Queries
-- Copy the JSON block below into AgentBeats "Leaderboard Queries" editor.

-- =============================================================================
-- Paste this JSON into AgentBeats Leaderboard Queries editor:
-- =============================================================================
/*
[
  {
    "name": "Overall Performance",
    "query": "SELECT results.participants.\"purple-comtrade-baseline-v2\" AS id, ROUND(SUM(r.score_total), 1) AS \"Total Score\", COUNT(*) AS \"Tasks\", ROUND(AVG(r.score_total), 1) AS \"Avg Score\" FROM results CROSS JOIN UNNEST(results.results[1]) AS t(r) GROUP BY results.participants.\"purple-comtrade-baseline-v2\" ORDER BY \"Total Score\" DESC;"
  }
]
*/

-- =============================================================================
-- Readable version (for reference only):
-- =============================================================================

SELECT
    results.participants."purple-comtrade-baseline-v2" AS id,
    ROUND(SUM(r.score_total), 1) AS "Total Score",
    COUNT(*) AS "Tasks",
    ROUND(AVG(r.score_total), 1) AS "Avg Score"
FROM results
CROSS JOIN UNNEST(results.results[1]) AS t(r)
GROUP BY results.participants."purple-comtrade-baseline-v2"
ORDER BY "Total Score" DESC;
