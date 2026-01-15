# Mock Fixtures

These JSONL files provide small, deterministic datasets for the mock service.

## Schema

Each line is a JSON object with at least:

- `year`, `reporter`, `partner`, `flow`, `hs`
- `tradeValue`, `netWeight`, `qty`
- `record_id`

Extra fields are allowed. Blank lines are ignored.

## Totals Marker

Totals rows use the following marker (all must match):

- `isTotal` is `true`
- `partner` equals `"WLD"`
- `hs` equals `"TOTAL"`

Totals rows should be dropped by the Purple agent before writing `data.jsonl`.

**Note:** In totals_trap mode, the mock service prepends one synthetic totals row to every /records response, so totals rows may be numerous depending on the client's pagination strategy; agents must filter all rows matching (isTotal=true AND partner="WLD" AND hs="TOTAL").

## Regenerating Fixtures

You can create synthetic fixtures via:

```
python3 scripts/gen_fixtures.py
```
