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
from src.services.bilibili_quality import (
    DEFAULT_TITLE_BLACKLIST,
    denoise_comments,
    filter_video_candidates,
)
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


def normalize_bvid(value: str | None) -> str | None:
    """从 BV / URL 提取 BV 号；解析不到则返回 None。"""
    ref = _parse_video_ref(value or "")
    bvid = ref.get("bvid")
    return str(bvid) if bvid else None


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


def _has_sessdata() -> bool:
    parsed = _parse_cookie_blob(getattr(settings, "bilibili_sessdata", None) or "")
    return bool(parsed.get("SESSDATA"))


def search_videos(
    client: httpx.Client,
    keyword: str,
    *,
    max_videos: int = 3,
    filter_titles: bool = True,
    require_keyword_hit: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """搜索视频。返回 (accepted, rejected)。关键词搜索可套用标题质量门禁。"""
    keyword = (keyword or "").strip()
    if not keyword:
        raise BilibiliCollectError("关键词不能为空")
    max_videos = max(1, min(int(max_videos), 10))
    # 多取候选再过滤，避免黑名单后数量不足
    fetch_n = max_videos * 4 if filter_titles else max_videos

    raw_videos: list[dict[str, Any]] = []
    # 1) 官方搜索 all/v2（本机实测可用）
    try:
        resp = client.get(
            "https://api.bilibili.com/x/web-interface/search/all/v2",
            params={"keyword": keyword, "page": 1, "page_size": max(20, fetch_n)},
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
                    raw_videos.append(
                        {
                            "aid": int(aid) if aid else None,
                            "bvid": bvid,
                            "title": title.strip(),
                            "owner": str(item.get("author") or "").strip(),
                            "url": f"https://www.bilibili.com/video/{bvid}" if bvid else None,
                        }
                    )
                    if len(raw_videos) >= fetch_n:
                        break
                if len(raw_videos) >= fetch_n:
                    break
    except Exception:
        pass

    # 2) HTML 搜索页提取 BV
    if len(raw_videos) < fetch_n:
        try:
            html = client.get(
                "https://search.bilibili.com/all",
                params={"keyword": keyword, "from_source": "webtop_search"},
                headers={"Accept": "text/html,application/xhtml+xml"},
            ).text
            for bvid in list(dict.fromkeys(BV_RE.findall(html))):
                if any(v.get("bvid") == bvid for v in raw_videos):
                    continue
                try:
                    raw_videos.append(resolve_video(client, bvid=bvid))
                    time.sleep(0.35)
                except BilibiliCollectError:
                    continue
                if len(raw_videos) >= fetch_n:
                    break
        except Exception as exc:
            if not raw_videos:
                raise BilibiliCollectError(f"关键词搜索失败: {exc}") from exc

    if not raw_videos:
        raise BilibiliCollectError("未搜到可用视频（可能被风控，可改用 BV 号或配置 BILIBILI_SESSDATA）")

    if not filter_titles:
        return raw_videos[:max_videos], []

    accepted, rejected = filter_video_candidates(
        raw_videos,
        keyword=keyword,
        max_videos=max_videos,
        blacklist=list(DEFAULT_TITLE_BLACKLIST),
        require_keyword_hit=require_keyword_hit,
    )
    if not accepted:
        reasons = ", ".join(
            sorted({str(r.get("reject_reason") or "") for r in rejected if r.get("reject_reason")})[:4]
        )
        raise BilibiliCollectError(
            "搜索结果均未通过标题质量门禁"
            + (f"（{reasons}）" if reasons else "")
            + "。请换更具体关键词，或改用 BV 直采，或关闭 filter_titles。"
        )
    return accepted, rejected


def fetch_comments(
    client: httpx.Client,
    aid: int,
    *,
    max_comments: int = 40,
    filter_noise: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    max_comments = max(1, min(int(max_comments), 200))
    collected: list[dict[str, Any]] = []
    seen: set[int] = set()
    logged_in = _has_sessdata()
    # 有 Cookie 时多翻几页，尽量凑够口碑样本量
    main_rounds = 20 if logged_in else 10
    classic_pages = 15 if logged_in else 8
    sleep_s = 0.55 if logged_in else 0.4

    def _append(reply: dict[str, Any]) -> None:
        if len(collected) >= max_comments * 2:
            # 先多收一点，去噪后再截断
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
            if len(collected) >= max_comments * 2:
                return
            _append(reply)
            kids = reply.get("replies")
            if isinstance(kids, list):
                _walk(kids)

    def _expand_roots(roots: list[dict[str, Any]]) -> None:
        """有 Cookie 时补拉二级回复，避免只有少量一级评。"""
        if not logged_in:
            return
        for reply in roots:
            if len(collected) >= max_comments * 2:
                return
            rcount = int(reply.get("rcount") or 0)
            kids = reply.get("replies") or []
            if rcount <= len(kids):
                continue
            root_id = reply.get("rpid")
            if not root_id:
                continue
            try:
                resp = client.get(
                    "https://api.bilibili.com/x/v2/reply/reply",
                    params={
                        "type": 1,
                        "oid": aid,
                        "root": int(root_id),
                        "ps": 20,
                        "pn": 1,
                    },
                )
                payload = resp.json()
                if payload.get("code") != 0:
                    continue
                data = payload.get("data") or {}
                _walk(data.get("replies") or [])
                time.sleep(sleep_s)
            except Exception:
                continue

    # 优先 main（带 cursor）；匿名时常只能拿少量一级 + 嵌套回复
    next_cursor = 0
    root_batch: list[dict[str, Any]] = []
    for _ in range(main_rounds):
        if len(collected) >= max_comments * 2:
            break
        resp = client.get(
            "https://api.bilibili.com/x/v2/reply/main",
            params={
                "type": 1,
                "oid": aid,
                "mode": 3,
                "next": next_cursor,
                "ps": min(30, max(20, max_comments)),
            },
        )
        payload = resp.json()
        if payload.get("code") != 0:
            break
        data = payload.get("data") or {}
        replies = data.get("replies") or []
        root_batch.extend(replies)
        _walk(replies)
        cursor = data.get("cursor") or {}
        if cursor.get("is_end"):
            break
        nxt = cursor.get("next")
        if nxt in (None, next_cursor):
            break
        next_cursor = nxt
        time.sleep(sleep_s)

    _expand_roots(root_batch[:12])

    # 回退经典分页（部分视频 main 为空时）
    if len(collected) < max(10, max_comments // 3):
        page = 1
        while len(collected) < max_comments * 2 and page <= classic_pages:
            resp = client.get(
                "https://api.bilibili.com/x/v2/reply",
                params={
                    "type": 1,
                    "oid": aid,
                    "pn": page,
                    "ps": min(30, max_comments),
                    "sort": 2,
                },
            )
            payload = resp.json()
            if payload.get("code") != 0:
                if page == 1 and not collected:
                    raise BilibiliCollectError(
                        f"拉取评论失败: {payload.get('message') or payload.get('code')}"
                    )
                break
            replies = ((payload.get("data") or {}).get("replies")) or []
            if not replies:
                break
            _walk(replies)
            page += 1
            time.sleep(sleep_s)

    if not collected:
        hint = "" if logged_in else "；未检测到 SESSDATA，建议在 backend/.env 配置 BILIBILI_SESSDATA"
        raise BilibiliCollectError(
            "未拉到评论（视频可能关闭评论" + hint + "）"
        )

    meta: dict[str, Any] = {
        "raw_fetched": len(collected),
        "logged_in": logged_in,
        "noise_filtered": {},
    }
    if filter_noise:
        kept, noise_stats = denoise_comments(collected)
        meta["noise_filtered"] = noise_stats
        collected = kept
    if not collected:
        raise BilibiliCollectError("评论均被去噪过滤，可关闭 filter_comments 重试或换视频")
    return collected[:max_comments], meta


def resolve_collect_topic(
    *,
    topic: str | None,
    keyword: str | None,
    video_titles: list[str] | None = None,
) -> str:
    """显式话题 > 搜索关键词 > 视频标题 > 默认。"""
    explicit = (topic or "").strip()[:100]
    if explicit:
        return explicit
    kw = (keyword or "").strip()
    if kw:
        return kw[:40]
    for title in video_titles or []:
        t = (title or "").strip()
        if t:
            return t[:100]
    return "B站评论"


def _to_posts(
    comments: list[dict[str, Any]],
    *,
    video: dict[str, Any],
    topic: str | None,
) -> list[dict]:
    posts: list[dict] = []
    bvid = video.get("bvid") or ""
    title = video.get("title") or ""
    base_url = video.get("url") or (f"https://www.bilibili.com/video/{bvid}" if bvid else None)
    for c in comments:
        rpid = c.get("rpid")
        # 尽量带到评论锚点，方便前端「打开原评」
        source_url = base_url
        if base_url and rpid:
            source_url = f"{base_url}#reply{rpid}"
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
            "source_url": source_url,
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
    filter_titles: bool = True,
    filter_comments: bool = True,
    require_keyword_hit: bool = True,
) -> dict[str, Any]:
    """采集并入库。keyword 与 video（BV/URL）至少填一个。"""
    keyword = (keyword or "").strip()
    video_ref = (video or "").strip()
    if not keyword and not video_ref:
        raise BilibiliCollectError("请填写关键词或视频 BV/链接")

    topic_seed = resolve_collect_topic(topic=topic, keyword=keyword, video_titles=None)
    store = get_store()
    filename = f"bilibili:{keyword or video_ref}"[:120]
    job = store.create_import_job(filename=filename, topic=topic_seed, platform="bili")

    client = _client()
    try:
        targets: list[dict[str, Any]] = []
        rejected_videos: list[dict[str, Any]] = []
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
            targets, rejected_videos = search_videos(
                client,
                keyword,
                max_videos=max_videos,
                filter_titles=filter_titles,
                require_keyword_hit=require_keyword_hit,
            )

        topic_clean = resolve_collect_topic(
            topic=topic,
            keyword=keyword,
            video_titles=[str(t.get("title") or "") for t in targets],
        )
        if topic_clean != topic_seed:
            with store.connect() as conn:
                conn.execute(
                    "UPDATE import_jobs SET topic = ? WHERE id = ?",
                    (topic_clean, job["id"]),
                )
            job["topic"] = topic_clean

        all_posts: list[dict] = []
        video_summaries: list[dict[str, Any]] = []
        noise_total: dict[str, int] = {}
        video_errors: list[str] = []
        for target in targets:
            aid = target.get("aid")
            try:
                if not aid and target.get("bvid"):
                    target = resolve_video(client, bvid=target["bvid"])
                    aid = target["aid"]
                if not aid:
                    video_errors.append(f"{target.get('bvid') or '?'}: 缺少 aid")
                    continue
                comments, cmeta = fetch_comments(
                    client,
                    int(aid),
                    max_comments=max_comments_per_video,
                    filter_noise=filter_comments,
                )
            except Exception as exc:
                video_errors.append(
                    f"{target.get('bvid') or target.get('title') or 'unknown'}: {exc}"
                )
                video_summaries.append(
                    {
                        "aid": aid,
                        "bvid": target.get("bvid"),
                        "title": target.get("title"),
                        "comments_fetched": 0,
                        "posts_normalized": 0,
                        "error": str(exc),
                    }
                )
                time.sleep(0.4)
                continue
            for reason, n in (cmeta.get("noise_filtered") or {}).items():
                noise_total[reason] = noise_total.get(reason, 0) + int(n)
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
                    "comments_raw": cmeta.get("raw_fetched"),
                    "posts_normalized": len(posts),
                    "logged_in": cmeta.get("logged_in"),
                    "noise_filtered": cmeta.get("noise_filtered") or {},
                }
            )
            time.sleep(0.55 if _has_sessdata() else 0.45)

        if not all_posts:
            detail = "；".join(video_errors[:3])
            raise BilibiliCollectError(
                "未入库任何评论（可能全部被过滤或拉取失败）"
                + (f"：{detail}" if detail else "")
            )

        inserted = store.insert_posts(job["id"], all_posts)
        notes: list[str] = []
        if not _has_sessdata():
            notes.append("未配置 BILIBILI_SESSDATA，评论量可能偏少，建议在 backend/.env 填写 Cookie")
        if rejected_videos:
            notes.append(f"标题门禁跳过 {len(rejected_videos)} 个视频")
        if noise_total:
            notes.append(
                "评论去噪："
                + "，".join(f"{k}{v}" for k, v in sorted(noise_total.items(), key=lambda x: -x[1])[:5])
            )
        if video_errors:
            notes.append(f"{len(video_errors)} 个视频采集失败（其余已入库）")

        stats = {
            "total": len(all_posts),
            "accepted": len(all_posts),
            "inserted": inserted,
            "duplicates": max(len(all_posts) - inserted, 0),
            "rejected": sum(noise_total.values()),
            "errors": video_errors[:20],
            "videos": video_summaries,
            "videos_rejected": [
                {
                    "bvid": v.get("bvid"),
                    "title": v.get("title"),
                    "reason": v.get("reject_reason"),
                }
                for v in rejected_videos[:20]
            ],
            "noise_filtered": noise_total,
            "filter_titles": filter_titles and not bool(video_ref),
            "filter_comments": filter_comments,
            "logged_in": _has_sessdata(),
            "notes": notes,
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
