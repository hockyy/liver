import sys
import re
import requests
import json
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class TranslatorThread(QThread):
    update_signal = pyqtSignal(int, str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, rows, texts, source_lang, target_lang, translate_func):
        QThread.__init__(self)
        self.rows = rows
        self.texts = texts
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.translate_func = translate_func
        self.stop_flag = False

    def run(self):
        try:
            for row, text in zip(self.rows, self.texts):
                if self.stop_flag:
                    break
                translated_text = self.translate_func(text, self.source_lang, self.target_lang)
                if translated_text.startswith("Error:"):
                    self.error_signal.emit(translated_text)
                    return
                self.update_signal.emit(row, translated_text)
        except Exception as e:
            self.error_signal.emit(f"Error: {str(e)}")
        finally:
            self.finished_signal.emit()

    def stop(self):
        self.stop_flag = True
        
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

        # Stop button
        self.stopBtn = QPushButton('Stop Translation')
        self.stopBtn.clicked.connect(self.stop_translation)
        self.stopBtn.setEnabled(False)  # Disable the button initially
        button_layout.addWidget(self.stopBtn)

        # Save button
        self.saveBtn = QPushButton('Save Translated SRT')
        self.saveBtn.clicked.connect(self.save_translated_srt)
        button_layout.addWidget(self.saveBtn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select SRT File", "", "SRT Files (*.srt)")
        if file_path:
            self.current_file_path = file_path
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
        if not text or text.strip() == '':
            return ''
        try:
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
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = json.loads(response.text)
                translated_text = ''.join([sentence[0] for sentence in result[0]])
                return translated_text
            else:
                return f"Error: Translation request failed with status code: {response.status_code}"
        except requests.RequestException as e:
            return f"Error: {str(e)}"
        except json.JSONDecodeError:
            return "Error: Failed to decode JSON response"
        except Exception as e:
            return f"Error: {str(e)}"

    def translate_all(self):
        if not self.current_file_path:
            QMessageBox.warning(self, "Warning", "Please select an SRT file first.")
            return

        rows = []
        texts = []
        for row in range(self.subtitleTable.rowCount()):
            translated_text = self.subtitleTable.item(row, 3).text()
            if not translated_text:  # Check if the translation is empty
                rows.append(row)
                texts.append(self.subtitleTable.item(row, 2).text())
        
        if not texts:
            QMessageBox.information(self, "Information", "All lines have already been translated.")
            return

        self.translate_thread = TranslatorThread(rows, texts, 'yue', 'en', self.google_translate)
        self.translate_thread.update_signal.connect(self.update_translation)
        self.translate_thread.error_signal.connect(self.show_error_message)
        self.translate_thread.finished_signal.connect(self.translation_finished)
        self.translate_thread.start()

        # Disable translate buttons and enable stop button
        self.translateAllBtn.setEnabled(False)
        self.blockTranslateBtn.setEnabled(False)
        self.stopBtn.setEnabled(True)

    def block_translate(self):
        selected_ranges = self.subtitleTable.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "Warning", "Please select a range of subtitles to translate.")
            return
        
        rows = []
        texts = []
        for range_ in selected_ranges:
            for row in range(range_.topRow(), range_.bottomRow() + 1):
                translated_text = self.subtitleTable.item(row, 3).text()
                if not translated_text:  # Check if the translation is empty
                    rows.append(row)
                    texts.append(self.subtitleTable.item(row, 2).text())
        
        if not texts:
            QMessageBox.information(self, "Information", "All selected lines have already been translated.")
            return

        self.translate_thread = TranslatorThread(rows, texts, 'yue', 'en', self.google_translate)
        self.translate_thread.update_signal.connect(self.update_translation)
        self.translate_thread.error_signal.connect(self.show_error_message)
        self.translate_thread.finished_signal.connect(self.translation_finished)
        self.translate_thread.start()

        # Disable translate buttons and enable stop button
        self.translateAllBtn.setEnabled(False)
        self.blockTranslateBtn.setEnabled(False)
        self.stopBtn.setEnabled(True)

    def stop_translation(self):
        if self.translate_thread and self.translate_thread.isRunning():
            self.translate_thread.stop()
            self.stopBtn.setEnabled(False)  # Disable the stop button immediately

    def translation_finished(self):
        # Re-enable translate buttons and disable stop button
        self.translateAllBtn.setEnabled(True)
        self.blockTranslateBtn.setEnabled(True)
        self.stopBtn.setEnabled(False)
        
        # Automatically save the translated file
        self.save_translated_srt(auto_save=True)
        
        QMessageBox.information(self, "Information", "Translation process finished and file saved.")

    def save_translated_srt(self, auto_save=False):
        if auto_save:
            if self.current_file_path:
                directory, filename = os.path.split(self.current_file_path)
                name, _ = os.path.splitext(filename)
                new_filename = f"{name}.en.srt"
                file_path = os.path.join(directory, new_filename)
            else:
                QMessageBox.warning(self, "Warning", "No file was selected. Cannot auto-save.")
                return
        else:
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
            
            if not auto_save:
                QMessageBox.information(self, "Information", f"File saved successfully as {file_path}")

    def show_error_message(self, error_message):
        QMessageBox.critical(self, "Error", error_message)

    def update_translation(self, row, translated_text):
        self.subtitleTable.setItem(row, 3, QTableWidgetItem(translated_text))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = TranslatorApp()
    ex.show()
    sys.exit(app.exec_())