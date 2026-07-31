"""删除校园样例中「同文案」重复帖，每个 text 只保留 id 最小的一条。"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from src.storage.db import get_store  # noqa: E402


def main() -> None:
    store = get_store()
    posts = store.list_posts(limit=10000)
    campus = [p for p in posts if (p.get("platform") or "") == "campus"]
    by_text: dict[str, list[dict]] = {}
    for p in campus:
        key = (p.get("text") or "").strip()
        if not key:
            continue
        by_text.setdefault(key, []).append(p)

    keep_ids: set[int] = set()
    drop_ids: list[int] = []
    for group in by_text.values():
        group.sort(key=lambda x: int(x["id"]))
        keep_ids.add(int(group[0]["id"]))
        for extra in group[1:]:
            drop_ids.append(int(extra["id"]))

    if not drop_ids:
        print(f"campus={len(campus)} unique_texts={len(by_text)} nothing to delete")
        return

    with store.connect() as conn:
        placeholders = ",".join("?" * len(drop_ids))
        conn.execute(f"DELETE FROM posts WHERE id IN ({placeholders})", drop_ids)

    print(
        f"campus_before={len(campus)} unique_texts={len(by_text)} "
        f"kept={len(keep_ids)} deleted={len(drop_ids)}"
    )


if __name__ == "__main__":
    main()
