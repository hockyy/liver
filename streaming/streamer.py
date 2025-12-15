"""
Streaming Tools Launcher - A beautiful PyQt5 GUI for launching streaming applications
"""

import sys
import os
import json
import subprocess
import webbrowser
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QDialog,
    QLineEdit, QFormLayout, QMessageBox, QFrame, QScrollArea,
    QGraphicsDropShadowEffect, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QFontDatabase


CONFIG_FILE = Path(__file__).parent / "streamer_config.json"

DEFAULT_TOOLS = [
    {"name": "VTS-POG", "path": "C:\\Program Files\\vts-pog\\VTS-POG.exe", "type": "exe"},
    {"name": "MinimizeToTray", "path": "C:\\Program Files\\MinimizeToTray\\MinimizeToTray.exe", "type": "exe"},
    {"name": "Vtube Studio (Steam)", "path": "steam://rungameid/1325860", "type": "steam"},
    {"name": "VBridger (Steam)", "path": "steam://rungameid/1898830", "type": "steam"},
    {"name": "Streamer.bot", "path": "C:\\Program Files\\Streamer.bot-x64-1.0.0\\Streamer.bot.exe", "type": "exe"},
    {"name": "Hideous", "path": "C:\\Program Files\\Hideous\\Hideous.exe", "type": "exe"},
    {"name": "Twitch Dashboard", "path": "https://dashboard.twitch.tv/u/mikiraIRL/stream-manager", "type": "url"},
]


STYLE_SHEET = """
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0f0c29, stop:0.5 #302b63, stop:1 #24243e);
}

QWidget#centralWidget {
    background: transparent;
}

QLabel#titleLabel {
    color: #ff6b9d;
    font-size: 28px;
    font-weight: bold;
    padding: 10px;
}

QLabel#subtitleLabel {
    color: #a0a0c0;
    font-size: 12px;
    padding-bottom: 15px;
}

QFrame#toolCard {
    background: rgba(30, 30, 50, 0.85);
    border: 1px solid rgba(255, 107, 157, 0.3);
    border-radius: 12px;
    padding: 8px;
    margin: 4px;
}

QFrame#toolCard:hover {
    background: rgba(45, 45, 70, 0.95);
    border: 1px solid rgba(255, 107, 157, 0.6);
}

QLabel#toolName {
    color: #ffffff;
    font-size: 14px;
    font-weight: bold;
}

QLabel#toolPath {
    color: #8888aa;
    font-size: 10px;
}

QLabel#toolType {
    color: #ff6b9d;
    font-size: 9px;
    font-weight: bold;
    padding: 2px 8px;
    background: rgba(255, 107, 157, 0.2);
    border-radius: 8px;
}

QPushButton#launchBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff6b9d, stop:1 #c44569);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 11px;
    min-width: 70px;
}

QPushButton#launchBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff85b1, stop:1 #d45579);
}

QPushButton#launchBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #e55585, stop:1 #b43559);
}

QPushButton#launchAllBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6c5ce7, stop:1 #a855f7);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 15px 40px;
    font-weight: bold;
    font-size: 16px;
    min-width: 200px;
}

QPushButton#launchAllBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c6cf7, stop:1 #b865ff);
}

QPushButton#launchAllBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5c4cd7, stop:1 #9845e7);
}

QPushButton#actionBtn {
    background: rgba(60, 60, 90, 0.8);
    color: #c0c0e0;
    border: 1px solid rgba(255, 107, 157, 0.3);
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 12px;
}

QPushButton#actionBtn:hover {
    background: rgba(80, 80, 110, 0.9);
    border: 1px solid rgba(255, 107, 157, 0.5);
    color: #ffffff;
}

QPushButton#deleteBtn {
    background: rgba(220, 50, 50, 0.3);
    color: #ff6b6b;
    border: 1px solid rgba(220, 50, 50, 0.4);
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 10px;
    min-width: 50px;
}

QPushButton#deleteBtn:hover {
    background: rgba(220, 50, 50, 0.5);
    border: 1px solid rgba(220, 50, 50, 0.7);
}

QScrollArea {
    background: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}

QScrollBar:vertical {
    background: rgba(30, 30, 50, 0.5);
    width: 10px;
    border-radius: 5px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: rgba(255, 107, 157, 0.5);
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(255, 107, 157, 0.7);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QDialog {
    background: #1e1e32;
}

QDialog QLabel {
    color: #ffffff;
    font-size: 12px;
}

QDialog QLineEdit {
    background: rgba(40, 40, 60, 0.9);
    border: 1px solid rgba(255, 107, 157, 0.3);
    border-radius: 8px;
    padding: 10px;
    color: #ffffff;
    font-size: 12px;
}

QDialog QLineEdit:focus {
    border: 1px solid rgba(255, 107, 157, 0.7);
}

QDialog QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff6b9d, stop:1 #c44569);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 25px;
    font-weight: bold;
    font-size: 12px;
}

QDialog QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff85b1, stop:1 #d45579);
}

QDialog QPushButton#cancelBtn {
    background: rgba(60, 60, 90, 0.8);
    border: 1px solid rgba(255, 107, 157, 0.3);
}

QDialog QPushButton#cancelBtn:hover {
    background: rgba(80, 80, 110, 0.9);
}

QFrame#statusBar {
    background: rgba(20, 20, 35, 0.9);
    border-top: 1px solid rgba(255, 107, 157, 0.2);
    padding: 8px;
}

QLabel#statusLabel {
    color: #6c6c8c;
    font-size: 11px;
}
"""


class ToolCard(QFrame):
    """A card widget representing a single tool."""
    
    def __init__(self, tool_data: dict, on_launch, on_delete, parent=None):
        super().__init__(parent)
        self.tool_data = tool_data
        self.on_launch = on_launch
        self.on_delete = on_delete
        self.setObjectName("toolCard")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        
        # Icon based on type
        type_icons = {
            "exe": "⚙️",
            "steam": "🎮",
            "url": "🌐"
        }
        icon_label = QLabel(type_icons.get(self.tool_data.get("type", "exe"), "📦"))
        icon_label.setStyleSheet("font-size: 24px;")
        icon_label.setFixedWidth(40)
        layout.addWidget(icon_label)
        
        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(self.tool_data["name"])
        name_label.setObjectName("toolName")
        info_layout.addWidget(name_label)
        
        path_label = QLabel(self.tool_data["path"])
        path_label.setObjectName("toolPath")
        path_label.setWordWrap(True)
        info_layout.addWidget(path_label)
        
        layout.addLayout(info_layout, 1)
        
        # Type badge
        type_label = QLabel(self.tool_data.get("type", "exe").upper())
        type_label.setObjectName("toolType")
        type_label.setFixedHeight(20)
        layout.addWidget(type_label)
        
        # Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)
        
        launch_btn = QPushButton("Launch")
        launch_btn.setObjectName("launchBtn")
        launch_btn.setCursor(Qt.PointingHandCursor)
        launch_btn.clicked.connect(lambda: self.on_launch(self.tool_data))
        btn_layout.addWidget(launch_btn)
        
        delete_btn = QPushButton("Remove")
        delete_btn.setObjectName("deleteBtn")
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.clicked.connect(lambda: self.on_delete(self.tool_data))
        btn_layout.addWidget(delete_btn)
        
        layout.addLayout(btn_layout)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)


class AddToolDialog(QDialog):
    """Dialog for adding a new tool."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Tool")
        self.setFixedSize(450, 280)
        self.setModal(True)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("✨ Add New Tool")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff6b9d; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., OBS Studio")
        form_layout.addRow("Name:", self.name_input)
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("e.g., C:\\Program Files\\OBS\\obs64.exe")
        form_layout.addRow("Path:", self.path_input)
        
        self.type_input = QLineEdit()
        self.type_input.setPlaceholderText("exe, steam, or url")
        self.type_input.setText("exe")
        form_layout.addRow("Type:", self.type_input)
        
        layout.addLayout(form_layout)
        
        # Hint
        hint = QLabel("💡 For Steam games, use: steam://rungameid/APPID\n     For websites, use: https://...")
        hint.setStyleSheet("color: #8888aa; font-size: 10px; margin-top: 5px;")
        layout.addWidget(hint)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        add_btn = QPushButton("Add Tool")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self.accept)
        btn_layout.addWidget(add_btn)
        
        layout.addLayout(btn_layout)
        
    def get_tool_data(self) -> dict:
        tool_type = self.type_input.text().strip().lower()
        if tool_type not in ("exe", "steam", "url"):
            tool_type = "exe"
        return {
            "name": self.name_input.text().strip(),
            "path": self.path_input.text().strip(),
            "type": tool_type
        }


class StreamerLauncher(QMainWindow):
    """Main window for the Streaming Tools Launcher."""
    
    def __init__(self):
        super().__init__()
        self.tools = []
        self.load_config()
        self.setup_ui()
        self.setStyleSheet(STYLE_SHEET)
        
    def load_config(self):
        """Load tools configuration from file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.tools = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.tools = DEFAULT_TOOLS.copy()
        else:
            self.tools = DEFAULT_TOOLS.copy()
            self.save_config()
            
    def save_config(self):
        """Save tools configuration to file."""
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.tools, f, indent=2, ensure_ascii=False)
            
    def setup_ui(self):
        self.setWindowTitle("🎬 Streaming Tools Launcher")
        self.setMinimumSize(550, 650)
        self.resize(550, 700)
        
        # Central widget
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 10)
        main_layout.setSpacing(0)
        
        # Header
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("🎬 Streaming Tools")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)
        
        subtitle = QLabel("Launch all your streaming apps with one click")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle)
        
        main_layout.addLayout(header_layout)
        
        # Launch All button
        launch_all_btn = QPushButton("🚀  Launch All Tools")
        launch_all_btn.setObjectName("launchAllBtn")
        launch_all_btn.setCursor(Qt.PointingHandCursor)
        launch_all_btn.clicked.connect(self.launch_all)
        
        launch_all_container = QHBoxLayout()
        launch_all_container.addStretch()
        launch_all_container.addWidget(launch_all_btn)
        launch_all_container.addStretch()
        main_layout.addLayout(launch_all_container)
        
        main_layout.addSpacing(20)
        
        # Tools list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.tools_container = QWidget()
        self.tools_layout = QVBoxLayout(self.tools_container)
        self.tools_layout.setContentsMargins(0, 0, 10, 0)
        self.tools_layout.setSpacing(8)
        self.tools_layout.setAlignment(Qt.AlignTop)
        
        scroll_area.setWidget(self.tools_container)
        main_layout.addWidget(scroll_area, 1)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        action_layout.setContentsMargins(0, 15, 0, 10)
        
        add_btn = QPushButton("➕ Add Tool")
        add_btn.setObjectName("actionBtn")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self.add_tool)
        action_layout.addWidget(add_btn)
        
        action_layout.addStretch()
        
        reset_btn = QPushButton("🔄 Reset to Default")
        reset_btn.setObjectName("actionBtn")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.clicked.connect(self.reset_to_default)
        action_layout.addWidget(reset_btn)
        
        main_layout.addLayout(action_layout)
        
        # Status bar
        status_frame = QFrame()
        status_frame.setObjectName("statusBar")
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        self.status_label = QLabel(f"📊 {len(self.tools)} tools configured")
        self.status_label.setObjectName("statusLabel")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        version_label = QLabel("v1.0.0")
        version_label.setObjectName("statusLabel")
        status_layout.addWidget(version_label)
        
        main_layout.addWidget(status_frame)
        
        # Populate tools
        self.refresh_tools()
        
    def refresh_tools(self):
        """Refresh the tools list display."""
        # Clear existing cards
        while self.tools_layout.count():
            item = self.tools_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Add tool cards
        for tool in self.tools:
            card = ToolCard(tool, self.launch_tool, self.delete_tool)
            self.tools_layout.addWidget(card)
            
        # Update status
        self.status_label.setText(f"📊 {len(self.tools)} tools configured")
        
    def launch_tool(self, tool: dict):
        """Launch a single tool."""
        path = tool["path"]
        tool_type = tool.get("type", "exe")
        
        try:
            if tool_type == "url" or path.startswith("http"):
                webbrowser.open(path)
            elif tool_type == "steam" or path.startswith("steam://"):
                os.startfile(path)
            else:
                # Regular executable
                if os.path.exists(path):
                    subprocess.Popen([path], shell=True)
                else:
                    # Try using explorer as fallback
                    os.startfile(path)
                    
            self.status_label.setText(f"✅ Launched: {tool['name']}")
            
        except Exception as e:
            self.status_label.setText(f"❌ Failed to launch: {tool['name']}")
            QMessageBox.warning(
                self,
                "Launch Failed",
                f"Could not launch {tool['name']}:\n{str(e)}"
            )
            
    def launch_all(self):
        """Launch all tools with a delay between each."""
        self.status_label.setText("🚀 Launching all tools...")
        
        for i, tool in enumerate(self.tools):
            # Use QTimer to stagger launches
            QTimer.singleShot(i * 2000, lambda t=tool: self.launch_tool(t))
            
        QTimer.singleShot(
            len(self.tools) * 2000 + 500,
            lambda: self.status_label.setText("✅ All tools launched!")
        )
        
    def add_tool(self):
        """Open dialog to add a new tool."""
        dialog = AddToolDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            tool_data = dialog.get_tool_data()
            if tool_data["name"] and tool_data["path"]:
                self.tools.append(tool_data)
                self.save_config()
                self.refresh_tools()
                self.status_label.setText(f"✅ Added: {tool_data['name']}")
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Input",
                    "Please provide both a name and path for the tool."
                )
                
    def delete_tool(self, tool: dict):
        """Delete a tool from the list."""
        reply = QMessageBox.question(
            self,
            "Remove Tool",
            f"Are you sure you want to remove '{tool['name']}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.tools = [t for t in self.tools if t != tool]
            self.save_config()
            self.refresh_tools()
            self.status_label.setText(f"🗑️ Removed: {tool['name']}")
            
    def reset_to_default(self):
        """Reset tools list to default configuration."""
        reply = QMessageBox.question(
            self,
            "Reset to Default",
            "This will reset all tools to the default configuration.\nAre you sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.tools = DEFAULT_TOOLS.copy()
            self.save_config()
            self.refresh_tools()
            self.status_label.setText("🔄 Reset to default configuration")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set application-wide font
    font = QFont("Segoe UI", 15)
    app.setFont(font)
    
    window = StreamerLauncher()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

