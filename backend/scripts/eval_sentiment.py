# -*- coding: utf-8 -*-
"""对照黄金集评测当前情感模型（准确率 / 按类召回）。"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

EVAL_PATH = BACKEND / "data" / "samples" / "sentiment_eval.json"


def main() -> None:
    rows = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    from src.services.sentiment import get_sentiment_analyzer
    from src.config.settings import settings

    analyzer = get_sentiment_analyzer()
    print("model:", settings.sentiment_model_id)
    preds = analyzer.predict_batch([r["text"] for r in rows])

    ok = 0
    by_true: Counter[str] = Counter()
    hit_true: Counter[str] = Counter()
    confusions: list[str] = []
    for gold, pred in zip(rows, preds):
        t = gold["label"]
        p = pred["sentiment_label"]
        # uncertain 对 gold 计为错，但单独统计
        by_true[t] += 1
        match = p == t
        if match:
            ok += 1
            hit_true[t] += 1
        else:
            confusions.append(
                f"期望={t} 预测={p} conf={pred.get('confidence')} | {gold['text']}"
            )

    n = len(rows)
    print(f"accuracy: {ok}/{n} = {ok / max(n, 1):.3f}")
    for lab in ("positive", "neutral", "negative"):
        total = by_true[lab]
        hit = hit_true[lab]
        print(f"  recall[{lab}]: {hit}/{total} = {hit / max(total, 1):.3f}")
    unc = sum(1 for p in preds if p["sentiment_label"] == "uncertain")
    print(f"uncertain predictions: {unc}")
    if confusions:
        print("mismatches:")
        for line in confusions:
            print(" -", line)


if __name__ == "__main__":
    main()
