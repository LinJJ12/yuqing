"""B 站公开评论采集（关键词搜索视频 → 拉评论 → 规范化入库）。

仅用于学习 / 大创演示；遵守平台 ToS，控制频率与条数。
搜索优先 search/all/v2；失败时回退 HTML 提取 BV 号。
可选环境变量 BILIBILI_SESSDATA 提高成功率。
"""

from __future__ import annotations

import re
import time
import uuid
from typing import Any
from urllib.parse import urlparse

import httpx

from src.config.settings import settings
from src.services.normalize import normalize_post
from src.storage.db import get_store

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

BV_RE = re.compile(r"(BV[\w]+)")
AID_RE = re.compile(r"av(\d+)", re.I)


class BilibiliCollectError(RuntimeError):
    """采集失败。"""


def _parse_cookie_blob(raw: str) -> dict[str, str]:
    """支持只填 SESSDATA，或粘贴整段浏览器 Cookie。"""
    text = (raw or "").strip()
    if not text:
        return {}
    if "=" not in text and ";" not in text:
        return {"SESSDATA": text}
    out: dict[str, str] = {}
    for part in text.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            out[key] = value
    # 若用户只写了 SESSDATA=xxx 形式也已覆盖；若整段里没有 SESSDATA 但整串像 token，保留原逻辑
    if "SESSDATA" not in out and "buvid3" not in out and len(text) < 200:
        out["SESSDATA"] = text
    return out


def _client() -> httpx.Client:
    buvid = "XY" + uuid.uuid4().hex[:32].upper()
    cookies: dict[str, str] = {"buvid3": buvid}
    parsed = _parse_cookie_blob(getattr(settings, "bilibili_sessdata", None) or "")
    cookies.update(parsed)
    if "buvid3" not in parsed:
        cookies["buvid3"] = buvid
    client = httpx.Client(
        timeout=30.0,
        headers={
            "User-Agent": UA,
            "Referer": "https://www.bilibili.com",
            "Origin": "https://www.bilibili.com",
            "Accept": "application/json, text/plain, */*",
        },
        follow_redirects=True,
        cookies=cookies,
    )
    try:
        client.get("https://www.bilibili.com")
    except Exception:
        pass
    return client


def _parse_video_ref(value: str) -> dict[str, str | int | None]:
    """从 BV / av / URL 解析标识。"""
    raw = (value or "").strip()
    if not raw:
        return {"bvid": None, "aid": None}
    bv = BV_RE.search(raw)
    if bv:
        return {"bvid": bv.group(1), "aid": None}
    av = AID_RE.search(raw)
    if av:
        return {"bvid": None, "aid": int(av.group(1))}
    if raw.isdigit():
        return {"bvid": None, "aid": int(raw)}
    try:
        path = urlparse(raw).path
        bv2 = BV_RE.search(path)
        if bv2:
            return {"bvid": bv2.group(1), "aid": None}
        av2 = AID_RE.search(path)
        if av2:
            return {"bvid": None, "aid": int(av2.group(1))}
    except Exception:
        pass
    return {"bvid": None, "aid": None}


def resolve_video(client: httpx.Client, *, bvid: str | None = None, aid: int | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if bvid:
        params["bvid"] = bvid
    elif aid:
        params["aid"] = aid
    else:
        raise BilibiliCollectError("需要 bvid 或 aid")
    resp = client.get("https://api.bilibili.com/x/web-interface/view", params=params)
    data = resp.json()
    if data.get("code") != 0 or not data.get("data"):
        raise BilibiliCollectError(f"解析视频失败: {data.get('message') or data.get('code')}")
    info = data["data"]
    return {
        "aid": int(info["aid"]),
        "bvid": info.get("bvid") or bvid,
        "title": (info.get("title") or "").strip(),
        "owner": ((info.get("owner") or {}).get("name") or "").strip(),
        "url": f"https://www.bilibili.com/video/{info.get('bvid') or bvid}",
    }


def search_videos(client: httpx.Client, keyword: str, *, max_videos: int = 3) -> list[dict[str, Any]]:
    keyword = (keyword or "").strip()
    if not keyword:
        raise BilibiliCollectError("关键词不能为空")
    max_videos = max(1, min(int(max_videos), 10))

    videos: list[dict[str, Any]] = []
    # 1) 官方搜索 all/v2（本机实测可用）
    try:
        resp = client.get(
            "https://api.bilibili.com/x/web-interface/search/all/v2",
            params={"keyword": keyword, "page": 1, "page_size": max(10, max_videos)},
            headers={"Referer": "https://search.bilibili.com"},
        )
        payload = resp.json()
        if payload.get("code") == 0:
            for block in (payload.get("data") or {}).get("result") or []:
                if block.get("result_type") != "video":
                    continue
                for item in block.get("data") or []:
                    aid = item.get("aid") or item.get("id")
                    bvid = item.get("bvid")
                    if not aid and not bvid:
                        continue
                    title = re.sub(r"<[^>]+>", "", str(item.get("title") or ""))
                    videos.append(
                        {
                            "aid": int(aid) if aid else None,
                            "bvid": bvid,
                            "title": title.strip(),
                            "owner": str(item.get("author") or "").strip(),
                            "url": f"https://www.bilibili.com/video/{bvid}" if bvid else None,
                        }
                    )
                    if len(videos) >= max_videos:
                        return videos
    except Exception:
        pass

    # 2) HTML 搜索页提取 BV
    if len(videos) < max_videos:
        try:
            html = client.get(
                "https://search.bilibili.com/all",
                params={"keyword": keyword, "from_source": "webtop_search"},
                headers={"Accept": "text/html,application/xhtml+xml"},
            ).text
            for bvid in list(dict.fromkeys(BV_RE.findall(html))):
                if any(v.get("bvid") == bvid for v in videos):
                    continue
                try:
                    videos.append(resolve_video(client, bvid=bvid))
                    time.sleep(0.35)
                except BilibiliCollectError:
                    continue
                if len(videos) >= max_videos:
                    break
        except Exception as exc:
            if not videos:
                raise BilibiliCollectError(f"关键词搜索失败: {exc}") from exc

    if not videos:
        raise BilibiliCollectError("未搜到可用视频（可能被风控，可改用 BV 号或配置 BILIBILI_SESSDATA）")
    return videos[:max_videos]


def fetch_comments(
    client: httpx.Client,
    aid: int,
    *,
    max_comments: int = 40,
) -> list[dict[str, Any]]:
    max_comments = max(1, min(int(max_comments), 200))
    collected: list[dict[str, Any]] = []
    seen: set[int] = set()

    def _append(reply: dict[str, Any]) -> None:
        if len(collected) >= max_comments:
            return
        rpid = reply.get("rpid")
        if rpid is not None:
            try:
                rid = int(rpid)
            except (TypeError, ValueError):
                rid = None
            if rid is not None:
                if rid in seen:
                    return
                seen.add(rid)
        content = ((reply.get("content") or {}).get("message") or "").strip()
        if not content:
            return
        member = reply.get("member") or {}
        collected.append(
            {
                "rpid": rpid,
                "text": content,
                "author": member.get("uname") or "",
                "published_at": reply.get("ctime"),
                "likes": reply.get("like") or 0,
                "root": reply.get("root") or 0,
                "parent": reply.get("parent") or 0,
            }
        )

    def _walk(replies: list[dict[str, Any]] | None) -> None:
        if not replies:
            return
        for reply in replies:
            if len(collected) >= max_comments:
                return
            _append(reply)
            kids = reply.get("replies")
            if isinstance(kids, list):
                _walk(kids)

    # 优先 main（带 cursor）；匿名时常只能拿少量一级 + 嵌套回复
    next_cursor = 0
    for _ in range(8):
        if len(collected) >= max_comments:
            break
        resp = client.get(
            "https://api.bilibili.com/x/v2/reply/main",
            params={
                "type": 1,
                "oid": aid,
                "mode": 3,
                "next": next_cursor,
                "ps": min(20, max_comments),
            },
        )
        payload = resp.json()
        if payload.get("code") != 0:
            break
        data = payload.get("data") or {}
        _walk(data.get("replies") or [])
        cursor = data.get("cursor") or {}
        if cursor.get("is_end"):
            break
        nxt = cursor.get("next")
        if nxt in (None, next_cursor):
            break
        next_cursor = nxt
        time.sleep(0.4)

    # 回退经典分页（部分视频 main 为空时）
    if not collected:
        page = 1
        while len(collected) < max_comments and page <= 10:
            resp = client.get(
                "https://api.bilibili.com/x/v2/reply",
                params={
                    "type": 1,
                    "oid": aid,
                    "pn": page,
                    "ps": min(20, max_comments),
                    "sort": 2,
                },
            )
            payload = resp.json()
            if payload.get("code") != 0:
                if page == 1:
                    raise BilibiliCollectError(
                        f"拉取评论失败: {payload.get('message') or payload.get('code')}"
                    )
                break
            replies = ((payload.get("data") or {}).get("replies")) or []
            if not replies:
                break
            _walk(replies)
            page += 1
            time.sleep(0.4)

    if not collected:
        raise BilibiliCollectError(
            "未拉到评论（视频可能关闭评论，或需配置 BILIBILI_SESSDATA）"
        )
    return collected[:max_comments]


def _to_posts(
    comments: list[dict[str, Any]],
    *,
    video: dict[str, Any],
    topic: str | None,
) -> list[dict]:
    posts: list[dict] = []
    bvid = video.get("bvid") or ""
    title = video.get("title") or ""
    for c in comments:
        rpid = c.get("rpid")
        record = {
            "id": f"bili-cmt-{rpid}" if rpid else None,
            "text": c.get("text"),
            "author": c.get("author"),
            "published_at": c.get("published_at"),
            "likes": c.get("likes") or 0,
            "comments": 0,
            "reposts": 0,
            "platform": "bili",
            "topic": topic,
            "source_url": video.get("url") or (f"https://www.bilibili.com/video/{bvid}" if bvid else None),
            "extra": {
                "video_title": title,
                "bvid": bvid,
                "aid": video.get("aid"),
                "rpid": rpid,
            },
        }
        try:
            posts.append(normalize_post(record, platform="bili", topic=topic))
        except ValueError:
            continue
    return posts


def collect_bilibili(
    *,
    keyword: str | None = None,
    video: str | None = None,
    topic: str | None = None,
    max_videos: int = 3,
    max_comments_per_video: int = 40,
    include_video_title: bool = False,
) -> dict[str, Any]:
    """采集并入库。keyword 与 video（BV/URL）至少填一个。"""
    keyword = (keyword or "").strip()
    video_ref = (video or "").strip()
    if not keyword and not video_ref:
        raise BilibiliCollectError("请填写关键词或视频 BV/链接")

    topic_clean = (topic or "").strip()[:100] or (keyword[:40] if keyword else "B站评论")
    store = get_store()
    filename = f"bilibili:{keyword or video_ref}"[:120]
    job = store.create_import_job(filename=filename, topic=topic_clean, platform="bili")

    client = _client()
    try:
        targets: list[dict[str, Any]] = []
        if video_ref:
            ref = _parse_video_ref(video_ref)
            if not ref["bvid"] and not ref["aid"]:
                raise BilibiliCollectError("无法从输入解析 BV / av 号")
            targets.append(
                resolve_video(
                    client,
                    bvid=str(ref["bvid"]) if ref["bvid"] else None,
                    aid=int(ref["aid"]) if ref["aid"] else None,
                )
            )
        else:
            targets = search_videos(client, keyword, max_videos=max_videos)

        all_posts: list[dict] = []
        video_summaries: list[dict[str, Any]] = []
        for target in targets:
            aid = target.get("aid")
            if not aid and target.get("bvid"):
                target = resolve_video(client, bvid=target["bvid"])
                aid = target["aid"]
            if not aid:
                continue
            comments = fetch_comments(
                client,
                int(aid),
                max_comments=max_comments_per_video,
            )
            posts = _to_posts(comments, video=target, topic=topic_clean)
            if include_video_title and target.get("title"):
                try:
                    posts.insert(
                        0,
                        normalize_post(
                            {
                                "id": f"bili-av-{aid}",
                                "text": target["title"],
                                "author": target.get("owner") or "",
                                "platform": "bili",
                                "topic": topic_clean,
                                "source_url": target.get("url"),
                            },
                            platform="bili",
                            topic=topic_clean,
                        ),
                    )
                except ValueError:
                    pass
            all_posts.extend(posts)
            video_summaries.append(
                {
                    "aid": aid,
                    "bvid": target.get("bvid"),
                    "title": target.get("title"),
                    "comments_fetched": len(comments),
                    "posts_normalized": len(posts),
                }
            )
            time.sleep(0.5)

        inserted = store.insert_posts(job["id"], all_posts)
        stats = {
            "total": len(all_posts),
            "accepted": len(all_posts),
            "inserted": inserted,
            "duplicates": max(len(all_posts) - inserted, 0),
            "rejected": 0,
            "errors": [],
            "videos": video_summaries,
            "source": "bilibili_collect",
        }
        finished = store.finish_import_job(job["id"], status="succeeded", stats=stats)
        return finished
    except Exception as exc:
        return store.finish_import_job(
            job["id"],
            status="failed",
            error_message=str(exc),
        )
    finally:
        client.close()
