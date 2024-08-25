import sys
import re
import requests
import json
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class TranslatorThread(QThread):
    update_signal = pyqtSignal(int, str)
    
    def __init__(self, rows, texts, source_lang, target_lang, translate_func):
        QThread.__init__(self)
        self.rows = rows
        self.texts = texts
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.translate_func = translate_func

    def run(self):
        for row, text in zip(self.rows, self.texts):
            translated_text = self.translate_func(text, self.source_lang, self.target_lang)
            self.update_signal.emit(row, translated_text)

class TranslatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('SRT Translator (Cantonese to English)')
        self.setGeometry(100, 100, 1000, 600)

        layout = QVBoxLayout()

        # File selection
        file_layout = QHBoxLayout()
        self.filePathLabel = QLabel("No file selected")
        file_layout.addWidget(self.filePathLabel)
        self.selectFileBtn = QPushButton('Select SRT File')
        self.selectFileBtn.clicked.connect(self.select_file)
        file_layout.addWidget(self.selectFileBtn)
        layout.addLayout(file_layout)

        # Subtitle table
        self.subtitleTable = QTableWidget()
        self.subtitleTable.setColumnCount(5)
        self.subtitleTable.setHorizontalHeaderLabels(["Time From", "Time Until", "Original", "Translated", ""])
        self.subtitleTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.subtitleTable)

        # Buttons layout
        button_layout = QHBoxLayout()

        # Translate All button
        self.translateAllBtn = QPushButton('Translate All')
        self.translateAllBtn.clicked.connect(self.translate_all)
        button_layout.addWidget(self.translateAllBtn)

        # Block Translate button
        self.blockTranslateBtn = QPushButton('Block Translate')
        self.blockTranslateBtn.clicked.connect(self.block_translate)
        button_layout.addWidget(self.blockTranslateBtn)

        # Save button
        self.saveBtn = QPushButton('Save Translated SRT')
        self.saveBtn.clicked.connect(self.save_translated_srt)
        button_layout.addWidget(self.saveBtn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select SRT File", "", "SRT Files (*.srt)")
        if file_path:
            self.filePathLabel.setText(file_path)
            with open(file_path, 'r', encoding='utf-8') as file:
                srt_content = file.read()
            self.load_subtitles(srt_content)

    def load_subtitles(self, srt_content):
        subtitles = self.parse_srt(srt_content)
        self.subtitleTable.setRowCount(len(subtitles))
        for row, (index, time_from, time_until, text) in enumerate(subtitles):
            self.subtitleTable.setItem(row, 0, QTableWidgetItem(time_from))
            self.subtitleTable.setItem(row, 1, QTableWidgetItem(time_until))
            self.subtitleTable.setItem(row, 2, QTableWidgetItem(text))
            self.subtitleTable.setItem(row, 3, QTableWidgetItem(""))
            
            translateBtn = QPushButton('Translate')
            translateBtn.clicked.connect(lambda _, r=row: self.translate_row(r))
            self.subtitleTable.setCellWidget(row, 4, translateBtn)

    def parse_srt(self, srt_content):
        pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.*\n)*?)\n'
        return re.findall(pattern, srt_content, re.MULTILINE)

    def translate_row(self, row):
        original_text = self.subtitleTable.item(row, 2).text()
        translated_text = self.google_translate(original_text, 'yue', 'en')
        self.subtitleTable.setItem(row, 3, QTableWidgetItem(translated_text))

    def google_translate(self, text, source_lang, target_lang):
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": source_lang,
            "tl": target_lang,
            "dt": "t",
            "q": text
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
        
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            result = json.loads(response.text)
            translated_text = ''.join([sentence[0] for sentence in result[0]])
            return translated_text
        else:
            raise Exception(f"Translation request failed with status code: {response.status_code}")

    def translate_all(self):
        rows = range(self.subtitleTable.rowCount())
        texts = [self.subtitleTable.item(row, 2).text() for row in rows]
        self.translate_thread = TranslatorThread(rows, texts, 'yue', 'en', self.google_translate)
        self.translate_thread.update_signal.connect(self.update_translation)
        self.translate_thread.start()

    def block_translate(self):
        selected_ranges = self.subtitleTable.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "Warning", "Please select a range of subtitles to translate.")
            return
        
        rows = []
        texts = []
        for range_ in selected_ranges:
            for row in range(range_.topRow(), range_.bottomRow() + 1):
                rows.append(row)
                texts.append(self.subtitleTable.item(row, 2).text())
        
        self.translate_thread = TranslatorThread(rows, texts, 'yue', 'en', self.google_translate)
        self.translate_thread.update_signal.connect(self.update_translation)
        self.translate_thread.start()

    def update_translation(self, row, translated_text):
        self.subtitleTable.setItem(row, 3, QTableWidgetItem(translated_text))

    def save_translated_srt(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Translated SRT", "", "SRT Files (*.srt)")
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as file:
                for row in range(self.subtitleTable.rowCount()):
                    index = str(row + 1)
                    time_from = self.subtitleTable.item(row, 0).text()
                    time_until = self.subtitleTable.item(row, 1).text()
                    translated_text = self.subtitleTable.item(row, 3).text()
                    if not translated_text:
                        translated_text = self.subtitleTable.item(row, 2).text()  # Use original if not translated
                    file.write(f"{index}\n{time_from} --> {time_until}\n{translated_text}\n\n")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = TranslatorApp()
    ex.show()
    sys.exit(app.exec_())