"""
EduManage Pro - QSS Theme Stylesheets
Provides modern dark, light, and slate palettes matching Windows 11 Fluent and Enterprise software standards.
"""

DARK_THEME_QSS = """
QMainWindow, QDialog, QWidget#centralWidget {
    background-color: #0f172a;
    color: #f8fafc;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

/* Sidebar */
QWidget#sidebarContainer {
    background-color: #1e293b;
    border-right: 1px solid #334155;
}

QPushButton.sidebarButton {
    background-color: transparent;
    color: #94a3b8;
    text-align: left;
    padding: 10px 14px;
    border-radius: 8px;
    border: none;
    font-size: 13px;
    font-weight: 500;
}

QPushButton.sidebarButton:hover {
    background-color: #334155;
    color: #ffffff;
}

QPushButton.sidebarButton:checked, QPushButton.sidebarButtonActive {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
}

/* Topbar */
QWidget#topbarContainer {
    background-color: #1e293b;
    border-bottom: 1px solid #334155;
    min-height: 56px;
    max-height: 56px;
}

QLineEdit.searchBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
    color: #f8fafc;
}

QLineEdit.searchBox:focus {
    border: 1px solid #3b82f6;
}

/* KPI Cards */
QFrame.kpiCard {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 16px;
}

QLabel.kpiTitle {
    color: #94a3b8;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
}

QLabel.kpiValue {
    color: #f8fafc;
    font-size: 26px;
    font-weight: 700;
}

/* Primary Action Buttons */
QPushButton.btnPrimary {
    background-color: #2563eb;
    color: #ffffff;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    border: none;
}

QPushButton.btnPrimary:hover {
    background-color: #1d4ed8;
}

QPushButton.btnPrimary:pressed {
    background-color: #1e40af;
}

/* Form Controls */
QLineEdit, QComboBox, QSpinBox, QDateEdit, QTextEdit {
    background-color: #1e293b;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 8px 10px;
    color: #f8fafc;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #3b82f6;
}

/* Tables */
QTableWidget {
    background-color: #1e293b;
    border: 1px solid #334155;
    gridline-color: #334155;
    color: #f8fafc;
    border-radius: 8px;
}

QHeaderView::section {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 8px;
    border: none;
    font-weight: 600;
    font-size: 12px;
}

QTableWidget::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}
"""

LIGHT_THEME_QSS = """
QMainWindow, QDialog, QWidget#centralWidget {
    background-color: #f1f5f9;
    color: #0f172a;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

QWidget#sidebarContainer {
    background-color: #ffffff;
    border-right: 1px solid #e2e8f0;
}

QPushButton.sidebarButton {
    background-color: transparent;
    color: #64748b;
    text-align: left;
    padding: 10px 14px;
    border-radius: 8px;
    border: none;
    font-size: 13px;
    font-weight: 500;
}

QPushButton.sidebarButton:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}

QPushButton.sidebarButton:checked, QPushButton.sidebarButtonActive {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
}

QWidget#topbarContainer {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    min-height: 56px;
    max-height: 56px;
}

QLineEdit.searchBox {
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 12px;
    color: #0f172a;
}

QFrame.kpiCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px;
}

QLabel.kpiTitle {
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
}

QLabel.kpiValue {
    color: #0f172a;
    font-size: 26px;
    font-weight: 700;
}

QPushButton.btnPrimary {
    background-color: #2563eb;
    color: #ffffff;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    border: none;
}

QPushButton.btnPrimary:hover {
    background-color: #1d4ed8;
}

QLineEdit, QComboBox, QSpinBox, QDateEdit, QTextEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 10px;
    color: #0f172a;
}

QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    gridline-color: #e2e8f0;
    color: #0f172a;
    border-radius: 8px;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    padding: 8px;
    border: none;
    font-weight: 600;
}
"""
