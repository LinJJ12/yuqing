"""报告导出：CSV / PDF；可选 OpenAI 兼容 LLM 摘要。"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from src.config.settings import settings
from src.services.forecast import build_report_summary, detect_alerts


_LABEL_ZH = {
    "positive": "正面",
    "neutral": "中性",
    "negative": "负面",
    "unknown": "未标注",
}


def _find_cjk_font() -> str | None:
    candidates = [
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\msyh.ttf"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def _xml(text: Any) -> str:
    """ReportLab Paragraph 按类 XML 解析，用户文本必须转义。"""
    return escape(str(text if text is not None else ""), {"\"": "&quot;"})


def _register_cjk_font() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    if "YuqingCJK" in pdfmetrics.getRegisteredFontNames():
        return "YuqingCJK"
    font_path = _find_cjk_font()
    if not font_path:
        return "Helvetica"
    try:
        if font_path.lower().endswith(".ttc"):
            pdfmetrics.registerFont(TTFont("YuqingCJK", font_path, subfontIndex=0))
        else:
            pdfmetrics.registerFont(TTFont("YuqingCJK", font_path))
        return "YuqingCJK"
    except Exception:
        try:
            pdfmetrics.registerFont(TTFont("YuqingCJK", font_path, subfontIndex=1))
            return "YuqingCJK"
        except Exception:
            return "Helvetica"


def build_csv_bytes(summary: dict[str, Any] | None = None) -> bytes:
    data = summary or build_report_summary()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["舆情报告导出"])
    writer.writerow(["生成时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow([])
    writer.writerow(["指标", "数值"])
    writer.writerow(["帖子总量", data.get("overview", {}).get("total_posts", 0)])
    writer.writerow(["情感已分析", data.get("sentiment", {}).get("bert_done", 0)])
    writer.writerow(["预警总数", data.get("alerts", {}).get("total", 0)])
    writer.writerow(["高风险预警", data.get("alerts", {}).get("high", 0)])
    writer.writerow([])
    writer.writerow(["情感分布"])
    writer.writerow(["标签", "方法", "数量"])
    for row in data.get("sentiment", {}).get("breakdown", []):
        writer.writerow(
            [
                _LABEL_ZH.get(row.get("label"), row.get("label")),
                row.get("method"),
                row.get("count"),
            ]
        )
    writer.writerow([])
    writer.writerow(["话题统计"])
    writer.writerow(["话题", "数量"])
    for row in data.get("overview", {}).get("by_topic", []):
        writer.writerow([row.get("topic"), row.get("count")])
    writer.writerow([])
    writer.writerow(["趋势（日）"])
    writer.writerow(["日期", "发帖量", "滑动平均", "增长率", "Prophet预测"])
    for row in data.get("trend", []):
        writer.writerow(
            [
                row.get("day"),
                row.get("count"),
                row.get("rolling_mean"),
                row.get("growth_rate"),
                row.get("prophet_yhat", ""),
            ]
        )
    writer.writerow([])
    writer.writerow(["预警明细"])
    writer.writerow(["级别", "标题", "内容", "关键词", "时间"])
    for item in data.get("alerts", {}).get("items", []):
        writer.writerow(
            [
                item.get("severity"),
                item.get("title"),
                item.get("message"),
                "、".join(item.get("keywords") or []),
                item.get("created_at"),
            ]
        )
    if data.get("ai_summary"):
        writer.writerow([])
        writer.writerow(["AI 摘要"])
        writer.writerow([data["ai_summary"]])
    return buf.getvalue().encode("utf-8-sig")


def build_pdf_bytes(summary: dict[str, Any] | None = None) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    data = summary or build_report_summary()
    buf = io.BytesIO()
    font_name = _register_cjk_font()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCN",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=16,
        spaceAfter=12,
    )
    h_style = ParagraphStyle(
        "HeadingCN",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=12,
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyCN",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        leading=14,
    )

    story: list[Any] = []
    story.append(Paragraph(_xml(data.get("generated_for") or "舆情报告"), title_style))
    story.append(
        Paragraph(
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            body_style,
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    overview = data.get("overview") or {}
    sentiment = data.get("sentiment") or {}
    alerts = data.get("alerts") or {}
    kpi_rows = [
        ["指标", "数值"],
        ["帖子总量", str(overview.get("total_posts", 0))],
        ["情感已分析", str(sentiment.get("bert_done", 0))],
        ["预警总数", str(alerts.get("total", 0))],
        ["高风险预警", str(alerts.get("high", 0))],
    ]
    table = Table(kpi_rows, colWidths=[8 * cm, 6 * cm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(table)

    story.append(Paragraph("情感分布", h_style))
    for row in sentiment.get("breakdown", []):
        label = _LABEL_ZH.get(row.get("label"), row.get("label"))
        story.append(
            Paragraph(
                f"· {_xml(label)}（{_xml(row.get('method'))}）：{_xml(row.get('count'))} 条",
                body_style,
            )
        )

    story.append(Paragraph("话题 Top", h_style))
    for row in overview.get("by_topic", [])[:8]:
        story.append(
            Paragraph(
                f"· {_xml(row.get('topic'))}：{_xml(row.get('count'))} 条",
                body_style,
            )
        )

    story.append(Paragraph("预警摘要", h_style))
    items = alerts.get("items") or detect_alerts()[:8]
    if not items:
        story.append(Paragraph("暂无预警。", body_style))
    for item in items[:8]:
        story.append(
            Paragraph(
                f"[{_xml(item.get('severity'))}] {_xml(item.get('title'))} — {_xml(item.get('message'))}",
                body_style,
            )
        )

    if data.get("ai_summary"):
        story.append(Paragraph("AI 摘要", h_style))
        for line in str(data["ai_summary"]).splitlines() or [data["ai_summary"]]:
            story.append(Paragraph(_xml(line), body_style))

    story.append(Paragraph("说明", h_style))
    for note in data.get("notes") or []:
        story.append(Paragraph(f"· {_xml(note)}", body_style))

    doc.build(story)
    return buf.getvalue()


def generate_ai_summary(summary: dict[str, Any] | None = None) -> dict[str, Any]:
    """调用 OpenAI 兼容接口生成报告摘要；未配置 Key 时返回明确提示。"""
    data = summary or build_report_summary()
    if not settings.has_cloud_llm:
        return {
            "enabled": False,
            "summary": None,
            "message": "未配置 OPENAI_API_KEY，跳过 AI 摘要",
        }

    overview = data.get("overview") or {}
    sentiment = data.get("sentiment") or {}
    alerts = data.get("alerts") or {}
    topics = overview.get("by_topic") or []
    prompt = (
        "你是舆情分析助手。根据以下统计写一段 150～250 字中文摘要，"
        "包含总体态势、主要话题、风险点与建议，语气客观。\n\n"
        f"帖子总量：{overview.get('total_posts', 0)}\n"
        f"情感已分析：{sentiment.get('bert_done', 0)}\n"
        f"情感分布：{sentiment.get('breakdown', [])}\n"
        f"话题：{topics[:8]}\n"
        f"预警：共 {alerts.get('total', 0)} 条，高风险 {alerts.get('high', 0)}\n"
        f"预警样例：{(alerts.get('items') or [])[:5]}\n"
    )
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=60.0,
        )
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": "你擅长简洁清晰的舆情简报。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=600,
        )
        text = (resp.choices[0].message.content or "").strip()
        return {"enabled": True, "summary": text, "message": "ok"}
    except Exception as exc:
        return {
            "enabled": True,
            "summary": None,
            "message": f"LLM 调用失败: {exc}",
        }
