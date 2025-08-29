"""GUI module for Subana application"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, List
import os

from models import SubanaProject, Track, Cue
from extractor import SubanaExtractor
from exporters import ExporterFactory
from utils import milliseconds_to_time


class SubanaGUI:
    """Main GUI application for Subana"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Subana - Subtitle & Cue Extractor")
        self.root.geometry("1300x750")
        
        # Configure style
        self.setup_style()
        
        # Variables
        self.json_file_path = tk.StringVar()
        self.selected_track = tk.StringVar()
        self.project: Optional[SubanaProject] = None
        self.current_track: Optional[Track] = None
        
        # Build GUI
        self.build_gui()
        
        # Initialize status
        self.update_status("Ready")
    
    def setup_style(self):
        """Configure GUI style"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('Title.TLabel', font=('Segoe UI', 10, 'bold'))
        style.configure('Info.TLabel', font=('Segoe UI', 9))
    
    def build_gui(self):
        """Build the main GUI"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # File selection section
        self.build_file_section(main_frame)
        
        # Track selection section
        self.build_track_section(main_frame)
        
        # Project info section
        self.build_info_section(main_frame)
        
        # Cues display section
        self.build_cues_section(main_frame)
        
        # Export section
        self.build_export_section(main_frame)
        
        # Status bar
        self.status_bar = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=5, column=0, sticky="ew", pady=(5, 0))
    
    def build_file_section(self, parent):
        """Build file selection section"""
        frame = ttk.LabelFrame(parent, text="File Selection", padding="10")
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        frame.columnconfigure(1, weight=1)
        
        ttk.Label(frame, text="JSON File:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Entry(frame, textvariable=self.json_file_path, width=80).grid(
            row=0, column=1, sticky="ew", padx=5
        )
        ttk.Button(frame, text="Browse", command=self.browse_file).grid(
            row=0, column=2, padx=(5, 0)
        )
        ttk.Button(frame, text="Load", command=self.load_file).grid(
            row=0, column=3, padx=(10, 0)
        )
    
    def build_track_section(self, parent):
        """Build track selection section"""
        frame = ttk.LabelFrame(parent, text="Track Selection", padding="10")
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        frame.columnconfigure(1, weight=1)
        
        ttk.Label(frame, text="Select Track:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        
        self.track_combo = ttk.Combobox(
            frame, 
            textvariable=self.selected_track,
            state="readonly",
            width=50
        )
        self.track_combo.grid(row=0, column=1, sticky="ew", padx=5)
        self.track_combo.bind("<<ComboboxSelected>>", self.on_track_selected)
        
        # Add "All Tracks" option by default
        self.track_combo['values'] = ["All Tracks"]
        self.track_combo.current(0)
        
        # Track info label
        self.track_info_label = ttk.Label(frame, text="No track loaded", style='Info.TLabel')
        self.track_info_label.grid(row=0, column=2, padx=(10, 0))
        
        # Statistics frame
        stats_frame = ttk.Frame(frame)
        stats_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        
        self.stats_label = ttk.Label(stats_frame, text="", style='Info.TLabel')
        self.stats_label.pack(side=tk.LEFT)
    
    def build_info_section(self, parent):
        """Build project info section"""
        frame = ttk.LabelFrame(parent, text="Project Information", padding="10")
        frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        frame.columnconfigure(0, weight=1)
        
        self.info_text = tk.Text(frame, height=3, wrap=tk.WORD, font=('Segoe UI', 9))
        self.info_text.grid(row=0, column=0, sticky="ew")
        self.info_text.config(state=tk.DISABLED)
    
    def build_cues_section(self, parent):
        """Build cues display section"""
        frame = ttk.LabelFrame(parent, text="Extracted Cues", padding="10")
        frame.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        
        # Create Treeview
        columns = ('Speaker', 'Start Time', 'End Time', 'Duration', 'Text', 'Original Text')
        self.tree = ttk.Treeview(frame, columns=columns, show='tree headings', height=20)
        
        # Configure columns
        self.tree.heading('#0', text='#')
        self.tree.column('#0', width=50)
        self.tree.heading('Speaker', text='Speaker')
        self.tree.column('Speaker', width=100)
        self.tree.heading('Start Time', text='Start Time')
        self.tree.column('Start Time', width=120)
        self.tree.heading('End Time', text='End Time')
        self.tree.column('End Time', width=120)
        self.tree.heading('Duration', text='Duration')
        self.tree.column('Duration', width=80)
        self.tree.heading('Text', text='Text')
        self.tree.column('Text', width=350)
        self.tree.heading('Original Text', text='Original Text')
        self.tree.column('Original Text', width=350)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
    
    def build_export_section(self, parent):
        """Build export section"""
        frame = ttk.LabelFrame(parent, text="Export Options", padding="10")
        frame.grid(row=4, column=0, sticky="ew")
        
        # Export buttons
        ttk.Button(frame, text="Export to TXT", command=lambda: self.export_file('txt')).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="Export to CSV", command=lambda: self.export_file('csv')).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="Export to SRT", command=lambda: self.export_file('srt')).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="Export to VTT", command=lambda: self.export_file('vtt')).pack(side=tk.LEFT, padx=5)
        
        # Separator
        ttk.Separator(frame, orient='vertical').pack(side=tk.LEFT, padx=10, fill='y')
        
        # Export all tracks button
        ttk.Button(
            frame, 
            text="Export All Tracks Separately", 
            command=self.export_all_tracks_separately
        ).pack(side=tk.LEFT, padx=5)
        
        # Clear button
        ttk.Separator(frame, orient='vertical').pack(side=tk.LEFT, padx=10, fill='y')
        ttk.Button(frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
    
    def browse_file(self):
        """Browse for JSON file"""
        filename = filedialog.askopenfilename(
            title="Select JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.json_file_path.set(filename)
    
    def load_file(self):
        """Load and process JSON file"""
        file_path = self.json_file_path.get()
        if not file_path:
            messagebox.showwarning("Warning", "Please select a JSON file first")
            return
        
        try:
            self.update_status("Loading file...")
            self.root.update()
            
            # Extract project data
            self.project = SubanaExtractor.extract_project(file_path)
            
            # Update track dropdown
            self.update_track_dropdown()
            
            # Display project info
            self.display_project_info()
            
            # Load all tracks by default
            self.selected_track.set("All Tracks")
            self.on_track_selected()
            
            self.update_status(f"Successfully loaded {self.project.total_cues} cues from {self.project.track_count} tracks")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading file: {str(e)}")
            self.update_status("Error loading file")
    
    def update_track_dropdown(self):
        """Update track selection dropdown"""
        if not self.project:
            return
        
        # Create track options
        track_options = ["All Tracks"]
        
        for track in self.project.tracks:
            # Create display name with cue count
            display_name = f"{track.speaker_name} - {track.cue_count} cues ({track.id[:8]}...)"
            track_options.append(display_name)
        
        self.track_combo['values'] = track_options
        self.track_combo.current(0)
    
    def on_track_selected(self, event=None):
        """Handle track selection change"""
        if not self.project:
            return
        
        selected = self.selected_track.get()
        
        if selected == "All Tracks":
            self.current_track = None
            self.display_all_cues()
            self.track_info_label.config(text=f"Showing all {self.project.track_count} tracks")
        else:
            # Extract track index from selection
            try:
                track_index = self.track_combo.current() - 1  # -1 because "All Tracks" is at index 0
                if 0 <= track_index < len(self.project.tracks):
                    self.current_track = self.project.tracks[track_index]
                    self.display_track_cues(self.current_track)
                    self.track_info_label.config(text=f"Track: {self.current_track.cue_count} cues")
            except:
                pass
    
    def display_project_info(self):
        """Display project information"""
        if not self.project:
            return
        
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        
        info_lines = []
        info = self.project.info
        
        if info.name:
            info_lines.append(f"Project: {info.name}")
        if info.id:
            info_lines.append(f"ID: {info.id}")
        if info.duration_formatted != "Unknown":
            info_lines.append(f"Duration: {info.duration_formatted}")
        
        self.info_text.insert(1.0, ' | '.join(info_lines))
        self.info_text.config(state=tk.DISABLED)
    
    def display_all_cues(self):
        """Display all cues from all tracks"""
        self.tree.delete(*self.tree.get_children())
        
        if not self.project:
            return
        
        cue_number = 1
        total_cues = 0
        
        for track in self.project.tracks:
            for cue in track.cues:
                self.add_cue_to_tree(cue_number, cue)
                cue_number += 1
                total_cues += 1
        
        self.update_statistics(total_cues, len(self.project.tracks))
    
    def display_track_cues(self, track: Track):
        """Display cues from a specific track"""
        self.tree.delete(*self.tree.get_children())
        
        for i, cue in enumerate(track.cues, 1):
            self.add_cue_to_tree(i, cue)
        
        self.update_statistics(track.cue_count, 1)
    
    def add_cue_to_tree(self, number: int, cue: Cue):
        """Add a single cue to the tree view"""
        duration_sec = cue.duration_seconds
        
        self.tree.insert('', 'end', text=str(number),
            values=(
                cue.speaker,
                milliseconds_to_time(cue.start_ms),
                milliseconds_to_time(cue.end_ms),
                f"{duration_sec:.2f}s",
                cue.text,
                cue.original_text
            ))
    
    def update_statistics(self, cue_count: int, track_count: int):
        """Update statistics display"""
        if track_count == 1:
            self.stats_label.config(text=f"Displaying {cue_count} cues from 1 track")
        else:
            self.stats_label.config(text=f"Displaying {cue_count} cues from {track_count} tracks")
    
    def export_file(self, format: str):
        """Export cues to file"""
        if not self.project:
            messagebox.showwarning("Warning", "No data to export")
            return
        
        # Get file path
        filetypes = {
            'txt': ("Text files", "*.txt"),
            'csv': ("CSV files", "*.csv"),
            'srt': ("SRT files", "*.srt"),
            'vtt': ("WebVTT files", "*.vtt")
        }
        
        filename = filedialog.asksaveasfilename(
            defaultextension=f".{format}",
            filetypes=[filetypes[format], ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            # Create exporter
            exporter = ExporterFactory.create_exporter(format, self.project)
            
            # Export based on current selection
            if self.current_track:
                exporter.export(filename, self.current_track.id)
                track_info = f" from track '{self.current_track.speaker_name}'"
            else:
                exporter.export(filename)
                track_info = " from all tracks"
            
            messagebox.showinfo("Success", f"Exported{track_info} to {os.path.basename(filename)}")
            self.update_status(f"Exported to {os.path.basename(filename)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error exporting file: {str(e)}")
    
    def export_all_tracks_separately(self):
        """Export each track to a separate file"""
        if not self.project or not self.project.tracks:
            messagebox.showwarning("Warning", "No tracks to export")
            return
        
        # Ask for output directory
        output_dir = filedialog.askdirectory(title="Select output directory for track exports")
        if not output_dir:
            return
        
        # Ask for format
        format_dialog = tk.Toplevel(self.root)
        format_dialog.title("Select Export Format")
        format_dialog.geometry("300x150")
        
        tk.Label(format_dialog, text="Select export format for all tracks:").pack(pady=10)
        
        format_var = tk.StringVar(value="srt")
        formats = [("SRT", "srt"), ("VTT", "vtt"), ("TXT", "txt"), ("CSV", "csv")]
        
        for text, value in formats:
            ttk.Radiobutton(format_dialog, text=text, variable=format_var, value=value).pack(anchor=tk.W, padx=20)
        
        def do_export():
            format_dialog.destroy()
            
            try:
                export_format = format_var.get()
                exported_count = 0
                
                for track in self.project.tracks:
                    # Create filename
                    safe_speaker = "".join(c for c in track.speaker_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    filename = f"{safe_speaker}_{track.id[:8]}.{export_format}"
                    file_path = os.path.join(output_dir, filename)
                    
                    # Export track
                    exporter = ExporterFactory.create_exporter(export_format, self.project)
                    exporter.export(file_path, track.id)
                    exported_count += 1
                
                messagebox.showinfo("Success", f"Exported {exported_count} tracks to {output_dir}")
                self.update_status(f"Exported {exported_count} tracks")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error exporting tracks: {str(e)}")
        
        ttk.Button(format_dialog, text="Export", command=do_export).pack(pady=10)
    
    def clear_all(self):
        """Clear all data and reset GUI"""
        self.project = None
        self.current_track = None
        self.json_file_path.set("")
        self.selected_track.set("All Tracks")
        self.track_combo['values'] = ["All Tracks"]
        self.tree.delete(*self.tree.get_children())
        
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.config(state=tk.DISABLED)
        
        self.track_info_label.config(text="No track loaded")
        self.stats_label.config(text="")
        self.update_status("Ready")
    
    def update_status(self, message: str):
        """Update status bar"""
        self.status_bar.config(text=message)
        self.root.update()


def run():
    """Run the GUI application"""
    root = tk.Tk()
    app = SubanaGUI(root)
    root.mainloop()


if __name__ == "__main__":
    run()
