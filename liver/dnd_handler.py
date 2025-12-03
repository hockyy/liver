"""Drag and drop functionality handler."""
import os
from config import logger, VALID_MEDIA_EXTENSIONS

# Try to import drag and drop support
# windnd works better with customtkinter on Windows
HAS_DND = False
DND_LIB = None

try:
    import windnd
    HAS_DND = True
    DND_LIB = 'windnd'
except ImportError:
    windnd = None
    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
        HAS_DND = True
        DND_LIB = 'tkinterdnd2'
    except ImportError:
        TkinterDnD = None
        DND_FILES = None

if not HAS_DND:
    print("Warning: Neither windnd nor tkinterdnd2 found. Drag and drop will not be available.")
    print("Install with: pip install windnd")


class DragDropHandler:
    """Handles drag and drop file operations."""
    
    def __init__(self, parent_window, queue_listbox, queue_list, log_callback):
        """
        Initialize drag and drop handler.
        
        Args:
            parent_window: Main application window
            queue_listbox: Listbox widget for queue display
            queue_list: List to store queued files
            log_callback: Function to call for logging
        """
        self.parent_window = parent_window
        self.queue_listbox = queue_listbox
        self.queue = queue_list
        self.log_callback = log_callback
        
    def setup(self):
        """Setup drag and drop functionality."""
        if not HAS_DND:
            return False
            
        try:
            if DND_LIB == 'windnd':
                # windnd is simpler and works great with customtkinter on Windows
                windnd.hook_dropfiles(self.parent_window, func=self._on_drop_windnd)
                windnd.hook_dropfiles(self.queue_listbox, func=self._on_drop_windnd)
                logger.info("Drag and drop initialized successfully using windnd!")
                return True
                
            elif DND_LIB == 'tkinterdnd2':
                # tkinterdnd2 fallback
                root = self.parent_window.winfo_toplevel()
                
                # Try to initialize tkdnd on the root window
                try:
                    root.tk.call('package', 'require', 'tkdnd')
                except:
                    try:
                        TkinterDnD._require(root.tk)
                    except:
                        pass
                
                # Register the listbox as a drop target
                self.queue_listbox.drop_target_register(DND_FILES)
                self.queue_listbox.dnd_bind('<<Drop>>', self._on_drop_tkinterdnd)
                logger.info("Drag and drop initialized successfully using tkinterdnd2!")
                return True
                
        except Exception as e:
            logger.warning(f"Could not setup drag and drop: {e}")
            return False
    
    def _on_drop_windnd(self, files):
        """Handle files dropped using windnd library."""
        # windnd provides files as a tuple of byte paths - decode them
        decoded_files = []
        for file_path in files:
            if isinstance(file_path, bytes):
                # Decode bytes to string - try multiple encodings
                try:
                    decoded = file_path.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        decoded = file_path.decode('gbk')  # Chinese encoding
                    except UnicodeDecodeError:
                        decoded = file_path.decode('latin-1')  # Fallback
                decoded_files.append(decoded)
            else:
                decoded_files.append(str(file_path))
        
        self._process_dropped_files(decoded_files)
    
    def _on_drop_tkinterdnd(self, event):
        """Handle files dropped using tkinterdnd2 library."""
        # Parse the dropped files from event data
        files = self._parse_drop_files(event.data)
        self._process_dropped_files(files)
        return event.action
    
    def _process_dropped_files(self, files):
        """Process dropped files (common handler for both DnD libraries)."""
        added_count = 0
        
        for file_path in files:
            # Clean the path
            if isinstance(file_path, str):
                file_path = file_path.strip().strip('{}').strip('"').strip("'")
            
            # Check if file exists and has valid extension
            if os.path.isfile(file_path):
                ext = os.path.splitext(file_path)[1].lower()
                if ext in VALID_MEDIA_EXTENSIONS:
                    if file_path not in self.queue:
                        self.queue.append(file_path)
                        self.queue_listbox.insert('end', file_path)
                        added_count += 1
                else:
                    self.log_callback(f"Skipped (unsupported format): {file_path}\n")
            elif os.path.isdir(file_path):
                # If it's a directory, scan for media files
                added_count += self._add_files_from_directory(file_path)
        
        if added_count > 0:
            self.log_callback(f"Added {added_count} file(s) via drag and drop\n")
    
    def _parse_drop_files(self, data):
        """Parse dropped file paths from the event data."""
        files = []
        
        # Handle different formats depending on OS
        if data.startswith('{'):
            # Windows format with braces
            data = data.strip('{}')
            # Split by '} {' for multiple files
            if '} {' in data:
                files = data.split('} {')
            else:
                files = [data]
        else:
            # Try splitting by spaces or newlines
            files = data.split()
        
        # Clean up the paths
        cleaned_files = []
        for f in files:
            f = f.strip().strip('{}').strip('"').strip("'")
            if f:
                cleaned_files.append(f)
        
        return cleaned_files
    
    def _add_files_from_directory(self, directory):
        """Recursively add all valid media files from a directory."""
        added_count = 0
        try:
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in VALID_MEDIA_EXTENSIONS:
                        file_path = os.path.join(root, filename)
                        if file_path not in self.queue:
                            self.queue.append(file_path)
                            self.queue_listbox.insert('end', file_path)
                            added_count += 1
        except Exception as e:
            self.log_callback(f"Error scanning directory {directory}: {e}\n")
        
        return added_count

