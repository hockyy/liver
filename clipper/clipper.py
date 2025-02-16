import os
import re
import time
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

def time_str_to_seconds(timestr):
    """
    Convert a time string in the format 'HH:MM:SS,mmm' to seconds (float).
    """
    try:
        parts = timestr.split(':')
        hours = int(parts[0].strip())
        minutes = int(parts[1].strip())
        sec, milli = parts[2].strip().split(',')
        seconds = int(sec)
        milliseconds = int(milli)
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
    except Exception:
        return None

class ClipApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stream Clip Editor")
        self.geometry("800x600")
        self.selected_file = None

        # --- File Selection ---
        self.file_frame = tk.Frame(self)
        self.file_frame.pack(pady=5, padx=10, anchor="w")
        tk.Label(self.file_frame, text="Selected file:").grid(row=0, column=0, sticky="w")
        self.file_label = tk.Label(self.file_frame, text="No video selected", fg="blue")
        self.file_label.grid(row=0, column=1, sticky="w", padx=5)
        self.browse_button = tk.Button(self.file_frame, text="Browse Video", command=self.browse_file)
        self.browse_button.grid(row=0, column=2, padx=5)

        # --- Video Info ---
        self.video_info_label = tk.Label(self, text="Video Info (from ffmpeg):")
        self.video_info_label.pack(pady=(10, 0), anchor="w", padx=10)
        self.video_info_text = scrolledtext.ScrolledText(self, height=10, wrap=tk.WORD)
        self.video_info_text.pack(fill=tk.BOTH, padx=10, pady=5)
        self.video_info_text.config(state=tk.DISABLED)

        # --- Timestamp Input ---
        self.timestamp_frame = tk.Frame(self)
        self.timestamp_frame.pack(pady=5, padx=10, fill=tk.X)
        tk.Label(self.timestamp_frame, text="Enter clip timestamps (one per line):").pack(anchor="w")
        tk.Label(self.timestamp_frame, text="Format: HH:MM:SS[,mmm] --> HH:MM:SS[,mmm]", fg="gray").pack(anchor="w")
        self.timestamp_text = scrolledtext.ScrolledText(self.timestamp_frame, height=10, wrap=tk.WORD)
        self.timestamp_text.pack(fill=tk.BOTH, pady=5)
        self.timestamp_text.bind("<KeyRelease>", self.update_clip_count)

        # --- Clip Count Display ---
        self.clip_count_label = tk.Label(self, text="Clips to be produced: 0")
        self.clip_count_label.pack(pady=5, padx=10, anchor="w")

        # --- Start Button ---
        self.start_button = tk.Button(self, text="Start Clipping", command=self.start_clipping)
        self.start_button.pack(pady=10)

        # --- Log Area ---
        self.log_label = tk.Label(self, text="Log:")
        self.log_label.pack(pady=(10, 0), padx=10, anchor="w")
        self.log_text = scrolledtext.ScrolledText(self, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, padx=10, pady=5)
        self.log_text.config(state=tk.DISABLED)

        # --- Regular Expression to Validate Timestamps ---
        # This regex matches HH:MM:SS with an optional ,mmm, followed by " --> " and then a similar pattern.
        self.timestamp_pattern = re.compile(
            r'(\d{2}):(\d{2}):(\d{2})(?:,(\d{3}))?\s*-->\s*'
            r'(\d{2}):(\d{2}):(\d{2})(?:,(\d{3}))?\s*'
        )

    def browse_file(self):
        filetypes = [
            ("Video files", "*.mp4 *.mkv *.ts"),
            ("All files", "*.*")
        ]
        filename = filedialog.askopenfilename(title="Select Video File", filetypes=filetypes)
        if filename:
            self.selected_file = filename
            self.file_label.config(text=filename)
            self.display_video_info(filename)

    def display_video_info(self, filename):
        """
        Runs ffmpeg to show the input video info.
        Note: ffmpeg writes its info to stderr.
        """
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-i", filename],
                capture_output=True, text=True
            )
            info = result.stderr  # ffmpeg writes info to stderr
            self.video_info_text.config(state=tk.NORMAL)
            self.video_info_text.delete("1.0", tk.END)
            self.video_info_text.insert(tk.END, info)
            self.video_info_text.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to retrieve video info:\n{str(e)}")

    def update_clip_count(self, event=None):
        """
        Update the display that shows how many valid clip lines exist.
        """
        content = self.timestamp_text.get("1.0", tk.END)
        lines = content.strip().splitlines()
        valid_lines = [
            line for line in lines
            if line.strip() and self.timestamp_pattern.match(line.strip())
        ]
        count = len(valid_lines)
        self.clip_count_label.config(text=f"Clips to be produced: {count}")

    def start_clipping(self):
        if not self.selected_file:
            messagebox.showerror("Error", "No video file selected!")
            return

        content = self.timestamp_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showerror("Error", "No timestamp data provided!")
            return

        lines = content.splitlines()
        timestamps = []  # List of tuples (start_time, end_time, duration)
        for line in lines:
            line = line.strip()
            if not line:
                continue
            print(line)
            match = self.timestamp_pattern.match(line)
            if not match:
                messagebox.showerror("Error", f"Invalid timestamp format:\n{line}")
                return

            # Extract start timestamp parts, using "000" as default ms if not provided
            start_hours = match.group(1)
            start_minutes = match.group(2)
            start_seconds = match.group(3)
            start_millis = match.group(4) if match.group(4) is not None else "000"
            start_str = f"{start_hours}:{start_minutes}:{start_seconds},{start_millis}"

            # Extract end timestamp parts, using "000" as default ms if not provided
            end_hours = match.group(5)
            end_minutes = match.group(6)
            end_seconds = match.group(7)
            end_millis = match.group(8) if match.group(8) is not None else "000"
            end_str = f"{end_hours}:{end_minutes}:{end_seconds},{end_millis}"

            start_secs = time_str_to_seconds(start_str)
            end_secs = time_str_to_seconds(end_str)
            if start_secs is None or end_secs is None or start_secs >= end_secs:
                messagebox.showerror("Error", f"Invalid time range in line:\n{line}")
                return
            duration = end_secs - start_secs
            timestamps.append((start_str, end_str, duration))

        if not timestamps:
            messagebox.showerror("Error", "No valid timestamp lines found!")
            return

        # Create an output directory. For an input file like "my_recording.mp4",
        # the output folder will be: {input_dir}/{video-title}-{epoch}/
        input_dir = os.path.dirname(self.selected_file)
        base_name = os.path.splitext(os.path.basename(self.selected_file))[0]
        current_epoch = int(time.time())
        output_dir = os.path.join(input_dir, f"{base_name}-{current_epoch}")
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create output directory:\n{str(e)}")
            return

        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.insert(tk.END, f"Starting clipping process...\n\n")
        clip_index = 1
        for start_str, end_str, duration in timestamps:
            # ffmpeg expects time with a period as the decimal separator.
            start_ffmpeg = start_str.replace(",", ".")
            duration_str = f"{duration:.3f}"
            output_filename = os.path.join(output_dir, f"clip-{clip_index:03}.mp4")
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-ss", start_ffmpeg,
                "-i", self.selected_file,
                "-t", duration_str,
                "-c", "copy",
                output_filename
            ]
            self.log_text.insert(tk.END, f"Processing clip {clip_index:03}: {start_str} --> {end_str}\n")
            self.log_text.update()
            ret = subprocess.run(cmd, capture_output=True, text=True)
            if ret.returncode != 0:
                self.log_text.insert(tk.END, f"Error clipping clip {clip_index:03}: {ret.stderr}\n")
            else:
                self.log_text.insert(tk.END, f"Created: {output_filename}\n")
            clip_index += 1

        self.log_text.insert(tk.END, "\nClipping process completed.\n")
        self.log_text.config(state=tk.DISABLED)
        messagebox.showinfo("Done", f"Clipping completed!\nClips saved to:\n{output_dir}")

if __name__ == "__main__":
    app = ClipApp()
    app.mainloop()