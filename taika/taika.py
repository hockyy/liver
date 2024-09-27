import sys
import json
import random
import pycantonese
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QTextEdit, QInputDialog, QShortcut
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtCore import Qt

class FlashcardApp(QWidget):
    def __init__(self):
        super().__init__()
        self.word_data = {}
        self.word_list = []
        self.current_word = None
        self.card_face = "front"
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Chinese Flashcard App')
        self.setGeometry(300, 300, 500, 600)  # Increased window size

        layout = QVBoxLayout()

        self.card_widget = QWidget(self)
        self.card_widget.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                border: 2px solid #a0a0a0;
                border-radius: 15px;
            }
        """)
        self.card_widget.setFixedSize(450, 300)  # Increased card size
        card_layout = QVBoxLayout(self.card_widget)

        self.word_label = QLabel('Click to load words', self)
        self.word_label.setAlignment(Qt.AlignCenter)
        self.word_label.setFont(QFont('Arial', 36))  # Increased font size
        self.word_label.setWordWrap(True)
        card_layout.addWidget(self.word_label)

        layout.addWidget(self.card_widget, alignment=Qt.AlignCenter)

        self.next_button = QPushButton('Next (Space / Right Arrow)', self)
        self.next_button.clicked.connect(self.next_card)
        layout.addWidget(self.next_button)

        self.load_file_button = QPushButton('Load JSON from File', self)
        self.load_file_button.clicked.connect(self.load_json_file)
        layout.addWidget(self.load_file_button)

        self.load_url_button = QPushButton('Load JSON from URL', self)
        self.load_url_button.clicked.connect(self.load_json_url)
        layout.addWidget(self.load_url_button)

        self.word_list_text = QTextEdit(self)
        self.word_list_text.setReadOnly(True)
        self.word_list_text.hide()  # Hide the word list text

        self.setLayout(layout)

        self.card_widget.mousePressEvent = self.flip_card

        # Add keyboard shortcuts
        QShortcut(QKeySequence(Qt.Key_Space), self, self.next_card)
        QShortcut(QKeySequence(Qt.Key_Right), self, self.next_card)
        QShortcut(QKeySequence(Qt.Key_Left), self, self.copy_current_word)
        QShortcut(QKeySequence(Qt.Key_Up), self, self.flip_card)

    def load_json_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open JSON File", "", "JSON Files (*.json)")
        if file_name:
            self.load_json(file_name)

    def load_json_url(self):
        url, ok = QInputDialog.getText(self, 'Load JSON from URL', 'Enter URL:')
        if ok and url:
            try:
                response = requests.get(url)
                response.raise_for_status()
                self.word_data = response.json()
                self.process_loaded_data()
            except Exception as e:
                print(f"Error loading JSON from URL: {e}")

    def load_json(self, source):
        try:
            with open(source, 'r', encoding='utf-8') as file:
                self.word_data = json.load(file)
            self.process_loaded_data()
        except Exception as e:
            print(f"Error loading JSON: {e}")

    def process_loaded_data(self):
        self.word_list = list(self.word_data.keys())
        self.word_list_text.setText("\n".join(self.word_list))
        self.next_card()

    def next_card(self):
        if self.word_list:
            self.current_word = random.choice(self.word_list)
            self.word_label.setText(self.current_word)
            self.card_face = "front"

    def flip_card(self, event = None):
        if self.current_word:
            if self.card_face == "front":
                jyutping = pycantonese.characters_to_jyutping(self.current_word)
                jyutping_str = ' '.join([f"{char}: {pinyin}" for char, pinyin in jyutping])
                back_text = f"{jyutping_str}"
                self.word_label.setText(back_text)
                self.card_face = "back"
            else:
                self.word_label.setText(self.current_word)
                self.card_face = "front"

    def copy_words(self):
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(self.word_list))

    def copy_current_word(self):
        if self.current_word:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_word)
            print(f"Copied: {self.current_word}")

if __name__ == '__main__':
    pycantonese.characters_to_jyutping("一")
    app = QApplication(sys.argv)
    ex = FlashcardApp()
    ex.show()
    sys.exit(app.exec_())