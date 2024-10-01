import logging
import os
import threading
import subprocess
import re
from datetime import timedelta
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import customtkinter as ctk
import codecs
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Regular expression to match subtitle lines
SUBTITLE_REGEX = re.compile(r'^\[(\d+):(\d{2}\.\d{3}) --> (\d+):(\d{2}\.\d{3})\] (.+)$')


def clean_srt(file_path):
    try:
        with codecs.open(file_path, 'r', encoding='utf-8-sig') as file:
            content = file.read()
    except UnicodeDecodeError:
        with codecs.open(file_path, 'r', encoding='iso-8859-1') as file:
            content = file.read()

    # Remove BOM if present
    content = content.lstrip('\ufeff')

    # Remove non-printable characters except newlines and CJK characters
    content = re.sub(r'[^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uff00-\uffef\u1100-\u11ff\u3130-\u318f\ua960-\ua97f\uac00-\ud7af\u4e00-\u9fff\x20-\x7E\n]', '', content)

    # Fix common encoding issues
    content = content.replace('â€™', "'")
    content = content.replace('â€"', "–")
    content = content.replace('â€œ', '"')
    content = content.replace('â€', '"')

    with codecs.open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

    print(f"Cleaned SRT file has been saved as {file_path}")

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
            '--best_of', "10",
            '--verbose', 'true',
            '--vad_filter', 'true',
            '--vad_alt_method', 'silero_v4',
            '--standard_asia',
        ]

        # Add language parameter only if the model is not cantonese
        if self.model != "cantonese":
            command.extend(['--language', lang])

        log_callback(f"Starting transcription for {audio_file}\n")
        log_callback(f"Command: {' '.join(command)}\n")

        if os.path.exists(cjk_srt_file):
            log_callback(f"Transcription exist, file saved at {cjk_srt_file}\n")
            return

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

        if os.path.exists(cjk_srt_file):
            log_callback(f"Transcription completed. SRT file saved at {cjk_srt_file}\n")
            try:
                clean_srt(cjk_srt_file)
                log_callback(f"Cleaned {cjk_srt_file}\n")
                os.remove(cjk_tmp_srt_file)
                log_callback(f"Removed {cjk_tmp_srt_file}\n")
            except:
                pass
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

class TranscriptionApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Subtitle Transcriber")
        self.geometry("800x800")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(8, weight=1)

        self.create_widgets()
        self.transcriber = SubtitleTranscriber()
        self.queue = []
        self.is_processing = False

    def create_widgets(self):
        # Model selection
        self.model_var = tk.StringVar(value='large-v3')
        model_frame = ctk.CTkFrame(self)
        model_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(model_frame, text="Model:").pack(side="left", padx=5)
        models = ['large-v3', 'large-v3-turbo', 'cantonese']
        model_menu = ctk.CTkOptionMenu(model_frame, variable=self.model_var, values=models, command=self.update_language_menu)
        model_menu.pack(side="left", padx=5)

        # Language selection
        self.filename_var = tk.StringVar(value='')
        self.language_var = tk.StringVar(value='yue')
        self.language_frame = ctk.CTkFrame(self)
        self.language_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.language_label = ctk.CTkLabel(self.language_frame, text="Source Language:")
        self.language_label.pack(side="left", padx=5)
        self.languages = ['en', 'ja', 'zh', 'yue']
        self.language_menu = ctk.CTkOptionMenu(self.language_frame, variable=self.language_var, values=self.languages)
        self.language_menu.pack(side="left", padx=5)

        # Beam size
        self.beam_size_var = tk.StringVar(value='10')
        beam_frame = ctk.CTkFrame(self)
        beam_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(beam_frame, text="Beam Size:").pack(side="left", padx=5)
        beam_entry = ctk.CTkEntry(beam_frame, textvariable=self.beam_size_var)
        beam_entry.pack(side="left", padx=5)

        # File selection
        file_frame = ctk.CTkFrame(self)
        file_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(file_frame, text="Files in Queue:").pack(side="left", padx=5)
        self.queue_listbox = tk.Listbox(file_frame, width=50, height=5)
        self.queue_listbox.pack(side="left", padx=5, expand=True, fill="both")
        file_scrollbar = ttk.Scrollbar(file_frame, orient="vertical", command=self.queue_listbox.yview)
        file_scrollbar.pack(side="left", fill="y")
        self.queue_listbox.config(yscrollcommand=file_scrollbar.set)
        browse_button = ctk.CTkButton(file_frame, text="Add Files", command=self.browse_and_add_files)
        browse_button.pack(side="left", padx=5)
        remove_button = ctk.CTkButton(file_frame, text="Remove Selected", command=self.remove_selected_files)
        remove_button.pack(side="left", padx=5)
        # Control buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
        start_button = ctk.CTkButton(button_frame, text="Start Processing", command=self.start_processing)
        start_button.pack(side="left", padx=5, expand=True, fill="x")

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=5, column=0, padx=10, pady=10, sticky="ew")

        # Queue list
        self.queue_frame = ctk.CTkFrame(self)
        self.queue_frame.grid(row=6, column=0, padx=10, pady=10, sticky="nsew")
        self.queue_frame.grid_columnconfigure(0, weight=1)
        self.queue_frame.grid_rowconfigure(0, weight=1)

        self.queue_list = tk.Listbox(self.queue_frame, selectmode=tk.SINGLE)
        self.queue_list.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        queue_scrollbar = ttk.Scrollbar(self.queue_frame, orient="vertical", command=self.queue_list.yview)
        queue_scrollbar.grid(row=0, column=1, sticky="ns")
        self.queue_list.configure(yscrollcommand=queue_scrollbar.set)

        # Log text area
        self.log_text = scrolledtext.ScrolledText(self, wrap='word', width=70, height=15)
        self.log_text.grid(row=7, column=0, padx=10, pady=10, sticky="nsew")

    def update_language_menu(self, *args):
        if self.model_var.get() == 'cantonese':
            self.language_label.pack_forget()
            self.language_menu.pack_forget()
        else:
            self.language_label.pack(side="left", padx=5)
            self.language_menu.pack(side="left", padx=5)

    def browse_and_add_files(self):
        initial_dir = os.path.expanduser("~")
        filenames = filedialog.askopenfilenames(filetypes=[("Audio/Video Files", "*.mkv *.mp4 *.wav *.mp3 *.aac *.opus")], initialdir=initial_dir)
        for filename in filenames:
            if filename not in self.queue:
                self.queue.append(filename)
                self.queue_listbox.insert(tk.END, filename)
                self.log_callback(f"Added to queue: {filename}\n")
                
    def remove_selected_files(self):
        selected_indices = self.queue_listbox.curselection()
        for index in reversed(selected_indices):
            if 0 <= index < len(self.queue):
                file_path = self.queue_listbox.get(index)
                del self.queue[index]  # Use del instead of remove to ensure we remove the correct index
                self.queue_listbox.delete(index)
                self.log_callback(f"Removed from queue: {file_path}\n")
            else:
                self.log_callback(f"Invalid index {index}, skipping removal.\n")
        
        # Ensure queue and listbox are in sync
        if len(self.queue) != self.queue_listbox.size():
            self.log_callback("Warning: Queue and listbox are out of sync. Resetting both.\n")
            self.queue.clear()
            self.queue_listbox.delete(0, tk.END)

    def start_processing(self):
        if self.is_processing:
            self.log_callback("Transcription is already in progress.\n")
            return
        if not self.queue:
            self.log_callback("No files to process. Please select a file or add files to the queue.\n")
            return
        self.is_processing = True
        self.process_next_in_queue()

    def process_next_in_queue(self):
        if not self.queue:
            self.is_processing = False
            self.log_callback("All transcriptions completed.\n")
            return

        file_path = self.queue[0]  # Get the first file, but don't remove it yet
        self.filename_var.set(file_path)
        self.log_callback(f"Processing: {file_path}\n")
        
        self.transcriber.model = self.model_var.get()
        lang = self.language_var.get() if self.model_var.get() != 'cantonese' else ''
        self.transcriber.start_transcription(file_path, self.log_callback, lang, self.beam_size_var.get())
        self.after(100, self.check_transcription_status)

    def check_transcription_status(self):
        if self.transcriber.thread and self.transcriber.thread.is_alive():
            self.after(100, self.check_transcription_status)
        else:
            if self.queue:  # Check if there's still an item in the queue
                processed_file = self.queue.pop(0)  # Remove the processed file
                self.queue_listbox.delete(0)  # Remove the first item from the listbox
                self.log_callback(f"Finished processing: {processed_file}\n")
                self.process_next_in_queue()
            else:
                self.log_callback("No more files to process.\n")
                self.is_processing = False

    def stop_processing(self):
        self.transcriber.stop_transcription()
        self.is_processing = False
        self.queue.clear()
        self.queue_list.delete(0, tk.END)
        self.log_callback("Transcription stopped. Queue processing interrupted.\n")

    def log_callback(self, message):
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        self.update_idletasks()

if __name__ == "__main__":
    app = TranscriptionApp()
    app.mainloop()