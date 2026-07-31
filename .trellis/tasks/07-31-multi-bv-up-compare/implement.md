# Implement — 多 BV / UP 口碑对比

## Checklist

1. [ ] Collect: write `mid` / `owner_name` into `raw.extra` when available
2. [ ] `services/video_report.py` (or new `compare.py`): `compare_videos(bvids, …)`
3. [ ] API router + `client.js` methods
4. [ ] pytest for compare (2 BV fixture)
5. [ ] Reports page UI: multi-select + table/chart
6. [ ] (Optional same PR) `list_ups` / `up_detail` if mid present
7. [ ] Update `docs/prd.md` §4.1 row

## Validation

```powershell
uv run pytest -q
cd frontend; npm run build
```

## Rollback

Revert API + UI; collect field additive only — safe to leave mid on old rows.
