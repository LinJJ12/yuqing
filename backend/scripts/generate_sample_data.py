"""生成可选样例数据（校园主题演示包）并写入 backend/data/samples。"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
OUT = BACKEND_ROOT / "data" / "samples"
OUT.mkdir(parents=True, exist_ok=True)

TOPICS = {
    "食堂": [
        "一食堂菜品今天有改善，味道满意，推荐黄焖鸡。",
        "三食堂排队久到离谱，窗口太少，希望后勤尽快处理。",
        "食堂米饭偏硬，但价格还算合理，总体中性评价。",
        "新开的轻食窗口干净又好吃，给后勤点赞。",
        "外卖进不了宿舍，只能吃食堂，选择太少有点失望。",
    ],
    "宿舍": [
        "宿舍热水晚上经常故障，报修两天还没修好，投诉。",
        "寝室楼卫生比上周干净多了，宿管老师很负责。",
        "空调开放时间延长了，住着舒服不少。",
        "隔壁施工噪音大，影响休息，希望学校协调。",
        "宿舍网络延迟高，打网游基本卡死。",
    ],
    "图书馆": [
        "图书馆座位预约系统终于稳定了，体验优秀。",
        "自习区有人占座不学习，管理需要加强。",
        "新到的专业书很全，考研复习方便。",
        "闭馆时间提前了，周五晚上没法学习，有点不满。",
        "安静区纪律好，适合深度学习。",
    ],
    "教务": [
        "选课系统崩了半小时，教务处公告来得及时。",
        "培养方案更新说明写得很清楚，感谢教务老师。",
        "期末考试安排冲突，希望能尽快协调。",
        "成绩录入延迟，查询一直转圈。",
        "转专业政策比去年更透明。",
    ],
    "就业": [
        "春季招聘会企业质量不错，拿到两个面试机会。",
        "就业指导讲座干货少，有点失望。",
        "简历门诊老师给的修改建议很实用。",
        "实习认定流程太繁琐，材料来回跑。",
        "校友分享会推荐，对求职很有帮助。",
    ],
    "校园网": [
        "宿舍校园网今晚又掉线，学习直播中断，差评。",
        "教学楼无线网速提升明显，网课流畅。",
        "校园网认证页面偶尔打不开。",
        "VPN 访问知网方便多了，点赞。",
        "凌晨限速太狠，下载课件都很慢。",
    ],
}

AUTHORS = ["同学A", "同学B", "匿名用户", "研一某", "大三某", "后勤观察"]


def main() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    posts = []
    idx = 1
    for day_offset in range(10, -1, -1):
        day = now - timedelta(days=day_offset)
        for topic, texts in TOPICS.items():
            for text in random.sample(texts, k=2):
                posts.append(
                    {
                        "id": f"campus-{idx:04d}",
                        "text": text,
                        "author": random.choice(AUTHORS),
                        "created_at": (day - timedelta(hours=random.randint(0, 20))).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "likes": random.randint(0, 80),
                        "comments": random.randint(0, 30),
                        "reposts": random.randint(0, 15),
                        "topic": topic,
                        "source_url": f"https://example.edu/post/{idx}",
                    }
                )
                idx += 1

    path = OUT / "campus_sample.json"
    path.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(posts)} posts -> {path}")


if __name__ == "__main__":
    main()
