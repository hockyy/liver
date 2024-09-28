import sys
import re
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QMessageBox, QSplitter
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QClipboard
import pycantonese

class LyricsConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Lyrics to Ruby HTML Converter')
        self.setGeometry(100, 100, 1000, 800)  # Increased width and heigh

        layout = QVBoxLayout()

        # Input section
        input_label = QLabel('Input Chinese Text (Cantonese):')
        layout.addWidget(input_label)

        self.input_text = QTextEdit()
        layout.addWidget(self.input_text)

        convert_button = QPushButton('Convert')
        convert_button.clicked.connect(self.convert_lyrics)
        layout.addWidget(convert_button)
        # Output and Preview section
        output_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(output_splitter)

        # Output section
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)

        output_label = QLabel('Output HTML:')
        output_layout.addWidget(output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(100)  # Limit height of output
        output_layout.addWidget(self.output_text)

        copy_button = QPushButton('Copy to Clipboard')
        copy_button.clicked.connect(self.copy_to_clipboard)
        output_layout.addWidget(copy_button)

        output_splitter.addWidget(output_widget)

        # Preview section
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        preview_label = QLabel('HTML Preview:')
        preview_layout.addWidget(preview_label)

        self.preview_web = QWebEngineView()
        preview_layout.addWidget(self.preview_web)

        output_splitter.addWidget(preview_widget)

        # Set the initial sizes of the splitter
        output_splitter.setSizes([100, 600])  # Much more space for preview

        self.setLayout(layout)


    def convert_lyrics(self):
        input_text = self.input_text.toPlainText()
        converted_text = self.text_to_ruby_html(input_text)
        self.output_text.setPlainText(converted_text)
        self.update_preview(converted_text)

    def text_to_ruby_html(self, text):
        result = []
        for line in text.split('\n'):
            converted_line = []
            words = pycantonese.characters_to_jyutping(line)
            for word, pronunciation in words:
                if not pronunciation:
                    continue
                ruby_text = ''
                prons = re.findall(r'\w+?\d', pronunciation)
                for char, pron in zip(word, prons):
                    ruby_text += f'<ruby>{char}<rt>{pron}</rt></ruby>'
                converted_line.append(ruby_text)
            result.append(''.join(converted_line) + '<br>')
        return '\n'.join(result)

    def update_preview(self, html_content):
        full_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; font-size: 16px; }}
                ruby {{ ruby-align: center; }}
                rt {{ font-size: 0.7em; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        self.preview_web.setHtml(full_html)

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.output_text.toPlainText())
        QMessageBox.information(self, 'Copied', 'Text copied to clipboard!')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LyricsConverter()
    ex.show()
    sys.exit(app.exec_())