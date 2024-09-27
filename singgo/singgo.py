import sys
import os
import subprocess
import threading
import ffmpeg
import time
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QSplitter, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont



class LRCGenerator(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.lyrics = []
        self.current_line = 0
        self.time_stamps = {}
        self.audio_file = None
        self.is_playing = False
        self.ffplay_process = None
        self.start_time = 0
        self.pause_time = 0
        self.total_pause_time = 0
        self.current_position = 0

    def initUI(self):
        layout = QVBoxLayout()

        # Create a splitter for lyrics input and table
        splitter = QSplitter(Qt.Vertical)

        # Lyrics input
        self.lyrics_input = QTextEdit()
        self.lyrics_input.setPlaceholderText("Paste your lyrics here...")
        splitter.addWidget(self.lyrics_input)

        # Lyrics table
        self.lyrics_table = QTableWidget()
        self.lyrics_table.setColumnCount(2)
        self.lyrics_table.setHorizontalHeaderLabels(["Time", "Text"])
        self.lyrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        splitter.addWidget(self.lyrics_table)

        layout.addWidget(splitter)

        # Current timer display
        self.timer_display = QLabel("00:00.000")
        self.timer_display.setAlignment(Qt.AlignCenter)
        self.timer_display.setFont(QFont("Arial", 20, QFont.Bold))
        layout.addWidget(self.timer_display)

        # Audio file name display
        self.audio_file_label = QLabel("No audio file loaded")
        self.audio_file_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.audio_file_label)

        # Buttons
        button_layout = QHBoxLayout()

        load_lyrics_btn = QPushButton('Load Lyrics')
        load_lyrics_btn.clicked.connect(self.load_lyrics)
        button_layout.addWidget(load_lyrics_btn)

        load_audio_btn = QPushButton('Load Audio')
        load_audio_btn.clicked.connect(self.load_audio)
        button_layout.addWidget(load_audio_btn)

        self.play_pause_btn = QPushButton('Play')
        self.play_pause_btn.clicked.connect(self.play_pause)
        button_layout.addWidget(self.play_pause_btn)

        save_lrc_btn = QPushButton('Save LRC')
        save_lrc_btn.clicked.connect(self.save_lrc)
        button_layout.addWidget(save_lrc_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setGeometry(300, 300, 600, 500)
        self.setWindowTitle('LRC Generator')
        self.show()

        # Timer for updating player time
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(10)  # Update every 10 ms for smoother display

    def load_audio(self):
        file_name, _ = QFileDialog.getOpenFileName(self, 'Open Audio File', '', 'Audio Files (*.mp3 *.wav *.ogg)')
        if file_name:
            self.audio_file = file_name
            self.audio_file_label.setText(f"Loaded: {os.path.basename(file_name)}")
            print(f"Loaded audio file: {file_name}")

    def update_time(self):
        if self.is_playing:
            current_time = self.get_current_time() - self.start_time - self.total_pause_time + self.current_position
            minutes, seconds = divmod(int(current_time / 1000), 60)
            milliseconds = current_time % 1000
            time_string = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            self.timer_display.setText(time_string)
            self.setWindowTitle(f'LRC Generator - {time_string}')

    def load_lyrics(self):
        text = self.lyrics_input.toPlainText()
        if text:
            self.lyrics = [line.strip() for line in text.split('\n') if line.strip()]
            self.update_lyrics_table()
        else:
            print("No lyrics to load. Please paste some lyrics in the text area.")

    def update_lyrics_table(self):
        self.lyrics_table.setRowCount(len(self.lyrics))
        for i, lyric in enumerate(self.lyrics):
            time_item = QTableWidgetItem("")
            self.lyrics_table.setItem(i, 0, time_item)
            text_item = QTableWidgetItem(lyric)
            self.lyrics_table.setItem(i, 1, text_item)
        self.lyrics_table.selectRow(0)
        self.current_line = 0

    def play_pause(self):
        if self.audio_file is None:
            print("No audio loaded. Please load an audio file first.")
            return

        current_time = self.get_current_time()

        if self.is_playing:
            self.stop_audio()
            self.pause_time = current_time
            self.is_playing = False
            self.play_pause_btn.setText('Play')
        else:
            if self.pause_time > 0:
                self.total_pause_time += current_time - self.pause_time

            self.play_audio()
            self.is_playing = True
            self.play_pause_btn.setText('Pause')

    def play_audio(self):
        if self.ffplay_process:
            self.ffplay_process.terminate()

        start_position = self.current_position / 1000  # Convert to seconds

        self.ffplay_process = (
            ffmpeg
            .input(self.audio_file, ss=start_position)
            .output('pipe:', format='s16le', acodec='pcm_s16le', ac=2, ar='44100')
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )

        def audio_playback():
            import pyaudio
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16,
                            channels=2,
                            rate=44100,
                            output=True)

            while self.is_playing:
                raw_data = self.ffplay_process.stdout.read(4096)
                if not raw_data:
                    break
                stream.write(raw_data)

            stream.stop_stream()
            stream.close()
            p.terminate()

        threading.Thread(target=audio_playback, daemon=True).start()
        self.start_time = self.get_current_time()

    def stop_audio(self):
        if self.ffplay_process:
            self.ffplay_process.terminate()
            self.ffplay_process = None
        self.current_position += self.get_current_time() - self.start_time - self.total_pause_time

    def get_current_time(self):
        return int(time.time() * 1000)

    def next_line(self):
        if self.current_line < len(self.lyrics) and self.is_playing:
            current_time = self.get_current_time() - self.start_time - self.total_pause_time
            minutes, seconds = divmod(int(current_time / 1000), 60)
            milliseconds = current_time % 1000
            time_string = f"[{minutes:02d}:{seconds:02d}.{milliseconds:03d}]"
            
            self.lyrics_table.item(self.current_line, 0).setText(time_string)
            self.current_line += 1
            if self.current_line < len(self.lyrics):
                self.lyrics_table.selectRow(self.current_line)

    def save_lrc(self):
        file_name, _ = QFileDialog.getSaveFileName(self, 'Save LRC File', '', 'LRC Files (*.lrc)')
        if file_name:
            with open(file_name, 'w', encoding='utf-8') as f:
                for row in range(self.lyrics_table.rowCount()):
                    time = self.lyrics_table.item(row, 0).text()
                    text = self.lyrics_table.item(row, 1).text()
                    if time:
                        f.write(f"{time}{text}\n")
            print(f"LRC file saved: {file_name}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.next_line()

    def closeEvent(self, event):
        if self.ffplay_process:
            self.ffplay_process.terminate()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LRCGenerator()
    sys.exit(app.exec_())