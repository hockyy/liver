import sys
import json
import random
import pycantonese
import requests
import webbrowser
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit, QInputDialog, QShortcut, QHBoxLayout
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
        self.setGeometry(300, 300, 500, 600)

        layout = QVBoxLayout()

        self.card_widget = QWidget(self)
        self.card_widget.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                border: 2px solid #a0a0a0;
                border-radius: 15px;
            }
        """)
        self.card_widget.setFixedSize(450, 300)
        card_layout = QVBoxLayout(self.card_widget)

        self.word_label = QLabel('Click to load words', self)
        self.word_label.setAlignment(Qt.AlignCenter)
        self.word_label.setFont(QFont('Arial', 36))
        self.word_label.setWordWrap(True)
        card_layout.addWidget(self.word_label)

        layout.addWidget(self.card_widget, alignment=Qt.AlignCenter)

        button_layout = QHBoxLayout()
        self.next_button = QPushButton('Next (Space / Right Arrow)', self)
        self.next_button.clicked.connect(self.next_card)
        button_layout.addWidget(self.next_button)

        self.flip_button = QPushButton('Flip (Up Arrow)', self)
        self.flip_button.clicked.connect(self.flip_card)
        button_layout.addWidget(self.flip_button)

        layout.addLayout(button_layout)

        self.load_gist_button = QPushButton('Load Gist', self)
        self.load_gist_button.clicked.connect(self.load_gist)
        layout.addWidget(self.load_gist_button)

        self.word_list_text = QTextEdit(self)
        self.word_list_text.setReadOnly(True)
        layout.addWidget(self.word_list_text)

        self.setLayout(layout)

        self.card_widget.mousePressEvent = self.flip_card

        # Add keyboard shortcuts
        QShortcut(QKeySequence(Qt.Key_Space), self, self.next_card)
        QShortcut(QKeySequence(Qt.Key_Right), self, self.next_card)
        QShortcut(QKeySequence(Qt.Key_Left), self, self.copy_current_word)
        QShortcut(QKeySequence(Qt.Key_Up), self, self.flip_card)
        QShortcut(QKeySequence(Qt.Key_Down), self, self.open_dictionary)

    def load_gist(self):
        gists = self.fetch_gists()
        if gists:
            gist, ok = QInputDialog.getItem(self, "Select a Gist", "Choose a gist:", gists, 0, False)
            if ok and gist:
                gist_id = gist.split(' - ')[0]
                self.load_gist_content(gist_id)

    def fetch_gists(self):
        try:
            response = requests.get('https://api.github.com/users/hockyy/gists')
            response.raise_for_status()
            gists = response.json()
            return [f"{gist['id']} - {list(gist['files'].keys())[0]}" for gist in gists]
        except Exception as e:
            print(f"Error fetching gists: {e}")
            return []

    def load_gist_content(self, gist_id):
        try:
            response = requests.get(f'https://api.github.com/gists/{gist_id}')
            response.raise_for_status()
            gist_data = response.json()
            file_content = list(gist_data['files'].values())[0]['content']
            self.word_data = json.loads(file_content)
            self.process_loaded_data()
        except Exception as e:
            print(f"Error loading gist content: {e}")

    def process_loaded_data(self):
        self.word_list = list(self.word_data.keys())
        self.word_list_text.setText("\n".join(self.word_list))
        self.next_card()

    def next_card(self):
        if self.word_list:
            self.current_word = random.choice(self.word_list)
            self.word_label.setText(self.current_word)
            self.card_face = "front"

    def flip_card(self, event=None):
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

    def open_dictionary(self):
        if self.current_word:
            url = f"https://words.hk/zidin/{self.current_word}"
            webbrowser.open(url)
            
if __name__ == '__main__':
    pycantonese.characters_to_jyutping("一")
    app = QApplication(sys.argv)
    ex = FlashcardApp()
    ex.show()
    sys.exit(app.exec_())