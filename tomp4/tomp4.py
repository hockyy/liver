import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import tempfile
import json
from pathlib import Path
import pygame
import shutil
import sys

class FFmpegConverter(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Initialize pygame mixer for audio preview
        pygame.mixer.init()
        
        self.title("MKV to MP4 Converter")
        self.geometry("800x600")
        self.configure(padx=20, pady=20)
        
        self.selected_file = None
        self.audio_tracks = []
        self.temp_audio_files = []
        self.currently_playing = None
        
        # Find ffmpeg executable
        self.ffmpeg_path = self.find_ffmpeg()
        self.ffprobe_path = self.find_ffprobe()
        
        if not self.ffmpeg_path or not self.ffprobe_path:
            messagebox.showerror(
                "Error", 
                "Could not find ffmpeg or ffprobe in your system PATH. "
                "Please make sure ffmpeg is installed correctly."
            )
        
        self.create_widgets()
        
    def find_ffmpeg(self):
        """Find the ffmpeg executable in the system PATH."""
        ffmpeg_cmd = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        ffmpeg_path = shutil.which(ffmpeg_cmd)
        
        if ffmpeg_path:
            self.status_var = tk.StringVar()
            self.status_var.set(f"Found ffmpeg at: {ffmpeg_path}")
            return ffmpeg_path
        return None
        
    def find_ffprobe(self):
        """Find the ffprobe executable in the system PATH."""
        ffprobe_cmd = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
        ffprobe_path = shutil.which(ffprobe_cmd)
        
        if ffprobe_path:
            return ffprobe_path
        return None
        
    def create_widgets(self):
        # File selection frame
        file_frame = ttk.LabelFrame(self, text="File Selection")
        file_frame.pack(fill="x", padx=5, pady=5)
        
        self.file_path_var = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, width=70)
        file_entry.pack(side=tk.LEFT, padx=5, pady=5, fill="x", expand=True)
        
        browse_button = ttk.Button(file_frame, text="Browse", command=self.browse_file)
        browse_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Conversion options frame
        options_frame = ttk.LabelFrame(self, text="Conversion Options")
        options_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Convert to MP4 button
        convert_button = ttk.Button(options_frame, text="Convert to MP4", command=self.convert_to_mp4)
        convert_button.pack(anchor="w", padx=5, pady=5)
        
        # Audio tracks section
        audio_label = ttk.Label(options_frame, text="Audio Tracks:")
        audio_label.pack(anchor="w", padx=5, pady=5)
        
        # Frame for audio tracks list
        self.audio_list_frame = ttk.Frame(options_frame)
        self.audio_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Scrollable frame for audio tracks
        self.audio_canvas = tk.Canvas(self.audio_list_frame)
        scrollbar = ttk.Scrollbar(self.audio_list_frame, orient="vertical", command=self.audio_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.audio_canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.audio_canvas.configure(scrollregion=self.audio_canvas.bbox("all"))
        )
        
        self.audio_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.audio_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.audio_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Status bar (must initialize if not already)
        if not hasattr(self, 'status_var'):
            self.status_var = tk.StringVar()
            self.status_var.set("Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self, orient="horizontal", length=100, mode="determinate", variable=self.progress_var)
        self.progress.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        # FFmpeg status indicator
        ffmpeg_status = "FFmpeg: Found ✓" if self.ffmpeg_path else "FFmpeg: Not found ✗"
        ffmpeg_status_label = ttk.Label(self, text=ffmpeg_status)
        ffmpeg_status_label.pack(side=tk.BOTTOM, anchor="e", padx=5)
        
    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("MKV files", "*.mkv")])
        if file_path:
            self.file_path_var.set(file_path)
            self.selected_file = file_path
            self.get_audio_tracks()
    
    def get_audio_tracks(self):
        if not self.selected_file:
            return
            
        if not self.ffprobe_path:
            messagebox.showerror("Error", "FFprobe not found. Cannot analyze audio tracks.")
            return
        
        # Clear existing audio tracks
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.audio_tracks = []
        self.temp_audio_files = []
        
        # Get audio track information using ffprobe
        try:
            self.status_var.set("Analyzing audio tracks...")
            
            # Use absolute file path
            file_path = os.path.abspath(self.selected_file)
            
            cmd = [
                self.ffprobe_path, 
                '-v', 'quiet', 
                '-print_format', 'json', 
                '-show_streams', 
                '-select_streams', 'a', 
                file_path
            ]
            
            # Debug output
            print(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                error_msg = f"Error analyzing file: {result.stderr}"
                print(error_msg)
                raise Exception(error_msg)
            
            data = json.loads(result.stdout)
            for i, stream in enumerate(data.get('streams', [])):
                track_info = {
                    'index': stream.get('index'),
                    'codec_name': stream.get('codec_name', 'Unknown'),
                    'language': stream.get('tags', {}).get('language', 'Unknown'),
                    'title': stream.get('tags', {}).get('title', f'Track {i+1}')
                }
                self.audio_tracks.append(track_info)
                
                # Create row for each audio track
                track_frame = ttk.Frame(self.scrollable_frame)
                track_frame.pack(fill="x", pady=2)
                
                # Checkbox for extraction
                var = tk.BooleanVar(value=True)
                check = ttk.Checkbutton(track_frame, variable=var)
                check.pack(side=tk.LEFT)
                track_info['extract_var'] = var
                
                # Track info label
                label_text = f"{track_info['title']} ({track_info['language']}) - {track_info['codec_name']}"
                label = ttk.Label(track_frame, text=label_text, width=50)
                label.pack(side=tk.LEFT, padx=5)
                
                # Preview button
                preview_btn = ttk.Button(
                    track_frame, 
                    text="Preview", 
                    command=lambda t=track_info: self.preview_audio_track(t)
                )
                preview_btn.pack(side=tk.LEFT, padx=5)
                
            # Add Extract All button if there are audio tracks
            if self.audio_tracks:
                extract_all_btn = ttk.Button(
                    self.scrollable_frame,
                    text="Extract Selected Audio Tracks",
                    command=self.extract_selected_audio
                )
                extract_all_btn.pack(pady=10)
                
            self.status_var.set(f"Found {len(self.audio_tracks)} audio tracks")
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)
            self.status_var.set("Error analyzing audio tracks")
    
    def convert_to_mp4(self):
        if not self.ffmpeg_path:
            messagebox.showerror("Error", "FFmpeg not found. Cannot convert file.")
            return
            
        if not self.selected_file:
            messagebox.showinfo("Error", "Please select an MKV file first")
            return
            
        output_file = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4")],
            initialfile=Path(self.selected_file).stem + ".mp4"
        )
        
        if not output_file:
            return
            
        def conversion_thread():
            try:
                self.status_var.set("Converting...")
                self.progress_var.set(0)
                
                # Use absolute paths
                input_file = os.path.abspath(self.selected_file)
                output_file_abs = os.path.abspath(output_file)
                
                cmd = [
                    self.ffmpeg_path,
                    '-i', input_file,
                    '-c', 'copy',
                    output_file_abs
                ]
                
                # Debug output
                print(f"Running conversion command: {' '.join(cmd)}")
                
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                
                # Get duration of the video
                duration_cmd = [
                    self.ffprobe_path, 
                    '-v', 'error', 
                    '-show_entries', 'format=duration', 
                    '-of', 'default=noprint_wrappers=1:nokey=1', 
                    input_file
                ]
                
                # Debug output
                print(f"Running duration command: {' '.join(duration_cmd)}")
                
                duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
                
                if duration_result.returncode != 0:
                    print(f"Duration error: {duration_result.stderr}")
                    total_duration = 100  # Default value if we can't get the duration
                else:
                    try:
                        total_duration = float(duration_result.stdout.strip())
                    except (ValueError, IndexError):
                        print(f"Couldn't parse duration: {duration_result.stdout}")
                        total_duration = 100
                
                # Monitor conversion progress
                for line in process.stdout:
                    print(line.strip())  # Debug output
                    if "time=" in line:
                        try:
                            time_str = line.split("time=")[1].split()[0]
                            h, m, s = map(float, time_str.split(':'))
                            current_time = h * 3600 + m * 60 + s
                            progress = (current_time / total_duration) * 100
                            self.progress_var.set(progress)
                        except Exception as e:
                            print(f"Progress parsing error: {e}")
                
                process.wait()
                if process.returncode == 0:
                    self.status_var.set("Conversion completed successfully")
                    self.progress_var.set(100)
                    messagebox.showinfo("Success", "MKV to MP4 conversion completed successfully!")
                else:
                    self.status_var.set("Conversion failed")
                    messagebox.showerror("Error", "Failed to convert file. Check console for details.")
            except Exception as e:
                error_msg = f"Conversion error: {str(e)}"
                print(error_msg)
                self.status_var.set("Conversion error")
                messagebox.showerror("Error", error_msg)
        
        # Start conversion in a separate thread
        thread = threading.Thread(target=conversion_thread)
        thread.daemon = True
        thread.start()
    
    def extract_selected_audio(self):
        if not self.ffmpeg_path:
            messagebox.showerror("Error", "FFmpeg not found. Cannot extract audio.")
            return
            
        if not self.selected_file or not self.audio_tracks:
            messagebox.showinfo("Error", "No audio tracks available")
            return
        
        output_dir = filedialog.askdirectory(title="Select folder to save MP3 files")
        if not output_dir:
            return
        
        def extraction_thread():
            try:
                self.status_var.set("Extracting audio tracks...")
                self.progress_var.set(0)
                
                # Use absolute paths
                input_file = os.path.abspath(self.selected_file)
                output_dir_abs = os.path.abspath(output_dir)
                
                selected_tracks = [track for track in self.audio_tracks if track['extract_var'].get()]
                total_tracks = len(selected_tracks)
                
                for i, track in enumerate(selected_tracks):
                    # Create output filename
                    base_name = Path(self.selected_file).stem
                    track_name = track['title'].replace(' ', '_')
                    language = track['language']
                    
                    # Remove any invalid characters from filename
                    for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
                        track_name = track_name.replace(char, '_')
                    
                    output_file = os.path.join(
                        output_dir_abs, 
                        f"{base_name}_{track_name}_{language}.mp3"
                    )
                    
                    # Extract audio track
                    cmd = [
                        self.ffmpeg_path,
                        '-i', input_file,
                        '-map', f"0:{track['index']}",
                        '-c:a', 'libmp3lame',
                        '-q:a', '2',
                        output_file
                    ]
                    
                    # Debug output
                    print(f"Running extraction command: {' '.join(cmd)}")
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        print(f"Extraction error: {result.stderr}")
                        raise Exception(f"Failed to extract track {track['title']}: {result.stderr}")
                    
                    # Update progress
                    progress = ((i + 1) / total_tracks) * 100
                    self.progress_var.set(progress)
                
                self.status_var.set("Audio extraction completed")
                self.progress_var.set(100)
                messagebox.showinfo("Success", "Audio tracks extracted successfully!")
            except Exception as e:
                error_msg = f"Extraction error: {str(e)}"
                print(error_msg)
                self.status_var.set("Extraction error")
                messagebox.showerror("Error", error_msg)
        
        # Start extraction in a separate thread
        thread = threading.Thread(target=extraction_thread)
        thread.daemon = True
        thread.start()
    
    def preview_audio_track(self, track_info):
        if not self.ffmpeg_path:
            messagebox.showerror("Error", "FFmpeg not found. Cannot preview audio.")
            return
            
        if self.currently_playing:
            # Stop current preview
            pygame.mixer.music.stop()
            self.currently_playing = None
            self.status_var.set("Audio preview stopped")
            return
        
        try:
            self.status_var.set(f"Preparing audio preview for {track_info['title']}...")
            
            # Create temporary file for the audio sample
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_file.close()
            
            # Use absolute paths
            input_file = os.path.abspath(self.selected_file)
            temp_file_path = os.path.abspath(temp_file.name)
            
            # Extract a 10-second sample starting at 30 seconds (or beginning if shorter)
            cmd = [
                self.ffmpeg_path,
                '-i', input_file,
                '-map', f"0:{track_info['index']}",
                '-ss', '30',  # Start at 30 seconds
                '-t', '10',   # Get 10 seconds
                '-c:a', 'libmp3lame',
                '-q:a', '2',
                temp_file_path
            ]
            
            # Debug output
            print(f"Running preview command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Preview extraction error: {result.stderr}")
                raise Exception(f"Failed to extract audio preview: {result.stderr}")
            
            # Play the audio sample
            pygame.mixer.music.load(temp_file_path)
            pygame.mixer.music.play()
            
            self.currently_playing = track_info
            self.temp_audio_files.append(temp_file_path)
            self.status_var.set(f"Playing preview: {track_info['title']}")
            
            # Set a callback to update status when playback finishes
            def check_playback():
                if not pygame.mixer.music.get_busy() and self.currently_playing:
                    self.currently_playing = None
                    self.status_var.set("Ready")
                else:
                    self.after(1000, check_playback)
            
            check_playback()
            
        except Exception as e:
            error_msg = f"Failed to preview audio: {str(e)}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)
            self.status_var.set("Audio preview error")
    
    def __del__(self):
        # Clean up temporary files
        for temp_file in self.temp_audio_files:
            try:
                os.unlink(temp_file)
            except:
                pass

if __name__ == "__main__":
    app = FFmpegConverter()
    app.mainloop()