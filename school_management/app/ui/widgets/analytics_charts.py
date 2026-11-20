"""
EduManage Pro - Real-Database Analytics Chart Widgets (PySide6 QPainter)
Pure database-driven charts (vertical bar, grouped comparison, horizontal breakdown).
Never renders fabricated/placeholder data: empty queries render an explicit empty state.
"""

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget


def _fmt_num(val: float, prefix: str = "", suffix: str = "") -> str:
    if abs(val - round(val)) < 1e-6:
        core = f"{int(round(val)):,}"
    elif abs(val) >= 1000:
        core = f"{val:,.0f}"
    else:
        core = f"{val:,.1f}"
    return f"{prefix}{core}{suffix}"


class RealBarChartWidget(QFrame):
    """Vertical bar chart painted exclusively from live database query series."""

    def __init__(
        self,
        title: str,
        accent_color: str = "#3b82f6",
        value_prefix: str = "",
        value_suffix: str = "",
        empty_message: str = "No database records found for selected filter.",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.title = title
        self.accent_color = accent_color
        self.value_prefix = value_prefix
        self.value_suffix = value_suffix
        self.empty_message = empty_message
        self._series: List[Dict[str, float]] = []
        self.setMinimumHeight(230)
        self.setStyleSheet(
            "QFrame { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; }"
        )

    def set_data(self, series: List[Dict[str, float]]) -> None:
        self._series = list(series or [])
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Title
        title_font = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor("#f8fafc"))
        painter.drawText(QRectF(14, 10, w - 28, 22), Qt.AlignLeft | Qt.AlignVCenter, self.title)

        if not self._series:
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(
                QRectF(16, 40, w - 32, h - 56),
                Qt.AlignCenter | Qt.TextWordWrap,
                self.empty_message,
            )
            return

        left_pad = 54
        right_pad = 16
        top_pad = 44
        bottom_pad = 36
        plot_w = max(40, w - left_pad - right_pad)
        plot_h = max(40, h - top_pad - bottom_pad)

        max_val = max(float(item.get("value", 0.0) or 0.0) for item in self._series)
        if max_val <= 0:
            max_val = 1.0

        # Horizontal gridlines & Y labels (4 ticks)
        small_font = QFont("Segoe UI", 8)
        painter.setFont(small_font)
        for i in range(5):
            frac = i / 4.0
            y = top_pad + plot_h * (1.0 - frac)
            painter.setPen(QPen(QColor("#334155"), 1, Qt.DashLine))
            painter.drawLine(int(left_pad), int(y), int(left_pad + plot_w), int(y))

            tick_val = max_val * frac
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(
                QRectF(4, y - 9, left_pad - 10, 18),
                Qt.AlignRight | Qt.AlignVCenter,
                _fmt_num(tick_val, self.value_prefix, self.value_suffix),
            )

        # Bars
        n = len(self._series)
        slot_w = plot_w / max(1, n)
        bar_w = min(44.0, max(10.0, slot_w * 0.56))
        bar_color = QColor(self.accent_color)
        fm = QFontMetrics(small_font)

        for idx, item in enumerate(self._series):
            val = float(item.get("value", 0.0) or 0.0)
            label = str(item.get("label", ""))
            cx = left_pad + slot_w * (idx + 0.5)
            bar_h = (val / max_val) * plot_h if max_val > 0 else 0.0
            bx = cx - bar_w / 2.0
            by = top_pad + plot_h - bar_h

            painter.setPen(Qt.NoPen)
            painter.setBrush(bar_color)
            if bar_h > 0:
                painter.drawRoundedRect(QRectF(bx, by, bar_w, max(2.0, bar_h)), 3, 3)

            # Value label above bar
            painter.setPen(QColor("#e2e8f0"))
            val_txt = _fmt_num(val, self.value_prefix, self.value_suffix)
            painter.drawText(
                QRectF(cx - slot_w / 2.0, max(32.0, by - 18), slot_w, 16),
                Qt.AlignCenter,
                val_txt,
            )

            # Bottom X label (elided cleanly)
            elided = fm.elidedText(label, Qt.ElideRight, int(max(24, slot_w - 4)))
            painter.setPen(QColor("#cbd5e1"))
            painter.drawText(
                QRectF(cx - slot_w / 2.0, top_pad + plot_h + 6, slot_w, 22),
                Qt.AlignCenter,
                elided,
            )


class RealGroupedBarChartWidget(QFrame):
    """Side-by-side comparison bar chart (e.g., Income vs Expense, Billed vs Collected) from real DB rows."""

    def __init__(
        self,
        title: str,
        primary_label: str = "Income",
        secondary_label: str = "Expense",
        primary_color: str = "#10b981",
        secondary_color: str = "#ef4444",
        value_prefix: str = "",
        empty_message: str = "No financial transactions recorded for selected criteria.",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.title = title
        self.primary_label = primary_label
        self.secondary_label = secondary_label
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.value_prefix = value_prefix
        self.empty_message = empty_message
        self._series: List[Dict[str, float]] = []
        self.setMinimumHeight(230)
        self.setStyleSheet(
            "QFrame { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; }"
        )

    def set_data(self, series: List[Dict[str, float]]) -> None:
        self._series = list(series or [])
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.setPen(QColor("#f8fafc"))
        painter.drawText(QRectF(14, 10, w - 210, 22), Qt.AlignLeft | Qt.AlignVCenter, self.title)

        # Legend
        painter.setFont(QFont("Segoe UI", 8))
        leg_x = w - 190
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self.primary_color))
        painter.drawRoundedRect(QRectF(leg_x, 16, 10, 10), 2, 2)
        painter.setPen(QColor("#cbd5e1"))
        painter.drawText(QRectF(leg_x + 14, 11, 76, 20), Qt.AlignLeft | Qt.AlignVCenter, self.primary_label)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self.secondary_color))
        painter.drawRoundedRect(QRectF(leg_x + 92, 16, 10, 10), 2, 2)
        painter.setPen(QColor("#cbd5e1"))
        painter.drawText(QRectF(leg_x + 106, 11, 80, 20), Qt.AlignLeft | Qt.AlignVCenter, self.secondary_label)

        if not self._series:
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(
                QRectF(16, 40, w - 32, h - 56),
                Qt.AlignCenter | Qt.TextWordWrap,
                self.empty_message,
            )
            return

        left_pad = 62
        right_pad = 16
        top_pad = 44
        bottom_pad = 36
        plot_w = max(40, w - left_pad - right_pad)
        plot_h = max(40, h - top_pad - bottom_pad)

        max_val = max(
            max(float(it.get("primary", 0.0) or 0.0), float(it.get("secondary", 0.0) or 0.0))
            for it in self._series
        )
        if max_val <= 0:
            max_val = 1.0

        small_font = QFont("Segoe UI", 8)
        painter.setFont(small_font)
        for i in range(5):
            frac = i / 4.0
            y = top_pad + plot_h * (1.0 - frac)
            painter.setPen(QPen(QColor("#334155"), 1, Qt.DashLine))
            painter.drawLine(int(left_pad), int(y), int(left_pad + plot_w), int(y))

            tick_val = max_val * frac
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(
                QRectF(4, y - 9, left_pad - 10, 18),
                Qt.AlignRight | Qt.AlignVCenter,
                _fmt_num(tick_val, self.value_prefix),
            )

        n = len(self._series)
        slot_w = plot_w / max(1, n)
        pair_w = min(46.0, max(16.0, slot_w * 0.65))
        single_w = max(6.0, (pair_w - 4.0) / 2.0)
        fm = QFontMetrics(small_font)

        c1 = QColor(self.primary_color)
        c2 = QColor(self.secondary_color)

        for idx, item in enumerate(self._series):
            p_val = float(item.get("primary", 0.0) or 0.0)
            s_val = float(item.get("secondary", 0.0) or 0.0)
            label = str(item.get("label", ""))
            cx = left_pad + slot_w * (idx + 0.5)

            ph = (p_val / max_val) * plot_h if max_val > 0 else 0.0
            sh = (s_val / max_val) * plot_h if max_val > 0 else 0.0

            x1 = cx - single_w - 2.0
            x2 = cx + 2.0
            y1 = top_pad + plot_h - ph
            y2 = top_pad + plot_h - sh

            painter.setPen(Qt.NoPen)
            if ph > 0:
                painter.setBrush(c1)
                painter.drawRoundedRect(QRectF(x1, y1, single_w, max(2.0, ph)), 2, 2)
            if sh > 0:
                painter.setBrush(c2)
                painter.drawRoundedRect(QRectF(x2, y2, single_w, max(2.0, sh)), 2, 2)

            elided = fm.elidedText(label, Qt.ElideRight, int(max(24, slot_w - 4)))
            painter.setPen(QColor("#cbd5e1"))
            painter.drawText(
                QRectF(cx - slot_w / 2.0, top_pad + plot_h + 6, slot_w, 22),
                Qt.AlignCenter,
                elided,
            )


class RealHorizontalBreakdownWidget(QFrame):
    """Horizontal proportion bar chart driven strictly by live DB distribution data."""

    DEFAULT_PALETTE: Tuple[str, ...] = (
        "#10b981",
        "#ef4444",
        "#f59e0b",
        "#3b82f6",
        "#8b5cf6",
        "#06b6d4",
        "#ec4899",
    )

    def __init__(
        self,
        title: str,
        empty_message: str = "No distribution records present in database.",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.title = title
        self.empty_message = empty_message
        self._series: List[Dict[str, float]] = []
        self.setMinimumHeight(230)
        self.setStyleSheet(
            "QFrame { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; }"
        )

    def set_data(self, series: List[Dict[str, float]]) -> None:
        self._series = list(series or [])
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.setPen(QColor("#f8fafc"))
        painter.drawText(QRectF(14, 10, w - 28, 22), Qt.AlignLeft | Qt.AlignVCenter, self.title)

        total = sum(float(it.get("value", 0.0) or 0.0) for it in self._series)
        if not self._series or total <= 0:
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(
                QRectF(16, 40, w - 32, h - 56),
                Qt.AlignCenter | Qt.TextWordWrap,
                self.empty_message,
            )
            return

        y = 44
        row_h = min(30, max(20, (h - 56) // max(1, len(self._series))))
        label_w = 100
        right_val_w = 82
        bar_area_w = max(50, w - label_w - right_val_w - 32)
        small_font = QFont("Segoe UI", 8)
        painter.setFont(small_font)

        for idx, it in enumerate(self._series[:7]):
            lbl = str(it.get("label", ""))
            val = float(it.get("value", 0.0) or 0.0)
            pct = (val / total) * 100.0 if total > 0 else 0.0
            col_hex = self.DEFAULT_PALETTE[idx % len(self.DEFAULT_PALETTE)]

            painter.setPen(QColor("#e2e8f0"))
            painter.drawText(QRectF(14, y, label_w - 6, row_h), Qt.AlignLeft | Qt.AlignVCenter, lbl)

            # Track
            bar_x = 14 + label_w
            bar_y = y + (row_h - 12) / 2.0
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#0f172a"))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_area_w, 12), 4, 4)

            fill_w = max(4.0, (val / total) * bar_area_w)
            painter.setBrush(QColor(col_hex))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, 12), 4, 4)

            painter.setPen(QColor("#cbd5e1"))
            painter.drawText(
                QRectF(bar_x + bar_area_w + 8, y, right_val_w, row_h),
                Qt.AlignRight | Qt.AlignVCenter,
                f"{int(round(val)):,} ({pct:.1f}%)",
            )
            y += row_h
