import logging
import os
import threading
import subprocess
import re
from datetime import timedelta
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import customtkinter as ctk
from googletrans import Translator
import logging
from httpx import Timeout
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress googletrans debug messages
logging.getLogger("googletrans").setLevel(logging.ERROR)

# Optionally, suppress httpx debug messages as well
logging.getLogger("httpx").setLevel(logging.WARNING)

# Regular expression to match subtitle lines
SUBTITLE_REGEX = re.compile(r'^\[(\d+):(\d{2}\.\d{3}) --> (\d+):(\d{2}\.\d{3})\] (.+)$')

def format_timestamp(seconds):
    delta = timedelta(seconds=seconds)
    hours, remainder = divmod(delta.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{milliseconds:03}"

def format_timestamp_from_match(minutes, sec_mili):
    total_seconds = float(minutes) * 60 + float(sec_mili)
    secint = int(total_seconds)
    milliseconds = int((total_seconds - secint) * 1000)
    hours, minutes = divmod(secint, 3600)
    minutes, seconds = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

class SubtitleTranscriber:
    def __init__(self, model="large-v3", device="CUDA"):
        self.model = model
        self.device = device
        self.stop_flag = threading.Event()
        self.thread = None
        self.translator = Translator(timeout=Timeout(10.0))  # Add a timeout
        self.translation_thread = None

    def transcribe_and_write_srt_live(self, audio_file, log_callback, lang, beam_size):
        output_dir = os.path.dirname(audio_file)
        base_name = os.path.splitext(os.path.basename(audio_file))[0]
        cjk_srt_file = os.path.join(output_dir, f"{base_name}.srt")
        cjk_tmp_srt_file = f"{output_dir}/{base_name}.{lang}.tmp.srt"

        if os.path.exists(cjk_srt_file):
            log_callback(f"Transcription completed. SRT file saved at {cjk_srt_file}\n")
            return

        command = [
            'Faster-Whisper-XXL.exe', audio_file,
            '--model', self.model,
            '--device', self.device,
            '--output_dir', output_dir,
            '--output_format', 'srt',
            '--task', 'transcribe',
            '--beam_size', str(beam_size),
            '--language', lang,
            '--verbose', 'true',
            '--vad_filter', 'true',
            '--vad_alt_method', 'silero_v4',
            '--standard_asia',
        ]

        log_callback(f"Starting transcription for {audio_file}\n")
        log_callback(f"Command: {' '.join(command)}\n")

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        except Exception as e:
            log_callback(f"Error starting transcription: {str(e)}\n")
            return

        with open(cjk_tmp_srt_file, 'w', encoding='utf-8') as cjk_f:
            segment_index = 1
            for line in process.stdout:
                if self.stop_flag.is_set():
                    process.terminate()
                    log_callback("Transcription stopped.\n")
                    return

                if '-->' in line:
                    log_callback(line)
                    match = SUBTITLE_REGEX.match(line)
                    if match:
                        hours_start, minutes_seconds_start, hours_end, minutes_seconds_end, text = match.groups()
                        start_time = format_timestamp_from_match(hours_start, minutes_seconds_start)
                        end_time = format_timestamp_from_match(hours_end, minutes_seconds_end)
                        log_callback(f"{start_time} --> {end_time}\n")
                        cjk_f.write(f"{segment_index}\n{start_time} --> {end_time}\n{text.strip()}\n\n")
                        cjk_f.flush()
                        segment_index += 1

        process.stdout.close()
        process.wait()

        os.remove(cjk_tmp_srt_file)

        if os.path.exists(cjk_srt_file):
            log_callback(f"Transcription completed. SRT file saved at {cjk_srt_file}\n")
        else:
            log_callback("Transcription failed or was stopped before completion.\n")

    def start_transcription(self, audio_file, log_callback, lang, beam_size):
        if self.thread and self.thread.is_alive():
            log_callback("Transcription is already running.\n")
            return

        self.stop_flag.clear()
        self.thread = threading.Thread(target=self.transcribe_and_write_srt_live, args=(audio_file, log_callback, lang, beam_size))
        self.thread.start()

    def stop_transcription(self):
        if self.thread and self.thread.is_alive():
            self.stop_flag.set()
            self.thread.join()
        else:
            logger.info("No transcription process is running.")

    def translate_srt(self, srt_file, target_lang, log_callback):
        if not os.path.exists(srt_file):
            log_callback(f"SRT file not found: {srt_file}\n")
            return

        output_file = srt_file.replace('.srt', f'.{target_lang}.srt')
        
        with open(srt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        translated_lines = []
        i = 0
        while i < len(lines):
            if lines[i].strip().isdigit():  # Subtitle number
                translated_lines.extend(lines[i:i+2])  # Keep number and timestamp
                i += 2
                text_lines = []
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1
                text = ' '.join(text_lines)
                translated_text = self.translator.translate(text, dest=target_lang).text
                translated_lines.append(f"{translated_text}\n\n")
            else:
                translated_lines.append(lines[i])
                i += 1

        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(translated_lines)

        log_callback(f"Translation completed. Translated SRT file saved at {output_file}\n")

    def start_translation(self, srt_file, target_lang, log_callback):
        if self.translation_thread and self.translation_thread.is_alive():
            log_callback("Translation is already running.\n")
            return

        self.translation_thread = threading.Thread(target=self.translate_srt, args=(srt_file, target_lang, log_callback))
        self.translation_thread.start()

class TranscriptionApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Subtitle Transcriber and Translator")
        self.geometry("600x700")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)

        self.create_widgets()
        self.transcriber = SubtitleTranscriber()

    def create_widgets(self):
        # Language selection
        self.language_var = tk.StringVar(value='yue')
        language_frame = ctk.CTkFrame(self)
        language_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(language_frame, text="Source Language:").pack(side="left", padx=5)
        languages = ['ja', 'zh', 'yue']
        language_menu = ctk.CTkOptionMenu(language_frame, variable=self.language_var, values=languages)
        language_menu.pack(side="left", padx=5)

        # Target language selection
        self.target_language_var = tk.StringVar(value='en')
        target_language_frame = ctk.CTkFrame(self)
        target_language_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(target_language_frame, text="Target Language:").pack(side="left", padx=5)
        target_languages = ['en', 'ja', 'zh-cn', 'yue']
        target_language_menu = ctk.CTkOptionMenu(target_language_frame, variable=self.target_language_var, values=target_languages)
        target_language_menu.pack(side="left", padx=5)

        # Beam size
        self.beam_size_var = tk.StringVar(value='3')
        beam_frame = ctk.CTkFrame(self)
        beam_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(beam_frame, text="Beam Size:").pack(side="left", padx=5)
        beam_entry = ctk.CTkEntry(beam_frame, textvariable=self.beam_size_var)
        beam_entry.pack(side="left", padx=5)

        # File selection
        self.filename_var = tk.StringVar()
        file_frame = ctk.CTkFrame(self)
        file_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(file_frame, text="File:").pack(side="left", padx=5)
        file_entry = ctk.CTkEntry(file_frame, textvariable=self.filename_var, width=300)
        file_entry.pack(side="left", padx=5, expand=True, fill="x")
        browse_button = ctk.CTkButton(file_frame, text="Browse", command=self.browse_file)
        browse_button.pack(side="left", padx=5)

        # Control buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
        start_button = ctk.CTkButton(button_frame, text="Start Transcription", command=self.start_transcription)
        start_button.pack(side="left", padx=5, expand=True, fill="x")
        stop_button = ctk.CTkButton(button_frame, text="Stop Transcription", command=self.stop_transcription)
        stop_button.pack(side="left", padx=5, expand=True, fill="x")
        translate_button = ctk.CTkButton(button_frame, text="Translate", command=self.translate_srt)
        translate_button.pack(side="left", padx=5, expand=True, fill="x")

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=5, column=0, padx=10, pady=10, sticky="ew")

        # Log text area
        self.log_text = scrolledtext.ScrolledText(self, wrap='word', width=70, height=20)
        self.log_text.grid(row=6, column=0, padx=10, pady=10, sticky="nsew")

    def browse_file(self):
        initial_dir = os.path.dirname(self.filename_var.get()) if self.filename_var.get() else os.path.expanduser("~")
        filename = filedialog.askopenfilename(filetypes=[("Audio/Video Files", "*.mp4 *.wav *.mp3 *.srt")], initialdir=initial_dir)
        if filename:
            self.filename_var.set(filename)

    def start_transcription(self):
        audio_file = self.filename_var.get()
        if not audio_file:
            messagebox.showerror("Error", "Please select a file.")
            return
        self.log_text.delete(1.0, tk.END)
        self.transcriber.start_transcription(audio_file, self.log_callback, self.language_var.get(), self.beam_size_var.get())

    def stop_transcription(self):
        self.transcriber.stop_transcription()

    def translate_srt(self):
        srt_file = self.filename_var.get().replace('.mp4', '.srt').replace('.wav', '.srt').replace('.mp3', '.srt')
        if not os.path.exists(srt_file):
            messagebox.showerror("Error", "SRT file not found. Please transcribe first.")
            return
        self.transcriber.start_translation(srt_file, self.target_language_var.get(), self.log_callback)

    def log_callback(self, message):
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        self.update_idletasks()

if __name__ == "__main__":
    app = TranscriptionApp()
    app.mainloop()