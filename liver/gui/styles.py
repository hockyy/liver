"""Application stylesheet."""

DARK_THEME = """
    QMainWindow {
        background-color: #1e1e1e;
    }
    QWidget {
        background-color: #1e1e1e;
        color: #e0e0e0;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 10pt;
    }
    QGroupBox {
        border: 1px solid #3a3a3a;
        border-radius: 5px;
        margin-top: 10px;
        padding-top: 10px;
        font-weight: bold;
        color: #ffffff;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }
    QLabel {
        color: #e0e0e0;
        background-color: transparent;
    }
    QComboBox, QSpinBox, QDoubleSpinBox {
        background-color: #2d2d2d;
        border: 1px solid #3a3a3a;
        border-radius: 3px;
        padding: 5px;
        min-width: 120px;
        color: #e0e0e0;
    }
    QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
        border: 1px solid #0d7377;
    }
    QComboBox::drop-down {
        border: none;
        background-color: #3a3a3a;
        width: 20px;
    }
    QComboBox::down-arrow {
        image: none;
        border: 2px solid #e0e0e0;
        width: 6px;
        height: 6px;
        border-width: 0 2px 2px 0;
        transform: rotate(45deg);
    }
    QPushButton {
        background-color: #0d7377;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #14a085;
    }
    QPushButton:pressed {
        background-color: #0a5f63;
    }
    QPushButton:disabled {
        background-color: #3a3a3a;
        color: #666666;
    }
    QListWidget {
        background-color: #2d2d2d;
        border: 2px dashed #3a3a3a;
        border-radius: 4px;
        padding: 5px;
        color: #e0e0e0;
    }
    QListWidget::item {
        padding: 4px;
        border-radius: 2px;
    }
    QListWidget::item:selected {
        background-color: #0d7377;
        color: white;
    }
    QTextEdit {
        background-color: #2d2d2d;
        border: 1px solid #3a3a3a;
        border-radius: 4px;
        padding: 5px;
        color: #e0e0e0;
        font-family: 'Consolas', 'Courier New', monospace;
    }
    QProgressBar {
        border: 1px solid #3a3a3a;
        border-radius: 4px;
        text-align: center;
        background-color: #2d2d2d;
        color: #e0e0e0;
        height: 25px;
    }
    QProgressBar::chunk {
        background-color: #0d7377;
        border-radius: 3px;
    }
    QCheckBox {
        spacing: 5px;
        color: #e0e0e0;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border: 1px solid #3a3a3a;
        border-radius: 3px;
        background-color: #2d2d2d;
    }
    QCheckBox::indicator:checked {
        background-color: #0d7377;
        border: 1px solid #0d7377;
    }
    QTabWidget::pane {
        border: 1px solid #3a3a3a;
        border-radius: 4px;
        background-color: #1e1e1e;
    }
    QTabBar::tab {
        background-color: #2d2d2d;
        color: #e0e0e0;
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background-color: #0d7377;
        color: white;
    }
    QTabBar::tab:hover:!selected {
        background-color: #3a3a3a;
    }
    QSplitter::handle {
        background-color: #3a3a3a;
        height: 2px;
    }
    QSplitter::handle:hover {
        background-color: #0d7377;
    }
    QScrollArea {
        background-color: transparent;
        border: none;
    }
    QScrollArea > QWidget > QWidget {
        background-color: transparent;
    }
    QScrollBar:vertical {
        background-color: #2d2d2d;
        width: 12px;
        border-radius: 6px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background-color: #4a4a4a;
        border-radius: 5px;
        min-height: 30px;
        margin: 2px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: #0d7377;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
        background: none;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
    QFrame#CollapsibleSection {
        background-color: transparent;
    }
    QToolButton#CollapsibleToggle {
        background-color: #252525;
        border: 1px solid #3a3a3a;
        border-radius: 5px;
        color: #ffffff;
        font-weight: bold;
        padding: 8px 10px;
        text-align: left;
    }
    QToolButton#CollapsibleToggle:hover {
        background-color: #2d2d2d;
        border: 1px solid #0d7377;
    }
    QToolButton#CollapsibleToggle:checked {
        background-color: #2a2a2a;
        border-bottom-left-radius: 0;
        border-bottom-right-radius: 0;
    }
    QWidget#CollapsibleContent {
        background-color: #1a1a1a;
        border: 1px solid #3a3a3a;
        border-top: none;
        border-bottom-left-radius: 5px;
        border-bottom-right-radius: 5px;
        padding: 4px;
    }
"""


def apply_modern_style(widget):
    """Apply the dark theme to a top-level widget."""
    widget.setStyleSheet(DARK_THEME)
