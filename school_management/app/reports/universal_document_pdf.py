"""
EduManage Pro - Universal Template-Driven PDF Document Generator (ReportLab)
Renders all 10 official institutional document types strictly from a configurable
DocumentTemplate + school branding + logo + signatures + custom fields + QR verification.
Never hard-codes a single school's design.
"""

from datetime import date
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A5, letter as LETTER, landscape, portrait
from reportlab.lib.units import inch
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from app.utils.qr_generator import generate_qr_matrix


def _hex(color_str: Any, fallback: str = "#1E3A8A") -> colors.Color:
    try:
        val = str(color_str or fallback).strip()
        if not val.startswith("#"):
            val = "#" + val
        return colors.HexColor(val)
    except Exception:
        return colors.HexColor(fallback)


def _font_pair(font_family: str) -> Tuple[str, str, str]:
    fam = (font_family or "Helvetica").strip()
    if fam == "Times-Roman":
        return "Times-Roman", "Times-Bold", "Times-Italic"
    if fam == "Courier":
        return "Courier", "Courier-Bold", "Courier-Oblique"
    return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"


def _resolve_pagesize(page_size: str, orientation: str) -> Tuple[float, float]:
    ps = (page_size or "A4").strip().upper()
    orient = (orientation or "Portrait").strip().lower()
    if ps == "CR80":
        base = (2.125 * inch, 3.375 * inch)
        return landscape(base) if orient == "landscape" else portrait(base)
    if ps == "A5":
        base = A5
    elif ps == "LETTER":
        base = LETTER
    else:
        base = A4
    return landscape(base) if orient == "landscape" else portrait(base)


def _draw_qr_matrix(c: canvas.Canvas, payload: str, x: float, y: float, size: float, border_color: colors.Color) -> None:
    matrix = generate_qr_matrix(payload or "EDUMANAGE")
    dim = len(matrix)
    if dim <= 0:
        return
    cell = size / float(dim)
    c.saveState()
    c.setFillColor(colors.white)
    c.setStrokeColor(border_color)
    c.setLineWidth(0.7)
    c.rect(x, y, size, size, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#0F172A"))
    for r_idx, row in enumerate(matrix):
        for c_idx, val in enumerate(row):
            if val:
                rx = x + c_idx * cell
                ry = y + size - (r_idx + 1) * cell
                c.rect(rx, ry, cell, cell, fill=1, stroke=0)
    c.restoreState()


def _draw_image_safe(
    c: canvas.Canvas,
    img_path: Any,
    x: float,
    y: float,
    w: float,
    h: float,
    mask: str = "auto",
) -> bool:
    if not img_path:
        return False
    p = Path(str(img_path))
    if not p.exists() or not p.is_file():
        return False
    try:
        c.drawImage(
            str(p),
            x,
            y,
            width=w,
            height=h,
            preserveAspectRatio=True,
            anchor="c",
            mask=mask,
        )
        return True
    except Exception:
        return False


def _draw_logo_or_crest(
    c: canvas.Canvas,
    logo_path: Any,
    school_name: str,
    x: float,
    y: float,
    size: float,
    primary: colors.Color,
    accent: colors.Color,
) -> None:
    if _draw_image_safe(c, logo_path, x, y, size, size):
        return
    # Dynamic vector crest monogram from school initials
    words = [w for w in (school_name or "ED").split() if w and w[0].isalnum()]
    initials = "".join(w[0].upper() for w in words[:2]) or "ED"
    c.saveState()
    c.setFillColor(primary)
    c.setStrokeColor(accent)
    c.setLineWidth(1.5)
    c.circle(x + size / 2.0, y + size / 2.0, size / 2.0 - 1, fill=1, stroke=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", max(7.0, size * 0.36))
    c.drawCentredString(x + size / 2.0, y + size / 2.0 - size * 0.13, initials)
    c.restoreState()


def _draw_border(
    c: canvas.Canvas,
    page_w: float,
    page_h: float,
    style_name: str,
    primary: colors.Color,
    accent: colors.Color,
    compact: bool = False,
) -> float:
    st = (style_name or "Classic").strip()
    if st == "None":
        return 14.0 if compact else 28.0
    m = 8.0 if compact else 22.0
    c.saveState()
    if st == "Double":
        c.setStrokeColor(primary)
        c.setLineWidth(2.2 if compact else 3.2)
        c.rect(m, m, page_w - 2 * m, page_h - 2 * m, fill=0, stroke=1)
        inner = m + (4 if compact else 8)
        c.setStrokeColor(accent)
        c.setLineWidth(0.9 if compact else 1.4)
        c.rect(inner, inner, page_w - 2 * inner, page_h - 2 * inner, fill=0, stroke=1)
        if not compact:
            c.setFillColor(accent)
            for cx, cy in [
                (inner, inner),
                (page_w - inner, inner),
                (inner, page_h - inner),
                (page_w - inner, page_h - inner),
            ]:
                c.circle(cx, cy, 3.5, fill=1, stroke=0)
        c.restoreState()
        return inner + (8 if compact else 14)
    elif st == "Modern":
        c.setStrokeColor(primary)
        c.setLineWidth(1.2 if compact else 1.8)
        c.roundRect(m, m, page_w - 2 * m, page_h - 2 * m, 6 if compact else 10, fill=0, stroke=1)
        c.restoreState()
        return m + (8 if compact else 14)
    elif st == "Minimal":
        c.setStrokeColor(accent)
        c.setLineWidth(0.8)
        c.rect(m, m, page_w - 2 * m, page_h - 2 * m, fill=0, stroke=1)
        c.restoreState()
        return m + (8 if compact else 12)
    else:  # Classic
        c.setStrokeColor(primary)
        c.setLineWidth(1.8 if compact else 2.2)
        c.rect(m, m, page_w - 2 * m, page_h - 2 * m, fill=0, stroke=1)
        c.restoreState()
        return m + (8 if compact else 14)


def _draw_watermark(c: canvas.Canvas, page_w: float, page_h: float, text: Any) -> None:
    wm = str(text or "").strip()
    if not wm:
        return
    c.saveState()
    c.translate(page_w / 2.0, page_h / 2.0)
    c.rotate(30)
    c.setFillColor(colors.Color(0.65, 0.70, 0.78, alpha=0.14))
    c.setFont("Helvetica-Bold", max(18.0, min(page_w, page_h) * 0.08))
    c.drawCentredString(0, 0, wm.upper()[:32])
    c.restoreState()


def _draw_signatures_and_seal(
    c: canvas.Canvas,
    tpl: Any,
    school_info: Dict[str, Any],
    left_x: float,
    right_x: float,
    base_y: float,
    center_x: float,
    primary: colors.Color,
    accent: colors.Color,
    text_col: colors.Color,
    font_reg: str,
    font_bold: str,
) -> None:
    if getattr(tpl, "show_seal", True):
        seal_drawn = _draw_image_safe(c, school_info.get("seal_image_path"), center_x - 24, base_y + 4, 48, 48)
        if not seal_drawn:
            c.saveState()
            c.setStrokeColor(accent)
            c.setFillColor(colors.Color(0.98, 0.96, 0.88, alpha=0.9))
            c.setLineWidth(1.5)
            c.circle(center_x, base_y + 26, 23, fill=1, stroke=1)
            c.setFillColor(accent)
            c.setFont(font_bold, 6.5)
            c.drawCentredString(center_x, base_y + 29, "OFFICIAL")
            c.drawCentredString(center_x, base_y + 20, "SEAL")
            c.restoreState()

    if not getattr(tpl, "show_signatures", True):
        return

    line_w = 135.0
    c.saveState()
    # Left Signature
    _draw_image_safe(c, school_info.get("signature_left_image_path"), left_x + 15, base_y + 22, line_w - 30, 26)
    c.setStrokeColor(text_col)
    c.setLineWidth(0.8)
    c.line(left_x, base_y + 20, left_x + line_w, base_y + 20)
    c.setFillColor(text_col)
    c.setFont(font_bold, 8.5)
    left_lbl = getattr(tpl, "signature_left_label", None) or "Registrar / Officer"
    c.drawCentredString(left_x + line_w / 2.0, base_y + 8, left_lbl[:32])
    left_name = getattr(tpl, "signature_left_name", None)
    if left_name:
        c.setFont(font_reg, 7.5)
        c.drawCentredString(left_x + line_w / 2.0, base_y - 2, str(left_name)[:32])

    # Right Signature
    _draw_image_safe(c, school_info.get("signature_right_image_path"), right_x - line_w + 15, base_y + 22, line_w - 30, 26)
    c.setStrokeColor(text_col)
    c.line(right_x - line_w, base_y + 20, right_x, base_y + 20)
    c.setFillColor(text_col)
    c.setFont(font_bold, 8.5)
    right_lbl = getattr(tpl, "signature_right_label", None) or "Principal"
    right_name = getattr(tpl, "signature_right_name", None) or school_info.get("principal_name") or ""
    if right_name:
        c.drawCentredString(right_x - line_w / 2.0, base_y + 8, str(right_name)[:32])
        c.setFont(font_reg, 7.5)
        c.drawCentredString(right_x - line_w / 2.0, base_y - 2, str(right_lbl)[:32])
    else:
        c.drawCentredString(right_x - line_w / 2.0, base_y + 8, str(right_lbl)[:32])
    c.restoreState()


class UniversalDocumentPDFGenerator:
    """
    Renders any payload from DocumentService.preview_document_data() or
    DocumentService.document_to_render_payload() to a crisp PDF.
    """

    @classmethod
    def generate_pdf(cls, payload: Dict[str, Any], output_pdf_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        tpl = payload["template"]
        page_w, page_h = _resolve_pagesize(tpl.page_size, tpl.orientation)
        c = canvas.Canvas(output_pdf_path, pagesize=(page_w, page_h))
        cls.draw_document_page(c, payload, page_w, page_h)
        c.showPage()
        c.save()
        return output_pdf_path

    @classmethod
    def generate_batch_id_sheet(cls, payloads: List[Dict[str, Any]], output_pdf_path: str) -> str:
        """Render up to 8 CR80 ID cards per Portrait A4 page using each card's template."""
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        page_w, page_h = portrait(A4)
        c = canvas.Canvas(output_pdf_path, pagesize=(page_w, page_h))
        card_w = 3.375 * inch
        card_h = 2.125 * inch
        margin_x = (page_w - (2 * card_w + 24)) / 2.0
        top_start_y = page_h - 48 - card_h

        for idx, payload in enumerate(payloads):
            pos = idx % 8
            if idx > 0 and pos == 0:
                c.showPage()
            col = pos % 2
            row = pos // 2
            x0 = margin_x + col * (card_w + 24)
            y0 = top_start_y - row * (card_h + 18)
            c.saveState()
            c.translate(x0, y0)
            cls._draw_id_card(c, payload, card_w, card_h)
            c.restoreState()

        c.showPage()
        c.save()
        return output_pdf_path

    @classmethod
    def draw_document_page(cls, c: canvas.Canvas, payload: Dict[str, Any], page_w: float, page_h: float) -> None:
        doc_type = payload.get("document_type", "Bonafide Certificate")
        tpl = payload["template"]
        if doc_type == "ID Card" or str(getattr(tpl, "page_size", "")).upper() == "CR80":
            cls._draw_id_card(c, payload, page_w, page_h)
        elif doc_type in ("Admission Receipt", "Fee Receipt"):
            cls._draw_receipt(c, payload, page_w, page_h)
        elif doc_type in ("Mark Sheet", "Report Card"):
            cls._draw_academic_transcript(c, payload, page_w, page_h)
        else:
            cls._draw_certificate(c, payload, page_w, page_h)

    # ------------------------------------------------------------------ #
    # 1. ID CARD (CR80 or Custom Card)
    # ------------------------------------------------------------------ #
    @classmethod
    def _draw_id_card(cls, c: canvas.Canvas, payload: Dict[str, Any], w: float, h: float) -> None:
        tpl = payload["template"]
        school = payload.get("school_info", {})
        rec = payload.get("recipient_info", {})
        primary = _hex(tpl.primary_color, "#1E3A8A")
        secondary = _hex(tpl.secondary_color, "#0F172A")
        accent = _hex(tpl.accent_color, "#D97706")
        text_col = _hex(tpl.text_color, "#0F172A")
        bg_col = _hex(tpl.background_color, "#FFFFFF")
        f_reg, f_bold, _ = _font_pair(tpl.font_family)

        c.saveState()
        c.setFillColor(bg_col)
        c.roundRect(0, 0, w, h, 6, fill=1, stroke=0)
        if getattr(tpl, "show_border", True):
            c.setStrokeColor(primary)
            c.setLineWidth(1.2)
            c.roundRect(1, 1, w - 2, h - 2, 6, fill=0, stroke=1)

        # Header Band
        band_h = 34.0
        c.setFillColor(primary)
        c.rect(1, h - band_h, w - 2, band_h - 1, fill=1, stroke=0)

        if getattr(tpl, "show_logo", True):
            _draw_logo_or_crest(c, school.get("logo_path"), school.get("school_name", "School"), 8, h - 28, 22, secondary, accent)

        text_center = w / 2.0 + (8 if getattr(tpl, "show_logo", True) else 0)
        c.setFillColor(colors.white)
        c.setFont(f_bold, 8.0)
        c.drawCentredString(text_center, h - 14, str(school.get("school_name", "Institution"))[:34])
        c.setFont(f_reg, 5.8)
        c.drawCentredString(text_center, h - 25, str(payload.get("rendered_header") or "IDENTITY CARD")[:42])

        # Photo Box
        px, py, pw, ph = 10, 22, 46, 58
        if getattr(tpl, "show_photo", True):
            c.setFillColor(colors.HexColor("#F1F5F9"))
            c.setStrokeColor(accent)
            c.setLineWidth(0.8)
            c.rect(px, py, pw, ph, fill=1, stroke=1)
            if not _draw_image_safe(c, rec.get("photo_path"), px + 1, py + 1, pw - 2, ph - 2):
                c.setFillColor(colors.HexColor("#64748B"))
                c.setFont(f_reg, 6.0)
                c.drawCentredString(px + pw / 2.0, py + ph / 2.0 - 2, "PHOTO")
            info_x = px + pw + 8
        else:
            info_x = 12

        iy = h - band_h - 14
        c.setFillColor(text_col)
        c.setFont(f_bold, 8.5)
        c.drawString(info_x, iy, str(rec.get("recipient_name", ""))[:22])
        c.setFont(f_reg, 6.6)
        c.drawString(info_x, iy - 11, f"ID: {rec.get('recipient_code', '-')}")
        c.drawString(info_x, iy - 21, str(rec.get("class_or_designation", ""))[:30])
        c.drawString(info_x, iy - 31, f"Blood: {rec.get('blood_group', 'N/A')} | Tel: {rec.get('emergency_contact', '-')[:14]}")

        cf_list = payload.get("custom_fields_display", [])
        if getattr(tpl, "show_custom_fields", True) and cf_list:
            cf = cf_list[0]
            c.drawString(info_x, iy - 41, f"{cf['label'][:12]}: {cf['value'][:18]}")

        if getattr(tpl, "show_qr", True):
            _draw_qr_matrix(c, payload.get("qr_payload", ""), w - 44, 18, 36, accent)

        # Signature mini
        if getattr(tpl, "show_signatures", True):
            _draw_image_safe(c, school.get("signature_right_image_path"), w - 92, 18, 42, 14)

        # Footer Bar
        c.setFillColor(secondary)
        c.rect(1, 1, w - 2, 14, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont(f_reg, 5.4)
        if getattr(tpl, "show_serial", True):
            c.drawString(8, 5, f"SN: {payload.get('serial_number', '')}")
        c.drawRightString(w - 8, 5, str(getattr(tpl, "signature_right_label", "Authorized") or "Authorized")[:28])
        c.restoreState()

    # ------------------------------------------------------------------ #
    # 2. CERTIFICATES (Character, Transfer, Bonafide, Study, Leaving)
    # ------------------------------------------------------------------ #
    @classmethod
    def _draw_certificate(cls, c: canvas.Canvas, payload: Dict[str, Any], w: float, h: float) -> None:
        tpl = payload["template"]
        school = payload.get("school_info", {})
        rec = payload.get("recipient_info", {})
        primary = _hex(tpl.primary_color, "#1E3A8A")
        secondary = _hex(tpl.secondary_color, "#0F172A")
        accent = _hex(tpl.accent_color, "#D97706")
        text_col = _hex(tpl.text_color, "#1E293B")
        bg_col = _hex(tpl.background_color, "#FFFFFF")
        f_reg, f_bold, f_ital = _font_pair(tpl.font_family)

        c.saveState()
        c.setFillColor(bg_col)
        c.rect(0, 0, w, h, fill=1, stroke=0)
        _draw_watermark(c, w, h, getattr(tpl, "watermark_text", None) or school.get("school_name", ""))
        margin = _draw_border(c, w, h, tpl.border_style if getattr(tpl, "show_border", True) else "None", primary, accent)

        # Top Serial & Verification Bar
        y_top = h - margin - 8
        c.setFillColor(colors.HexColor("#475569"))
        c.setFont("Helvetica-Bold", 8.0)
        if getattr(tpl, "show_serial", True):
            c.drawString(margin + 6, y_top, f"SERIAL NO: {payload.get('serial_number', '')}")
            c.drawRightString(w - margin - 6, y_top, f"VERIFY TOKEN: {payload.get('verification_code', '')}")

        # School Header + Logo
        header_y = y_top - 24
        if getattr(tpl, "show_logo", True):
            _draw_logo_or_crest(c, school.get("logo_path"), school.get("school_name", "School"), margin + 10, header_y - 26, 48, primary, accent)

        c.setFillColor(primary)
        c.setFont(f_bold, 19)
        c.drawCentredString(w / 2.0, header_y, str(school.get("school_name", "Institution")).upper()[:54])

        c.setFillColor(colors.HexColor("#475569"))
        c.setFont(f_ital, 9.5)
        sub_parts = [p for p in [school.get("motto"), f"EIIN: {school.get('eiin_number')}" if school.get("eiin_number") else None, school.get("address")] if p]
        c.drawCentredString(w / 2.0, header_y - 16, "  |  ".join(sub_parts)[:105])

        # Certificate Ribbon Banner
        ribbon_w = min(400.0, w - 2 * margin - 60)
        ribbon_h = 30.0
        ribbon_x = (w - ribbon_w) / 2.0
        ribbon_y = header_y - 56
        c.setFillColor(primary)
        c.roundRect(ribbon_x, ribbon_y, ribbon_w, ribbon_h, 5, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont(f_bold, 13.5)
        c.drawCentredString(w / 2.0, ribbon_y + 10, str(payload.get("rendered_header") or payload.get("document_type", "")).upper())

        # Optional Photo Top-Right
        if getattr(tpl, "show_photo", False):
            px = w - margin - 72
            py = ribbon_y - 10
            c.setFillColor(colors.HexColor("#F8FAFC"))
            c.setStrokeColor(accent)
            c.rect(px, py, 56, 68, fill=1, stroke=1)
            if not _draw_image_safe(c, rec.get("photo_path"), px + 1, py + 1, 54, 66):
                c.setFillColor(colors.HexColor("#94A3B8"))
                c.setFont("Helvetica", 7)
                c.drawCentredString(px + 28, py + 32, "PHOTO")

        # Subheader
        cursor_y = ribbon_y - 24
        if payload.get("rendered_subheader"):
            c.setFillColor(secondary)
            c.setFont(f_bold, 9.5)
            c.drawCentredString(w / 2.0, cursor_y, str(payload["rendered_subheader"]).upper()[:75])
            cursor_y -= 24

        # Recipient Nameplate
        c.setFillColor(secondary)
        c.setFont(f_bold, 20)
        c.drawCentredString(w / 2.0, cursor_y, str(rec.get("recipient_name", "")))
        c.setStrokeColor(accent)
        c.setLineWidth(1.2)
        c.line(w / 2.0 - 150, cursor_y - 6, w / 2.0 + 150, cursor_y - 6)
        cursor_y -= 30

        # Wrapped Body Paragraphs
        max_text_w = w - 2 * margin - 72
        c.setFillColor(text_col)
        c.setFont(f_reg, 11.5)
        for para in str(payload.get("rendered_body", "")).split("\n"):
            p_clean = para.strip()
            if not p_clean:
                cursor_y -= 10
                continue
            wrapped = simpleSplit(p_clean, f_reg, 11.5, max_text_w)
            for ln in wrapped:
                c.drawCentredString(w / 2.0, cursor_y, ln)
                cursor_y -= 17

        # Custom Fields Grid
        cf_items = payload.get("custom_fields_display", [])
        if getattr(tpl, "show_custom_fields", True) and cf_items:
            cursor_y -= 8
            box_w = w - 2 * margin - 80
            box_x = margin + 40
            row_h = 16.0
            cols = 2 if w > 520 else 1
            rows_needed = (len(cf_items) + cols - 1) // cols
            box_h = rows_needed * row_h + 12
            if cursor_y - box_h > margin + 95:
                c.setFillColor(colors.HexColor("#F8FAFC"))
                c.setStrokeColor(colors.HexColor("#CBD5E1"))
                c.setLineWidth(0.7)
                c.roundRect(box_x, cursor_y - box_h, box_w, box_h, 4, fill=1, stroke=1)
                c.setFont("Helvetica", 8.5)
                col_w = box_w / float(cols)
                for idx, cf in enumerate(cf_items):
                    r_i = idx // cols
                    c_i = idx % cols
                    tx = box_x + 10 + c_i * col_w
                    ty = cursor_y - 14 - r_i * row_h
                    c.setFillColor(primary)
                    c.setFont("Helvetica-Bold", 8.0)
                    lbl_txt = f"{cf['label']}: "
                    c.drawString(tx, ty, lbl_txt)
                    lbl_w = c.stringWidth(lbl_txt, "Helvetica-Bold", 8.0)
                    c.setFillColor(text_col)
                    c.setFont("Helvetica", 8.0)
                    c.drawString(tx + lbl_w, ty, str(cf["value"])[:42])
                cursor_y -= box_h + 10

        # QR Code Bottom Center/Left & Footer Note
        footer_y = margin + 12
        if getattr(tpl, "show_qr", True):
            _draw_qr_matrix(c, payload.get("qr_payload", ""), w / 2.0 - 24, margin + 8, 48, accent)

        if payload.get("rendered_footer"):
            c.setFillColor(colors.HexColor("#64748B"))
            c.setFont(f_ital, 7.8)
            c.drawCentredString(w / 2.0, footer_y - 2, str(payload["rendered_footer"])[:110])

        _draw_signatures_and_seal(
            c, tpl, school,
            left_x=margin + 24,
            right_x=w - margin - 24,
            base_y=margin + 28,
            center_x=w / 2.0 - (68 if getattr(tpl, "show_qr", True) else 0),
            primary=primary,
            accent=accent,
            text_col=text_col,
            font_reg=f_reg,
            font_bold=f_bold,
        )
        c.restoreState()

    # ------------------------------------------------------------------ #
    # 3. FINANCIAL RECEIPTS (Fee Receipt, Admission Receipt)
    # ------------------------------------------------------------------ #
    @classmethod
    def _draw_receipt(cls, c: canvas.Canvas, payload: Dict[str, Any], w: float, h: float) -> None:
        tpl = payload["template"]
        school = payload.get("school_info", {})
        rec = payload.get("recipient_info", {})
        metrics = payload.get("summary_metrics", {})
        rows = payload.get("table_rows", [])
        primary = _hex(tpl.primary_color, "#1E3A8A")
        secondary = _hex(tpl.secondary_color, "#0F172A")
        accent = _hex(tpl.accent_color, "#059669")
        text_col = _hex(tpl.text_color, "#0F172A")
        bg_col = _hex(tpl.background_color, "#FFFFFF")
        f_reg, f_bold, f_ital = _font_pair(tpl.font_family)
        cur = metrics.get("currency_code") or "BDT"

        c.saveState()
        c.setFillColor(bg_col)
        c.rect(0, 0, w, h, fill=1, stroke=0)
        margin = _draw_border(c, w, h, tpl.border_style if getattr(tpl, "show_border", True) else "None", primary, accent, compact=True)

        # Header Band
        band_h = 46.0
        c.setFillColor(primary)
        c.rect(margin, h - margin - band_h, w - 2 * margin, band_h, fill=1, stroke=0)
        if getattr(tpl, "show_logo", True):
            _draw_logo_or_crest(c, school.get("logo_path"), school.get("school_name", "School"), margin + 8, h - margin - band_h + 6, 34, secondary, accent)

        c.setFillColor(colors.white)
        c.setFont(f_bold, 13)
        c.drawCentredString(w / 2.0, h - margin - 16, str(school.get("school_name", "Institution")).upper()[:50])
        c.setFont(f_reg, 7.5)
        c.drawCentredString(w / 2.0, h - margin - 27, f"EIIN: {school.get('eiin_number', '-')}  |  {school.get('address', '')}  |  {school.get('phone', '')}"[:95])
        c.setFillColor(colors.HexColor("#FEF08A"))
        c.setFont(f_bold, 8.8)
        c.drawCentredString(w / 2.0, h - margin - 39, str(payload.get("rendered_header") or payload.get("document_type", "")).upper())

        # Metadata Row
        y = h - margin - band_h - 14
        c.setFillColor(text_col)
        c.setFont(f_bold, 8.2)
        c.drawString(margin + 6, y, f"SERIAL: {payload.get('serial_number', '')}  |  RECEIPT: {metrics.get('receipt_no', '-')}")
        c.drawRightString(w - margin - 6, y, f"Date: {metrics.get('payment_date') or payload.get('issue_date')}  |  Verify: {payload.get('verification_code', '')}")

        y -= 14
        c.setFont(f_bold, 8.2)
        c.drawString(margin + 6, y, "Recipient:")
        c.setFont(f_reg, 8.2)
        c.drawString(margin + 62, y, f"{rec.get('recipient_name', '')} ({rec.get('recipient_code', '')})")
        c.setFont(f_bold, 8.2)
        c.drawString(w / 2.0 + 10, y, "Class / Target:")
        c.setFont(f_reg, 8.2)
        c.drawString(w / 2.0 + 78, y, str(rec.get("class_or_designation", ""))[:32])

        y -= 13
        c.setFont(f_reg, 7.8)
        c.drawString(margin + 6, y, str(payload.get("rendered_body", ""))[:100])

        # Itemized Payment Table
        y -= 16
        tbl_w = w - 2 * margin - 12
        tx = margin + 6
        c.setFillColor(colors.HexColor("#F1F5F9"))
        c.rect(tx, y - 14, tbl_w, 16, fill=1, stroke=0)
        c.setFillColor(secondary)
        c.setFont(f_bold, 7.6)
        c.drawString(tx + 6, y - 9, "FEE DESCRIPTION")
        c.drawRightString(tx + tbl_w * 0.56, y - 9, "GROSS")
        c.drawRightString(tx + tbl_w * 0.70, y - 9, "CONCESSION")
        c.drawRightString(tx + tbl_w * 0.84, y - 9, "NET")
        c.drawRightString(tx + tbl_w - 6, y - 9, f"PAID ({cur})")

        y -= 28
        for item in (rows or [{"description": "Institutional Payment", "original": metrics.get("amount_paid", 0), "discount": 0, "net_amount": metrics.get("amount_paid", 0), "paid_now": metrics.get("amount_paid", 0)}])[:4]:
            c.setFillColor(text_col)
            c.setFont(f_reg, 7.8)
            c.drawString(tx + 6, y, str(item.get("description", ""))[:36])
            c.drawRightString(tx + tbl_w * 0.56, y, f"{float(item.get('original', 0)):,.2f}")
            c.drawRightString(tx + tbl_w * 0.70, y, f"{float(item.get('discount', 0)):,.2f}")
            c.drawRightString(tx + tbl_w * 0.84, y, f"{float(item.get('net_amount', 0)):,.2f}")
            c.setFillColor(accent)
            c.setFont(f_bold, 8.2)
            c.drawRightString(tx + tbl_w - 6, y, f"{cur} {float(item.get('paid_now', 0)):,.2f}")
            y -= 14

        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.line(tx, y + 6, tx + tbl_w, y + 6)

        y -= 6
        c.setFillColor(text_col)
        c.setFont(f_reg, 7.8)
        c.drawString(tx + 6, y, f"Method: {metrics.get('payment_method', 'Cash')} | Ref: {metrics.get('transaction_id', '-')} | Status: {metrics.get('status', 'Paid')}")
        c.setFont(f_bold, 8.0)
        c.drawRightString(tx + tbl_w - 6, y, f"Balance Due: {cur} {float(metrics.get('remaining_due', 0)):,.2f}")

        # Custom fields inline
        cf_items = payload.get("custom_fields_display", [])
        if getattr(tpl, "show_custom_fields", True) and cf_items:
            y -= 13
            cf_str = "  |  ".join(f"{cf['label']}: {cf['value']}" for cf in cf_items[:3])
            c.setFillColor(colors.HexColor("#475569"))
            c.setFont(f_reg, 7.4)
            c.drawString(tx + 6, y, cf_str[:105])

        if getattr(tpl, "show_qr", True):
            _draw_qr_matrix(c, payload.get("qr_payload", ""), w / 2.0 - 20, margin + 8, 40, accent)

        _draw_signatures_and_seal(
            c, tpl, school,
            left_x=margin + 12,
            right_x=w - margin - 12,
            base_y=margin + 12,
            center_x=w / 2.0 - (52 if getattr(tpl, "show_qr", True) else 0),
            primary=primary,
            accent=accent,
            text_col=text_col,
            font_reg=f_reg,
            font_bold=f_bold,
        )
        c.restoreState()

    # ------------------------------------------------------------------ #
    # 4. ACADEMIC TRANSCRIPTS (Mark Sheet & Report Card)
    # ------------------------------------------------------------------ #
    @classmethod
    def _draw_academic_transcript(cls, c: canvas.Canvas, payload: Dict[str, Any], w: float, h: float) -> None:
        tpl = payload["template"]
        school = payload.get("school_info", {})
        rec = payload.get("recipient_info", {})
        metrics = payload.get("summary_metrics", {})
        rows = payload.get("table_rows", [])
        primary = _hex(tpl.primary_color, "#1E3A8A")
        secondary = _hex(tpl.secondary_color, "#0F172A")
        accent = _hex(tpl.accent_color, "#059669")
        text_col = _hex(tpl.text_color, "#0F172A")
        bg_col = _hex(tpl.background_color, "#FFFFFF")
        f_reg, f_bold, f_ital = _font_pair(tpl.font_family)

        c.saveState()
        c.setFillColor(bg_col)
        c.rect(0, 0, w, h, fill=1, stroke=0)
        _draw_watermark(c, w, h, getattr(tpl, "watermark_text", None) or "")
        margin = _draw_border(c, w, h, tpl.border_style if getattr(tpl, "show_border", True) else "None", primary, accent)

        y = h - margin - 8
        c.setFillColor(colors.HexColor("#475569"))
        c.setFont("Helvetica-Bold", 7.8)
        if getattr(tpl, "show_serial", True):
            c.drawString(margin + 4, y, f"SERIAL: {payload.get('serial_number', '')}")
            c.drawRightString(w - margin - 4, y, f"VERIFY: {payload.get('verification_code', '')}")

        y -= 20
        if getattr(tpl, "show_logo", True):
            _draw_logo_or_crest(c, school.get("logo_path"), school.get("school_name", "School"), margin + 8, y - 22, 42, primary, accent)

        c.setFillColor(primary)
        c.setFont(f_bold, 15.5)
        c.drawCentredString(w / 2.0, y, str(school.get("school_name", "Institution")).upper()[:52])
        c.setFillColor(colors.HexColor("#475569"))
        c.setFont(f_reg, 8.2)
        c.drawCentredString(w / 2.0, y - 13, f"{school.get('address', '')}  •  EIIN: {school.get('eiin_number', '-')}  •  {school.get('phone', '')}"[:98])

        y -= 34
        c.setFillColor(primary)
        c.roundRect(margin + 40, y - 4, w - 2 * margin - 80, 22, 4, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont(f_bold, 11)
        c.drawCentredString(w / 2.0, y + 3, str(payload.get("rendered_header") or payload.get("document_type", "")).upper())

        y -= 16
        c.setFillColor(secondary)
        c.setFont(f_bold, 8.5)
        c.drawCentredString(
            w / 2.0,
            y,
            f"{metrics.get('exam_term_name', 'Term Exam')}  •  Status: {metrics.get('result_status', 'Compiled')}  •  Issued: {payload.get('issue_date')}",
        )

        # Student Profile Box
        y -= 12
        box_w = w - 2 * margin - 12
        bx = margin + 6
        c.setFillColor(colors.HexColor("#F8FAFC"))
        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.rect(bx, y - 46, box_w, 46, fill=1, stroke=1)
        c.setFillColor(text_col)
        c.setFont(f_bold, 8.2)
        c.drawString(bx + 8, y - 14, f"Student: {rec.get('recipient_name', '')}")
        c.drawString(bx + box_w * 0.52, y - 14, f"Class & Sec: {rec.get('class_or_designation', '')}")
        c.setFont(f_reg, 8.0)
        c.drawString(bx + 8, y - 27, f"Student ID: {rec.get('recipient_code', '')}  |  Adm No: {rec.get('admission_number', '')}")
        c.drawString(bx + box_w * 0.52, y - 27, f"Father: {rec.get('father_name', 'N/A')}")
        c.drawString(bx + 8, y - 40, f"Mother: {rec.get('mother_name', 'N/A')}")
        c.drawString(bx + box_w * 0.52, y - 40, f"Session: {payload.get('academic_year_name', '')}")

        if getattr(tpl, "show_photo", False):
            _draw_image_safe(c, rec.get("photo_path"), bx + box_w - 42, y - 44, 36, 42)

        # KPI Strip
        y -= 56
        c.setFillColor(colors.HexColor("#F1F5F9"))
        c.setStrokeColor(primary)
        c.rect(bx, y - 30, box_w, 30, fill=1, stroke=1)
        kpis = [
            ("TERM GPA", f"{float(metrics.get('gpa', 0)):.2f} / {float(metrics.get('max_gpa', 5.0)):.1f}"),
            ("CGPA", f"{float(metrics.get('cgpa', 0)):.2f}"),
            ("GRADE", str(metrics.get("overall_grade", "N/A"))),
            ("CLASS / SEC RANK", f"#{metrics.get('class_rank') or '-'} / #{metrics.get('section_rank') or '-'}"),
            ("TOTAL / RESULT", f"{float(metrics.get('total_obtained', 0)):.0f}/{float(metrics.get('total_full_marks', 0)):.0f} ({'PASSED' if metrics.get('passed_all') else 'FAILED'})"),
        ]
        kw = box_w / len(kpis)
        for i, (klbl, kval) in enumerate(kpis):
            kx = bx + i * kw + kw / 2.0
            c.setFillColor(colors.HexColor("#475569"))
            c.setFont(f_bold, 6.8)
            c.drawCentredString(kx, y - 10, klbl)
            c.setFillColor(accent if "PASSED" in kval else primary)
            c.setFont(f_bold, 9.2)
            c.drawCentredString(kx, y - 23, kval)

        # Marks Breakdown Table
        y -= 44
        cols_spec = [
            ("Code", 0.08), ("Subject", 0.25), ("Full", 0.06), ("Th", 0.06),
            ("MCQ", 0.06), ("Prac", 0.06), ("Viva", 0.06), ("Att", 0.06),
            ("Total", 0.08), ("GP", 0.07), ("Grd", 0.08), ("Res", 0.08),
        ]
        c.setFillColor(secondary)
        c.rect(bx, y - 14, box_w, 16, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont(f_bold, 7.3)
        cx = bx
        for hdr, frac in cols_spec:
            col_w = box_w * frac
            c.drawCentredString(cx + col_w / 2.0, y - 9, hdr)
            cx += col_w

        y -= 28
        for idx_r, rdata in enumerate(rows[:16]):
            if idx_r % 2 == 1:
                c.setFillColor(colors.HexColor("#F8FAFC"))
                c.rect(bx, y - 3, box_w, 14, fill=1, stroke=0)
            c.setStrokeColor(colors.HexColor("#E2E8F0"))
            c.line(bx, y - 3, bx + box_w, y - 3)
            vals = [
                str(rdata.get("code", "")),
                str(rdata.get("subject", ""))[:24],
                f"{float(rdata.get('full_marks', 100)):.0f}",
                f"{float(rdata.get('theory', 0)):.0f}",
                f"{float(rdata.get('mcq', 0)):.0f}",
                f"{float(rdata.get('practical', 0)):.0f}",
                f"{float(rdata.get('viva', 0)):.0f}",
                f"{float(rdata.get('attendance', 0)):.0f}",
                f"{float(rdata.get('total', 0)):.1f}",
                f"{float(rdata.get('grade_point', 0)):.2f}",
                str(rdata.get("grade_name", "")),
                "PASS" if rdata.get("passed", True) else "FAIL",
            ]
            cx = bx
            for col_idx, ((_, frac), v) in enumerate(zip(cols_spec, vals)):
                col_w = box_w * frac
                c.setFillColor(colors.HexColor("#B91C1C") if (col_idx >= 8 and not rdata.get("passed", True)) else text_col)
                c.setFont(f_bold if col_idx in (8, 10) else f_reg, 7.3)
                if col_idx == 1:
                    c.drawString(cx + 4, y + 1, v)
                else:
                    c.drawCentredString(cx + col_w / 2.0, y + 1, v)
                cx += col_w
            y -= 14

        if not rows:
            c.setFillColor(colors.HexColor("#64748B"))
            c.setFont(f_ital, 8.5)
            c.drawCentredString(w / 2.0, y, "No compiled subject marks attached to this transcript.")
            y -= 18

        # Body & Custom Fields Summary
        y -= 10
        if y > margin + 90:
            c.setFillColor(text_col)
            c.setFont(f_reg, 8.2)
            for ln in simpleSplit(str(payload.get("rendered_body", "")), f_reg, 8.2, box_w)[:3]:
                c.drawString(bx + 4, y, ln)
                y -= 11

        cf_items = payload.get("custom_fields_display", [])
        if getattr(tpl, "show_custom_fields", True) and cf_items and y > margin + 70:
            for cf in cf_items[:3]:
                c.setFont(f_bold, 7.8)
                c.setFillColor(primary)
                c.drawString(bx + 4, y, f"{cf['label']}: ")
                lw = c.stringWidth(f"{cf['label']}: ", f_bold, 7.8)
                c.setFillColor(text_col)
                c.setFont(f_reg, 7.8)
                c.drawString(bx + 4 + lw, y, str(cf["value"])[:80])
                y -= 11

        if getattr(tpl, "show_qr", True):
            _draw_qr_matrix(c, payload.get("qr_payload", ""), w / 2.0 - 22, margin + 10, 44, accent)

        _draw_signatures_and_seal(
            c, tpl, school,
            left_x=margin + 18,
            right_x=w - margin - 18,
            base_y=margin + 22,
            center_x=w / 2.0 - (62 if getattr(tpl, "show_qr", True) else 0),
            primary=primary,
            accent=accent,
            text_col=text_col,
            font_reg=f_reg,
            font_bold=f_bold,
        )
        c.restoreState()
