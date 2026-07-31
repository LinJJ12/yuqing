# Design — 多 BV / UP 口碑对比

## Boundaries

| In | Out |
|----|-----|
| 已入库 bili 帖的聚合对比 | 现场再爬全 UP 稿件 |
| `raw.extra.bvid` / 计划中的 `mid` | 新的独立数据库 |

## API sketch

```http
POST /api/v1/reports/compare
{ "bvids": ["BV1xx", "BV2yy"], "with_keywords": true, "keyword_top_k": 8 }
```

Response `data.items[]`:

- `bvid`, `video_title`, `comment_count`, `positive|neutral|negative|uncertain`, `last_fetched_at`, `missing?`, `keywords?[]`

```http
GET /api/v1/reports/ups?limit=50
GET /api/v1/reports/up?mid=123&limit=50
```

UP endpoints may ship in a follow-up commit after collect writes `mid`.

## Data

- Reuse `Store.list_posts_by_bvid` / extend `list_bilibili_videos` style SQL.
- Collect path (`bilibili_collect`): when resolving video info, persist `owner.mid` → `raw.extra.mid`, `owner.name` → `raw.extra.owner_name`.

## UI

- Prefer extending **Reports** with a 「对比」 tab to avoid nav sprawl.
- Multi-select from `fetchVideoSummaries` list; max 8 chips.
- Charts: ECharts bar for sentiment shares side-by-side.

## Compatibility

- Single-video report unchanged.
- Existing `?bvid=` scope unchanged.

## Risks

- Keyword extraction on many BV × large comments → cap texts per BV (e.g. 500) and skip BERTopic.
- Legacy rows without `mid` → UP view empty until re-collect.
