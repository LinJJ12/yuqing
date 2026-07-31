# Implement — 多 BV / UP 口碑对比

## Checklist

1. [x] Collect: write `mid` / `owner_name` into `raw.extra` when available
2. [x] `services/video_report.py` (or new `compare.py`): `compare_videos(bvids, …)`
3. [x] API router + `client.js` methods
4. [x] pytest for compare (2 BV fixture)
5. [x] Reports page UI: multi-select + table/chart
6. [x] (Optional same PR) `list_ups` / `up_detail` if mid present
7. [x] Update `docs/prd.md` §4.1 row

## Validation

```powershell
uv run pytest -q
cd frontend; npm run build
```

## Rollback

Revert API + UI; collect field additive only — safe to leave mid on old rows.
