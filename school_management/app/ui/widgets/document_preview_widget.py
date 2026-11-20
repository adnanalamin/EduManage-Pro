"""
EduManage Pro - Interactive Print Preview Widget & Qt Vector Document Painter
Renders live interactive visual Print Previews and OS QPrintPreviewDialog / QPrinter
output for all 10 template-driven official document types.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QRectF, QSize, QSizeF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPageLayout, QPageSize, QPen, QPixmap
from PySide6.QtPrintSupport import QPrintDialog, QPrintPreviewDialog, QPrinter
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.utils.qr_generator import generate_qr_matrix


def _qcolor(val: Any, fallback: str = "#1E3A8A") -> QColor:
    c = QColor(str(val or fallback))
    return c if c.isValid() else QColor(fallback)


def _qt_font_family(font_family: str) -> str:
    f = (font_family or "Helvetica").strip()
    if f == "Times-Roman":
        return "Times New Roman"
    if f == "Courier":
        return "Courier New"
    return "Segoe UI"


def _logical_page_size(page_size: str, orientation: str) -> QSizeF:
    ps = (page_size or "A4").strip().upper()
    orient = (orientation or "Portrait").strip().lower()
    if ps == "CR80":
        w, h = 243.0, 386.0  # crisp scaled card proportions
    elif ps == "A5":
        w, h = 420.0, 595.0
    elif ps == "LETTER":
        w, h = 612.0, 792.0
    else:
        w, h = 595.0, 842.0
    if orient == "landscape" and w < h:
        return QSizeF(h, w)
    if orient == "portrait" and w > h:
        return QSizeF(h, w)
    return QSizeF(w, h)


def _draw_qr_qt(painter: QPainter, payload: str, rect: QRectF, border_col: QColor) -> None:
    matrix = generate_qr_matrix(payload or "EDUMANAGE")
    dim = len(matrix)
    if dim <= 0:
        return
    painter.save()
    painter.setBrush(QColor("#FFFFFF"))
    painter.setPen(QPen(border_col, 1.0))
    painter.drawRect(rect)
    cw = rect.width() / float(dim)
    ch = rect.height() / float(dim)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#0F172A"))
    for r_idx, row in enumerate(matrix):
        for c_idx, cell in enumerate(row):
            if cell:
                painter.drawRect(QRectF(rect.left() + c_idx * cw, rect.top() + r_idx * ch, cw + 0.2, ch + 0.2))
    painter.restore()


def _draw_image_qt(painter: QPainter, path_str: Any, rect: QRectF) -> bool:
    if not path_str:
        return False
    p = Path(str(path_str))
    if not p.exists() or not p.is_file():
        return False
    img = QImage(str(p))
    if img.isNull():
        return False
    painter.save()
    scaled = img.scaled(int(max(1, rect.width())), int(max(1, rect.height())), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    dx = rect.left() + (rect.width() - scaled.width()) / 2.0
    dy = rect.top() + (rect.height() - scaled.height()) / 2.0
    painter.drawImage(QRectF(dx, dy, scaled.width(), scaled.height()), scaled)
    painter.restore()
    return True


def _draw_logo_qt(painter: QPainter, logo_path: Any, school_name: str, rect: QRectF, primary: QColor, accent: QColor) -> None:
    if _draw_image_qt(painter, logo_path, rect):
        return
    words = [w for w in (school_name or "ED").split() if w and w[0].isalnum()]
    initials = "".join(w[0].upper() for w in words[:2]) or "ED"
    painter.save()
    painter.setBrush(primary)
    painter.setPen(QPen(accent, 1.8))
    painter.drawEllipse(rect)
    painter.setPen(QColor("#FFFFFF"))
    painter.setFont(QFont("Segoe UI", max(7, int(rect.width() * 0.32)), QFont.Bold))
    painter.drawText(rect, Qt.AlignCenter, initials)
    painter.restore()


def paint_document_on_canvas(painter: QPainter, payload: Dict[str, Any], target_rect: QRectF) -> None:
    """Paints a template-driven document inside target_rect using logical coordinates."""
    tpl = payload["template"]
    school = payload.get("school_info", {})
    rec = payload.get("recipient_info", {})
    metrics = payload.get("summary_metrics", {})
    rows = payload.get("table_rows", [])
    doc_type = payload.get("document_type", "Bonafide Certificate")

    logical_sz = _logical_page_size(tpl.page_size, tpl.orientation)
    lw, lh = logical_sz.width(), logical_sz.height()

    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    painter.translate(target_rect.left(), target_rect.top())
    painter.scale(target_rect.width() / lw, target_rect.height() / lh)

    primary = _qcolor(tpl.primary_color, "#1E3A8A")
    secondary = _qcolor(tpl.secondary_color, "#0F172A")
    accent = _qcolor(tpl.accent_color, "#D97706")
    text_col = _qcolor(tpl.text_color, "#0F172A")
    bg_col = _qcolor(tpl.background_color, "#FFFFFF")
    ff = _qt_font_family(tpl.font_family)

    # Background Fill
    painter.fillRect(QRectF(0, 0, lw, lh), bg_col)

    is_id_card = doc_type == "ID Card" or str(tpl.page_size).upper() == "CR80"
    if is_id_card:
        # Card Frame
        if getattr(tpl, "show_border", True):
            painter.setPen(QPen(primary, 2.0))
            painter.drawRoundedRect(QRectF(2, 2, lw - 4, lh - 4), 10, 10)
        # Header Bar
        painter.fillRect(QRectF(2, 2, lw - 4, 52), primary)
        if getattr(tpl, "show_logo", True):
            _draw_logo_qt(painter, school.get("logo_path"), school.get("school_name", "S"), QRectF(12, 10, 34, 34), secondary, accent)
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont(ff, 11, QFont.Bold))
        painter.drawText(QRectF(52, 8, lw - 64, 22), Qt.AlignCenter, str(school.get("school_name", "Institution"))[:36])
        painter.setFont(QFont(ff, 8))
        painter.drawText(QRectF(52, 29, lw - 64, 18), Qt.AlignCenter, str(payload.get("rendered_header") or "IDENTITY CARD")[:45])

        # Photo & Info
        info_x = 18.0
        if getattr(tpl, "show_photo", True):
            p_rect = QRectF(16, 70, 74, 92)
            painter.fillRect(p_rect, QColor("#F1F5F9"))
            painter.setPen(QPen(accent, 1.2))
            painter.drawRect(p_rect)
            if not _draw_image_qt(painter, rec.get("photo_path"), p_rect):
                painter.setPen(QColor("#64748B"))
                painter.setFont(QFont(ff, 8, QFont.Bold))
                painter.drawText(p_rect, Qt.AlignCenter, "PHOTO")
            info_x = 104.0

        painter.setPen(text_col)
        painter.setFont(QFont(ff, 12, QFont.Bold))
        painter.drawText(QRectF(info_x, 70, lw - info_x - 74, 22), Qt.AlignLeft | Qt.AlignVCenter, str(rec.get("recipient_name", ""))[:26])
        painter.setFont(QFont(ff, 9))
        details = [
            f"ID: {rec.get('recipient_code', '-')}",
            f"{rec.get('class_or_designation', '-')}",
            f"Blood: {rec.get('blood_group', 'N/A')} | Tel: {rec.get('emergency_contact', '-')}",
        ]
        cf_items = payload.get("custom_fields_display", [])
        if getattr(tpl, "show_custom_fields", True) and cf_items:
            details.append(f"{cf_items[0]['label']}: {cf_items[0]['value']}")
        for idx, line in enumerate(details):
            painter.drawText(QRectF(info_x, 96 + idx * 18, lw - info_x - 76, 16), Qt.AlignLeft | Qt.AlignVCenter, line[:38])

        if getattr(tpl, "show_qr", True):
            _draw_qr_qt(painter, payload.get("qr_payload", ""), QRectF(lw - 70, lh - 88, 54, 54), accent)

        if getattr(tpl, "show_signatures", True):
            _draw_image_qt(painter, school.get("signature_right_image_path"), QRectF(lw - 140, lh - 56, 62, 24))

        # Bottom Strip
        painter.fillRect(QRectF(2, lh - 24, lw - 4, 22), secondary)
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont(ff, 7.5))
        if getattr(tpl, "show_serial", True):
            painter.drawText(QRectF(12, lh - 22, 180, 18), Qt.AlignLeft | Qt.AlignVCenter, f"SN: {payload.get('serial_number', '')}")
        painter.drawText(QRectF(lw - 180, lh - 22, 168, 18), Qt.AlignRight | Qt.AlignVCenter, str(getattr(tpl, "signature_right_label", "Principal") or "Principal")[:28])
        painter.restore()
        return

    # Standard Page Border & Watermark
    wm = str(getattr(tpl, "watermark_text", None) or school.get("school_name", ""))
    if wm and doc_type not in ("Fee Receipt", "Admission Receipt"):
        painter.save()
        painter.translate(lw / 2.0, lh / 2.0)
        painter.rotate(-28)
        painter.setPen(QColor(148, 163, 184, 38))
        painter.setFont(QFont(ff, 34, QFont.Bold))
        painter.drawText(QRectF(-260, -40, 520, 80), Qt.AlignCenter, wm.upper()[:28])
        painter.restore()

    m = 20.0
    if getattr(tpl, "show_border", True) and tpl.border_style != "None":
        if tpl.border_style == "Double":
            painter.setPen(QPen(primary, 3.0))
            painter.drawRect(QRectF(m, m, lw - 2 * m, lh - 2 * m))
            painter.setPen(QPen(accent, 1.3))
            painter.drawRect(QRectF(m + 7, m + 7, lw - 2 * (m + 7), lh - 2 * (m + 7)))
            m += 16.0
        elif tpl.border_style == "Modern":
            painter.setPen(QPen(primary, 1.8))
            painter.drawRoundedRect(QRectF(m, m, lw - 2 * m, lh - 2 * m), 10, 10)
            m += 12.0
        else:
            painter.setPen(QPen(primary, 2.0))
            painter.drawRect(QRectF(m, m, lw - 2 * m, lh - 2 * m))
            m += 12.0
    else:
        m = 24.0

    y = m + 6
    # Serial & Verify Bar
    if getattr(tpl, "show_serial", True):
        painter.setPen(QColor("#475569"))
        painter.setFont(QFont(ff, 8, QFont.Bold))
        painter.drawText(QRectF(m + 6, y, lw / 2.0 - m, 14), Qt.AlignLeft, f"SERIAL: {payload.get('serial_number', '')}")
        painter.drawText(QRectF(lw / 2.0, y, lw / 2.0 - m - 6, 14), Qt.AlignRight, f"VERIFY: {payload.get('verification_code', '')}")
        y += 18

    # School Header
    if getattr(tpl, "show_logo", True):
        _draw_logo_qt(painter, school.get("logo_path"), school.get("school_name", "S"), QRectF(m + 10, y, 44, 44), primary, accent)

    painter.setPen(primary)
    painter.setFont(QFont(ff, 15, QFont.Bold))
    painter.drawText(QRectF(m + 60, y, lw - 2 * m - 120, 22), Qt.AlignCenter, str(school.get("school_name", "Institution")).upper()[:54])
    painter.setPen(QColor("#475569"))
    painter.setFont(QFont(ff, 8.5))
    sub = " • ".join(p for p in [school.get("motto"), f"EIIN: {school.get('eiin_number')}" if school.get("eiin_number") else None, school.get("address")] if p)
    painter.drawText(QRectF(m + 60, y + 22, lw - 2 * m - 120, 16), Qt.AlignCenter, sub[:95])
    y += 52

    # Header Ribbon
    ribbon_w = min(400.0, lw - 2 * m - 40)
    rx = (lw - ribbon_w) / 2.0
    painter.setPen(Qt.NoPen)
    painter.setBrush(primary)
    painter.drawRoundedRect(QRectF(rx, y, ribbon_w, 26), 5, 5)
    painter.setPen(QColor("#FFFFFF"))
    painter.setFont(QFont(ff, 11.5, QFont.Bold))
    painter.drawText(QRectF(rx, y, ribbon_w, 26), Qt.AlignCenter, str(payload.get("rendered_header") or doc_type).upper())
    y += 34

    # Subheader / Recipient Banner
    if doc_type in ("Admission Receipt", "Fee Receipt"):
        cur = metrics.get("currency_code", "BDT")
        painter.setPen(text_col)
        painter.setFont(QFont(ff, 9, QFont.Bold))
        painter.drawText(QRectF(m + 8, y, lw - 2 * m - 16, 16), Qt.AlignLeft, f"Recipient: {rec.get('recipient_name', '')} ({rec.get('recipient_code', '')})   |   Class: {rec.get('class_or_designation', '')}")
        y += 20
        painter.setFont(QFont(ff, 8.5))
        painter.drawText(QRectF(m + 8, y, lw - 2 * m - 16, 26), Qt.AlignLeft | Qt.TextWordWrap, str(payload.get("rendered_body", "")))
        y += 30
        # Receipt Table
        painter.fillRect(QRectF(m + 8, y, lw - 2 * m - 16, 20), QColor("#F1F5F9"))
        painter.setPen(secondary)
        painter.setFont(QFont(ff, 8, QFont.Bold))
        painter.drawText(QRectF(m + 14, y, 200, 20), Qt.AlignLeft | Qt.AlignVCenter, "FEE DESCRIPTION")
        painter.drawText(QRectF(lw - m - 170, y, 155, 20), Qt.AlignRight | Qt.AlignVCenter, f"PAID ({cur})")
        y += 22
        for item in rows[:4]:
            painter.setPen(text_col)
            painter.setFont(QFont(ff, 8.5))
            painter.drawText(QRectF(m + 14, y, 220, 18), Qt.AlignLeft | Qt.AlignVCenter, str(item.get("description", ""))[:40])
            painter.setPen(accent)
            painter.setFont(QFont(ff, 9, QFont.Bold))
            painter.drawText(QRectF(lw - m - 170, y, 155, 18), Qt.AlignRight | Qt.AlignVCenter, f"{cur} {float(item.get('paid_now', 0)):,.2f}")
            y += 18
        y += 8
        painter.setPen(text_col)
        painter.setFont(QFont(ff, 8.5))
        painter.drawText(QRectF(m + 14, y, lw - 2 * m - 28, 16), Qt.AlignLeft, f"Method: {metrics.get('payment_method', '-')} | Remaining Due: {cur} {float(metrics.get('remaining_due', 0)):,.2f}")
        y += 20
    elif doc_type in ("Mark Sheet", "Report Card"):
        painter.fillRect(QRectF(m + 8, y, lw - 2 * m - 16, 36), QColor("#F8FAFC"))
        painter.setPen(QPen(QColor("#CBD5E1"), 1.0))
        painter.drawRect(QRectF(m + 8, y, lw - 2 * m - 16, 36))
        painter.setPen(text_col)
        painter.setFont(QFont(ff, 8.5, QFont.Bold))
        painter.drawText(QRectF(m + 14, y + 3, lw - 2 * m - 28, 15), Qt.AlignLeft, f"Student: {rec.get('recipient_name', '')} ({rec.get('recipient_code', '')})   •   {rec.get('class_or_designation', '')}")
        painter.setFont(QFont(ff, 8.5))
        painter.drawText(QRectF(m + 14, y + 19, lw - 2 * m - 28, 15), Qt.AlignLeft, f"Exam: {metrics.get('exam_term_name', '')}   •   GPA: {float(metrics.get('gpa', 0)):.2f}   •   CGPA: {float(metrics.get('cgpa', 0)):.2f}   •   Grade: {metrics.get('overall_grade', 'N/A')}")
        y += 44

        # Marks Table
        painter.fillRect(QRectF(m + 8, y, lw - 2 * m - 16, 20), secondary)
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont(ff, 7.8, QFont.Bold))
        painter.drawText(QRectF(m + 14, y, 200, 20), Qt.AlignLeft | Qt.AlignVCenter, "SUBJECT")
        painter.drawText(QRectF(lw - m - 210, y, 60, 20), Qt.AlignCenter, "FULL")
        painter.drawText(QRectF(lw - m - 150, y, 65, 20), Qt.AlignCenter, "OBTAINED")
        painter.drawText(QRectF(lw - m - 85, y, 70, 20), Qt.AlignCenter, "GRADE")
        y += 22
        for idx_r, rdata in enumerate(rows[:10]):
            if idx_r % 2 == 1:
                painter.fillRect(QRectF(m + 8, y, lw - 2 * m - 16, 17), QColor("#F8FAFC"))
            painter.setPen(text_col)
            painter.setFont(QFont(ff, 8))
            painter.drawText(QRectF(m + 14, y, 220, 17), Qt.AlignLeft | Qt.AlignVCenter, str(rdata.get("subject", ""))[:32])
            painter.drawText(QRectF(lw - m - 210, y, 60, 17), Qt.AlignCenter, f"{float(rdata.get('full_marks', 100)):.0f}")
            painter.drawText(QRectF(lw - m - 150, y, 65, 17), Qt.AlignCenter, f"{float(rdata.get('total', 0)):.1f}")
            painter.setFont(QFont(ff, 8, QFont.Bold))
            painter.drawText(QRectF(lw - m - 85, y, 70, 17), Qt.AlignCenter, f"{rdata.get('grade_name', '')} ({float(rdata.get('grade_point', 0)):.1f})")
            y += 17
        y += 10
    else:
        # Certificate Layout
        if payload.get("rendered_subheader"):
            painter.setPen(secondary)
            painter.setFont(QFont(ff, 9.5, QFont.Bold))
            painter.drawText(QRectF(m + 20, y, lw - 2 * m - 40, 18), Qt.AlignCenter, str(payload["rendered_subheader"]).upper())
            y += 22

        painter.setPen(secondary)
        painter.setFont(QFont(ff, 18, QFont.Bold))
        painter.drawText(QRectF(m + 30, y, lw - 2 * m - 60, 28), Qt.AlignCenter, str(rec.get("recipient_name", "")))
        painter.setPen(QPen(accent, 1.3))
        painter.drawLine(lw / 2.0 - 130, y + 30, lw / 2.0 + 130, y + 30)
        y += 40

        if getattr(tpl, "show_photo", False):
            ph_rect = QRectF(lw - m - 74, y - 40, 56, 68)
            painter.setPen(QPen(accent, 1.0))
            painter.drawRect(ph_rect)
            if not _draw_image_qt(painter, rec.get("photo_path"), ph_rect):
                painter.setPen(QColor("#94A3B8"))
                painter.setFont(QFont(ff, 7))
                painter.drawText(ph_rect, Qt.AlignCenter, "PHOTO")

        painter.setPen(text_col)
        painter.setFont(QFont(ff, 10.5))
        body_rect = QRectF(m + 32, y, lw - 2 * m - 64, max(70.0, lh - y - 165))
        painter.drawText(body_rect, Qt.AlignHCenter | Qt.TextWordWrap, str(payload.get("rendered_body", "")))
        y += 105

    # Custom Fields Display
    cf_items = payload.get("custom_fields_display", [])
    if getattr(tpl, "show_custom_fields", True) and cf_items and y < lh - 125:
        cf_text = "   |   ".join(f"{cf['label']}: {cf['value']}" for cf in cf_items[:4])
        painter.fillRect(QRectF(m + 24, y, lw - 2 * m - 48, 28), QColor("#F8FAFC"))
        painter.setPen(QPen(QColor("#CBD5E1"), 0.8))
        painter.drawRect(QRectF(m + 24, y, lw - 2 * m - 48, 28))
        painter.setPen(primary)
        painter.setFont(QFont(ff, 8, QFont.Bold))
        painter.drawText(QRectF(m + 30, y + 2, lw - 2 * m - 60, 24), Qt.AlignCenter | Qt.TextWordWrap, cf_text[:135])

    # Bottom QR, Seal & Signatures
    sig_base_y = lh - m - 56
    if getattr(tpl, "show_qr", True):
        _draw_qr_qt(painter, payload.get("qr_payload", ""), QRectF(lw / 2.0 - 25, lh - m - 64, 50, 50), accent)

    if getattr(tpl, "show_seal", True):
        sx = lw / 2.0 - (95 if getattr(tpl, "show_qr", True) else 22)
        if not _draw_image_qt(painter, school.get("seal_image_path"), QRectF(sx, lh - m - 62, 46, 46)):
            painter.setPen(QPen(accent, 1.4))
            painter.setBrush(QColor("#FEF3C7"))
            painter.drawEllipse(QRectF(sx, lh - m - 60, 42, 42))
            painter.setPen(accent)
            painter.setFont(QFont(ff, 6.5, QFont.Bold))
            painter.drawText(QRectF(sx, lh - m - 60, 42, 42), Qt.AlignCenter, "SEAL")

    if getattr(tpl, "show_signatures", True):
        _draw_image_qt(painter, school.get("signature_left_image_path"), QRectF(m + 28, sig_base_y, 110, 24))
        _draw_image_qt(painter, school.get("signature_right_image_path"), QRectF(lw - m - 138, sig_base_y, 110, 24))

        painter.setPen(QPen(text_col, 1.0))
        painter.drawLine(m + 20, sig_base_y + 26, m + 150, sig_base_y + 26)
        painter.drawLine(lw - m - 150, sig_base_y + 26, lw - m - 20, sig_base_y + 26)

        painter.setFont(QFont(ff, 8, QFont.Bold))
        painter.drawText(QRectF(m + 20, sig_base_y + 28, 130, 16), Qt.AlignCenter, str(getattr(tpl, "signature_left_label", "Registrar") or "Registrar")[:28])
        right_txt = getattr(tpl, "signature_right_name", None) or school.get("principal_name") or getattr(tpl, "signature_right_label", "Principal")
        painter.drawText(QRectF(lw - m - 150, sig_base_y + 28, 130, 16), Qt.AlignCenter, str(right_txt)[:28])

    if payload.get("rendered_footer"):
        painter.setPen(QColor("#64748B"))
        painter.setFont(QFont(ff, 7.2))
        painter.drawText(QRectF(m + 10, lh - m - 14, lw - 2 * m - 20, 12), Qt.AlignCenter, str(payload["rendered_footer"])[:110])

    painter.restore()


class _DocumentCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._payload: Optional[Dict[str, Any]] = None
        self._zoom: float = 0.85

    def set_payload(self, payload: Optional[Dict[str, Any]]) -> None:
        self._payload = payload
        self._update_size()
        self.update()

    def set_zoom(self, zoom: float) -> None:
        self._zoom = max(0.35, min(2.0, zoom))
        self._update_size()
        self.update()

    def _update_size(self) -> None:
        if not self._payload:
            self.setMinimumSize(460, 320)
            return
        tpl = self._payload["template"]
        lsz = _logical_page_size(tpl.page_size, tpl.orientation)
        self.setFixedSize(int(lsz.width() * self._zoom + 32), int(lsz.height() * self._zoom + 32))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#E2E8F0"))
        if not self._payload:
            painter.setPen(QColor("#64748B"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Select a document type & record to view live Print Preview.")
            return
        tpl = self._payload["template"]
        lsz = _logical_page_size(tpl.page_size, tpl.orientation)
        pw = lsz.width() * self._zoom
        ph = lsz.height() * self._zoom
        x = (self.width() - pw) / 2.0
        y = (self.height() - ph) / 2.0
        # Drop shadow
        painter.fillRect(QRectF(x + 4, y + 4, pw, ph), QColor(15, 23, 42, 45))
        paint_document_on_canvas(painter, self._payload, QRectF(x, y, pw, ph))


class DocumentPreviewWidget(QWidget):
    """Complete interactive Print Preview toolbar + canvas + OS Print/Preview dialogs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._payload: Optional[Dict[str, Any]] = None
        self._zoom = 0.85
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        bar = QHBoxLayout()
        self.lbl_meta = QLabel("Live Print Preview")
        self.lbl_meta.setStyleSheet("font-weight: 700; color: #1E293B; font-size: 12px;")
        bar.addWidget(self.lbl_meta)
        bar.addStretch()

        btn_zoom_out = QPushButton("➖ Zoom")
        btn_zoom_out.clicked.connect(lambda: self._change_zoom(-0.15))
        bar.addWidget(btn_zoom_out)

        btn_zoom_in = QPushButton("➕ Zoom")
        btn_zoom_in.clicked.connect(lambda: self._change_zoom(0.15))
        bar.addWidget(btn_zoom_in)

        btn_os_preview = QPushButton("🖨️ Print Preview Dialog")
        btn_os_preview.setStyleSheet("background-color: #0369A1; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold;")
        btn_os_preview.clicked.connect(self.open_print_preview_dialog)
        bar.addWidget(btn_os_preview)

        btn_print = QPushButton("🖨️ Print Now")
        btn_print.setStyleSheet("background-color: #0F172A; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold;")
        btn_print.clicked.connect(self.print_direct)
        bar.addWidget(btn_print)

        layout.addLayout(bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setStyleSheet("border: 1px solid #CBD5E1; border-radius: 6px; background: #E2E8F0;")
        self.canvas = _DocumentCanvas()
        self.scroll.setWidget(self.canvas)
        layout.addWidget(self.scroll)

    def set_payload(self, payload: Optional[Dict[str, Any]]) -> None:
        self._payload = payload
        if payload:
            tpl = payload["template"]
            self.lbl_meta.setText(f"Preview: {payload.get('document_type')} • {tpl.name} ({tpl.page_size} {tpl.orientation})")
        else:
            self.lbl_meta.setText("Live Print Preview")
        self.canvas.set_payload(payload)

    def _change_zoom(self, delta: float) -> None:
        self._zoom = max(0.35, min(2.0, self._zoom + delta))
        self.canvas.set_zoom(self._zoom)

    def _configure_printer(self, printer: QPrinter) -> None:
        if not self._payload:
            return
        tpl = self._payload["template"]
        ps_name = (tpl.page_size or "A4").upper()
        if ps_name == "A5":
            printer.setPageSize(QPageSize(QPageSize.A5))
        elif ps_name == "LETTER":
            printer.setPageSize(QPageSize(QPageSize.Letter))
        else:
            printer.setPageSize(QPageSize(QPageSize.A4))
        orient = QPageLayout.Landscape if str(tpl.orientation).lower() == "landscape" else QPageLayout.Portrait
        printer.setPageOrientation(orient)

    def _render_to_printer(self, printer: QPrinter) -> None:
        if not self._payload:
            return
        painter = QPainter(printer)
        if painter.isActive():
            rect = painter.viewport()
            paint_document_on_canvas(painter, self._payload, QRectF(0, 0, rect.width(), rect.height()))
            painter.end()

    def open_print_preview_dialog(self) -> None:
        if not self._payload:
            return
        printer = QPrinter(QPrinter.HighResolution)
        self._configure_printer(printer)
        dlg = QPrintPreviewDialog(printer, self)
        dlg.paintRequested.connect(self._render_to_printer)
        dlg.exec()

    def print_direct(self) -> None:
        if not self._payload:
            return
        printer = QPrinter(QPrinter.HighResolution)
        self._configure_printer(printer)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() == QPrintDialog.Accepted:
            self._render_to_printer(printer)
