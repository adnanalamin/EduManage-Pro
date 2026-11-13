"""
EduManage Pro - Reusable Qt Vector QR Code Widget (PySide6)
Draws any QR matrix directly with QPainter so Digital IDs render crisply offline.
"""

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from app.utils.qr_generator import generate_qr_matrix


class QRCodeWidget(QWidget):
    def __init__(self, payload: str = "", size: int = 84, parent=None):
        super().__init__(parent)
        self._payload = payload or "EDUMANAGE"
        self._matrix: List[List[bool]] = generate_qr_matrix(self._payload)
        self.setFixedSize(size, size)
        self.setToolTip(self._payload)

    def set_payload(self, payload: str) -> None:
        self._payload = payload or "EDUMANAGE"
        self._matrix = generate_qr_matrix(self._payload)
        self.setToolTip(self._payload)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        painter.setPen(QColor("#cbd5e1"))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        if not self._matrix:
            return
        dim = len(self._matrix)
        margin = 4
        usable = max(1, min(self.width(), self.height()) - margin * 2)
        cell = usable / float(dim)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#0f172a"))
        for r_idx, row in enumerate(self._matrix):
            for c_idx, val in enumerate(row):
                if val:
                    x = int(margin + c_idx * cell)
                    y = int(margin + r_idx * cell)
                    w = max(1, int(margin + (c_idx + 1) * cell) - x)
                    h = max(1, int(margin + (r_idx + 1) * cell) - y)
                    painter.drawRect(x, y, w, h)
