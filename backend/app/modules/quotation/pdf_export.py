"""
報價單 PDF 匯出 — 使用 reportlab 產生正式報價單文件
支援中文字型（思源黑體 Noto Sans CJK，需容器內安裝字型檔）
"""
import io
from datetime import date
from decimal import Decimal
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# reportlab內建的CID字型，無需額外安裝字型檔即可顯示中文（Adobe標準字型，Big5/繁中相容）
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

COMPANY_INFO = {
    "name": "龜山壓克力製造有限公司",
    "address": "桃園市龜山區（請於正式環境填入完整地址）",
    "phone": "(03) 000-0000",
    "tax_id": "00000000",
}


def generate_quotation_pdf(quotation: dict, customer: dict, items: list[dict]) -> bytes:
    """
    quotation: {quote_number, status, valid_until, profit_margin, final_price,
                material_cost, processing_cost, overhead_cost, notes, created_at}
    customer:  {name, contact_name, contact_email, contact_phone, billing_address}
    items:     [{line_no, description, quantity, unit_price}]
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    cn_normal = ParagraphStyle("CnNormal", fontName="STSong-Light", fontSize=10, leading=14)
    cn_title = ParagraphStyle("CnTitle", fontName="STSong-Light", fontSize=20, leading=26, alignment=1)
    cn_sub = ParagraphStyle("CnSub", fontName="STSong-Light", fontSize=9, leading=13, textColor=colors.grey)
    cn_h2 = ParagraphStyle("CnH2", fontName="STSong-Light", fontSize=12, leading=16, spaceAfter=6)

    elements = []

    # ── 標題
    elements.append(Paragraph(COMPANY_INFO["name"], cn_title))
    elements.append(Paragraph(
        f"{COMPANY_INFO['address']} ｜ 電話：{COMPANY_INFO['phone']} ｜ 統編：{COMPANY_INFO['tax_id']}",
        cn_sub
    ))
    elements.append(Spacer(1, 10 * mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1")))
    elements.append(Spacer(1, 6 * mm))

    # ── 報價單資訊
    elements.append(Paragraph(f"報價單　Quotation", cn_h2))
    info_data = [
        ["報價單號", quotation.get("quote_number", "—"), "報價日期", str(quotation.get("created_at", date.today()))[:10]],
        ["客戶名稱", customer.get("name", "—"), "有效期限", str(quotation.get("valid_until", "—"))],
        ["聯絡人", customer.get("contact_name", "—"), "聯絡電話", customer.get("contact_phone", "—")],
    ]
    info_table = Table(info_data, colWidths=[28*mm, 62*mm, 28*mm, 52*mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 8 * mm))

    # ── 報價明細
    elements.append(Paragraph("報價明細", cn_h2))
    item_rows = [["項次", "說明", "數量", "單價 (TWD)", "小計 (TWD)"]]
    for item in items:
        qty = item.get("quantity", 1)
        unit_price = Decimal(str(item.get("unit_price", 0)))
        subtotal = unit_price * qty
        item_rows.append([
            str(item.get("line_no", "")),
            item.get("description", ""),
            str(qty),
            f"{unit_price:,.0f}",
            f"{subtotal:,.0f}",
        ])
    item_table = Table(item_rows, colWidths=[15*mm, 75*mm, 20*mm, 32*mm, 28*mm])
    item_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    elements.append(item_table)
    elements.append(Spacer(1, 6 * mm))

    # ── 成本/總計摘要
    final_price = Decimal(str(quotation.get("final_price", 0)))
    summary_rows = [
        ["材料成本", f"NT$ {Decimal(str(quotation.get('material_cost', 0))):,.0f}"],
        ["加工成本", f"NT$ {Decimal(str(quotation.get('processing_cost', 0))):,.0f}"],
        ["管銷攤提", f"NT$ {Decimal(str(quotation.get('overhead_cost', 0))):,.0f}"],
        ["報價總額", f"NT$ {final_price:,.0f}"],
    ]
    summary_table = Table(summary_rows, colWidths=[120*mm, 50*mm])
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#1e293b")),
        ("TOPPADDING", (0, -1), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -2), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -2), 3),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 10 * mm))

    # ── 備註
    if quotation.get("notes"):
        elements.append(Paragraph("備註", cn_h2))
        elements.append(Paragraph(quotation["notes"], cn_normal))
        elements.append(Spacer(1, 6 * mm))

    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph(
        "本報價單有效期限內價格保證，逾期請重新確認。實際交期依生產排程確認為準。",
        cn_sub
    ))

    doc.build(elements)
    return buffer.getvalue()
