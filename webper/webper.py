import sys
import os
from io import BytesIO
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QPushButton, QFileDialog, 
                             QVBoxLayout, QHBoxLayout, QMessageBox, QSlider, QComboBox, QListWidget,
                             QListWidgetItem, QGridLayout, QMenu, QAction, QScrollArea, QSplitter)
from PyQt5.QtGui import QIcon, QDragEnterEvent, QDropEvent, QPalette, QPixmap, QCursor
from PyQt5.QtCore import Qt, QUrl
from PIL import Image

class ImageItem(QListWidgetItem):
    def __init__(self, file_path):
        super().__init__(os.path.basename(file_path))
        self.file_path = file_path
        self.original_size = self.get_image_size()
        self.new_size = self.original_size
        self.setText(f"{os.path.basename(file_path)} - {self.original_size[0]}x{self.original_size[1]}")

    def get_image_size(self):
        with Image.open(self.file_path) as img:
            return img.size

    def update_new_size(self, width, height):
        self.new_size = (width, height)
        self.setText(f"{os.path.basename(self.file_path)} - {self.original_size[0]}x{self.original_size[1]} -> {width}x{height}")

class ImageConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.webp_size_cache = {}  # Cache for WebP size calculations
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Batch Image to WebP Converter')
        self.setGeometry(300, 300, 900, 600)  # Increased size for preview panel
        
        # Enable drag and drop
        self.setAcceptDrops(True)

        layout = QVBoxLayout()

        # Create main horizontal splitter
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Image list
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel('Selected Images (drag & drop images here or use the button below):'))
        
        self.image_list = QListWidget()
        self.image_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.image_list.customContextMenuRequested.connect(self.show_context_menu)
        self.image_list.itemSelectionChanged.connect(self.update_preview)
        left_layout.addWidget(self.image_list)
        left_widget.setLayout(left_layout)
        
        # Right side - Image preview
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel('Image Preview:'))
        
        # Image info label (dimensions and file size)
        self.image_info_label = QLabel()
        self.image_info_label.setAlignment(Qt.AlignCenter)
        self.image_info_label.setStyleSheet("QLabel { background-color: #e8e8e8; border: 1px solid #ccc; padding: 5px; }")
        self.image_info_label.setText("No image selected")
        right_layout.addWidget(self.image_info_label)
        
        # Create scrollable preview area
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setAlignment(Qt.AlignCenter)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("QLabel { background-color: #f0f0f0; border: 1px solid #ccc; }")
        self.preview_label.setMinimumSize(300, 200)
        self.preview_label.setText("Select an image to preview")
        
        self.preview_scroll.setWidget(self.preview_label)
        right_layout.addWidget(self.preview_scroll)
        right_widget.setLayout(right_layout)
        
        # Add widgets to splitter
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([400, 300])  # Set initial sizes
        
        layout.addWidget(main_splitter)

        # Add images button
        add_button = QPushButton('Add Images')
        add_button.clicked.connect(self.add_images)
        layout.addWidget(add_button)

        # Resize options
        resize_layout = QGridLayout()
        resize_layout.addWidget(QLabel('Resize options:'), 0, 0)

        # Preset sizes
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(['Custom', '1920x1080', '1280x720', '800x600', '640x480'])
        self.preset_combo.currentIndexChanged.connect(self.update_size_from_preset)
        resize_layout.addWidget(self.preset_combo, 0, 1)

        # Custom size input
        self.width_edit = QLineEdit()
        self.width_edit.setPlaceholderText('Max Width')
        self.height_edit = QLineEdit()
        self.height_edit.setPlaceholderText('Max Height')
        resize_layout.addWidget(self.width_edit, 1, 0)
        resize_layout.addWidget(QLabel('x'), 1, 1)
        resize_layout.addWidget(self.height_edit, 1, 2)

        # Size slider
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(10, 100)
        self.size_slider.setValue(100)
        self.size_slider.valueChanged.connect(self.update_size_from_slider)
        resize_layout.addWidget(QLabel('Scale:'), 2, 0)
        resize_layout.addWidget(self.size_slider, 2, 1, 1, 2)

        layout.addLayout(resize_layout)

        # Apply resize button
        apply_resize_button = QPushButton('Apply Resize to All')
        apply_resize_button.clicked.connect(self.apply_resize_to_all)
        layout.addWidget(apply_resize_button)

        # Quality slider
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel('Quality:'))
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(80)
        self.quality_slider.setTickPosition(QSlider.TicksBelow)
        self.quality_slider.setTickInterval(10)
        quality_layout.addWidget(self.quality_slider)
        self.quality_label = QLabel('80')
        quality_layout.addWidget(self.quality_label)
        self.quality_slider.valueChanged.connect(self.update_quality_label)
        self.quality_slider.valueChanged.connect(self.update_preview)  # Update preview when quality changes
        layout.addLayout(quality_layout)

        # Convert button
        convert_button = QPushButton('Convert All to WebP')
        convert_button.clicked.connect(self.convert_images)
        layout.addWidget(convert_button)

        self.setLayout(layout)

    def add_images(self):
        file_names, _ = QFileDialog.getOpenFileNames(self, 'Select Input Images', '', 'Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)')
        for file_name in file_names:
            self.image_list.addItem(ImageItem(file_name))

    def update_size_from_preset(self, index):
        if index == 0:  # Custom
            return
        preset = self.preset_combo.currentText()
        width, height = map(int, preset.split('x'))
        self.width_edit.setText(str(width))
        self.height_edit.setText(str(height))
        self.apply_resize_to_all()

    def update_size_from_slider(self):
        scale = self.size_slider.value() / 100
        for index in range(self.image_list.count()):
            item = self.image_list.item(index)
            new_width = int(item.original_size[0] * scale)
            new_height = int(item.original_size[1] * scale)
            item.update_new_size(new_width, new_height)
        # Update preview if an item is selected
        self.update_preview()

    def apply_resize_to_all(self):
        try:
            max_width = int(self.width_edit.text())
            max_height = int(self.height_edit.text())
            for index in range(self.image_list.count()):
                item = self.image_list.item(index)
                new_size = self.calculate_new_size(item.original_size, max_width, max_height)
                item.update_new_size(*new_size)
            # Update preview if an item is selected
            self.update_preview()
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Please enter valid width and height values.')

    def calculate_new_size(self, original_size, max_width, max_height):
        original_width, original_height = original_size
        aspect_ratio = original_width / original_height

        if original_width <= max_width and original_height <= max_height:
            return original_size

        new_width = max_width
        new_height = int(new_width / aspect_ratio)

        if new_height > max_height:
            new_height = max_height
            new_width = int(new_height * aspect_ratio)

        return (new_width, new_height)

    def update_quality_label(self, value):
        self.quality_label.setText(str(value))

    def convert_images(self):
        if self.image_list.count() == 0:
            QMessageBox.warning(self, 'Error', 'Please add images to convert.')
            return

        quality = self.quality_slider.value()

        for index in range(self.image_list.count()):
            item = self.image_list.item(index)
            input_path = item.file_path
            output_path = os.path.splitext(input_path)[0] + '.webp'

            try:
                with Image.open(input_path) as img:
                    if item.new_size != item.original_size:
                        img = img.resize(item.new_size, Image.LANCZOS)
                    img.save(output_path, 'WEBP', quality=quality)
            except Exception as e:
                QMessageBox.warning(self, 'Error', f'Failed to convert {item.text()}: {str(e)}')

        QMessageBox.information(self, 'Success', 'All images have been converted to WebP format.')

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events"""
        if event.mimeData().hasUrls():
            # Check if any of the dragged items are image files
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if self.is_image_file(file_path):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag move events"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handle drop events"""
        if event.mimeData().hasUrls():
            image_files = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if self.is_image_file(file_path):
                    image_files.append(file_path)
            
            if image_files:
                self.add_dropped_images(image_files)
                event.acceptProposedAction()
            else:
                QMessageBox.warning(self, 'Warning', 'No valid image files were dropped.')
                event.ignore()
        else:
            event.ignore()

    def is_image_file(self, file_path):
        """Check if a file is a valid image file"""
        if not os.path.isfile(file_path):
            return False
        
        valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif', '.webp'}
        _, ext = os.path.splitext(file_path.lower())
        return ext in valid_extensions

    def add_dropped_images(self, file_paths):
        """Add dropped image files to the list"""
        added_count = 0
        for file_path in file_paths:
            # Check if file is already in the list
            already_added = False
            for index in range(self.image_list.count()):
                item = self.image_list.item(index)
                if item.file_path == file_path:
                    already_added = True
                    break
            
            if not already_added:
                try:
                    self.image_list.addItem(ImageItem(file_path))
                    added_count += 1
                except Exception as e:
                    QMessageBox.warning(self, 'Error', f'Failed to add {os.path.basename(file_path)}: {str(e)}')
        
        if added_count > 0:
            QMessageBox.information(self, 'Success', f'Added {added_count} image(s) to the list.')

    def get_file_size_formatted(self, file_path):
        """Get file size in human-readable format"""
        try:
            size_bytes = os.path.getsize(file_path)
            return self.format_file_size(size_bytes)
        except OSError:
            return "Unknown size"

    def format_file_size(self, size_bytes):
        """Format file size in bytes to human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def get_webp_size_estimate(self, file_path, target_size=None):
        """Get estimated WebP file size with caching"""
        quality = self.quality_slider.value()
        
        # Create cache key
        if target_size:
            cache_key = f"{file_path}_{quality}_{target_size[0]}x{target_size[1]}"
        else:
            cache_key = f"{file_path}_{quality}_original"
        
        # Check cache first
        if cache_key in self.webp_size_cache:
            return self.webp_size_cache[cache_key]
        
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if target size is specified
                if target_size and target_size != img.size:
                    img = img.resize(target_size, Image.LANCZOS)
                
                # Convert to WebP in memory
                webp_buffer = BytesIO()
                img.save(webp_buffer, 'WEBP', quality=quality)
                webp_size = webp_buffer.tell()
                
                # Cache the result
                self.webp_size_cache[cache_key] = webp_size
                
                return webp_size
                
        except Exception:
            return None

    def show_context_menu(self, position):
        """Show context menu for right-click on image list"""
        item = self.image_list.itemAt(position)
        if item is not None:
            menu = QMenu()
            
            remove_action = QAction("Remove from queue", self)
            remove_action.triggered.connect(lambda: self.remove_selected_image(item))
            menu.addAction(remove_action)
            
            # Show menu at cursor position
            menu.exec_(self.image_list.mapToGlobal(position))

    def remove_selected_image(self, item):
        """Remove the selected image from the list"""
        row = self.image_list.row(item)
        if row >= 0:
            removed_item = self.image_list.takeItem(row)
            if removed_item:
                # Clear preview if this was the selected item
                if self.image_list.currentItem() is None:
                    self.clear_preview()
                QMessageBox.information(self, 'Removed', f'Removed {os.path.basename(removed_item.file_path)} from queue.')

    def update_preview(self):
        """Update the image preview when selection changes"""
        current_item = self.image_list.currentItem()
        if current_item and hasattr(current_item, 'file_path'):
            self.load_image_preview(current_item.file_path)
        else:
            self.clear_preview()

    def load_image_preview(self, file_path):
        """Load and display image preview"""
        try:
            # Get original file size
            original_size = self.get_file_size_formatted(file_path)
            
            # Open image with PIL to handle various formats
            with Image.open(file_path) as img:
                # Convert to RGB if necessary (for RGBA, etc.)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                img_width, img_height = img.size
                
                # Get current item to check for resize settings
                current_item = self.image_list.currentItem()
                target_size = None
                if current_item and hasattr(current_item, 'new_size') and current_item.new_size != (img_width, img_height):
                    target_size = current_item.new_size
                
                # Get estimated WebP size
                webp_size_bytes = self.get_webp_size_estimate(file_path, target_size)
                
                # Format info text
                filename = os.path.basename(file_path)
                if webp_size_bytes:
                    webp_size = self.format_file_size(webp_size_bytes)
                    original_bytes = os.path.getsize(file_path)
                    compression_ratio = (1 - webp_size_bytes / original_bytes) * 100
                    
                    size_info = f"{original_size} → {webp_size} (−{compression_ratio:.1f}%)"
                    if target_size:
                        self.image_info_label.setText(f"{filename}\n{img_width} × {img_height} px → {target_size[0]} × {target_size[1]} px\n{size_info}")
                    else:
                        self.image_info_label.setText(f"{filename}\n{img_width} × {img_height} px\n{size_info}")
                else:
                    # Fallback if WebP estimation fails
                    if target_size:
                        self.image_info_label.setText(f"{filename}\n{img_width} × {img_height} px → {target_size[0]} × {target_size[1]} px\n{original_size} → WebP (calculating...)")
                    else:
                        self.image_info_label.setText(f"{filename}\n{img_width} × {img_height} px\n{original_size} → WebP (calculating...)")
                
                # Calculate preview size while maintaining aspect ratio
                preview_width = 400
                preview_height = 300
                
                # Calculate scaling factor
                scale_w = preview_width / img_width
                scale_h = preview_height / img_height
                scale = min(scale_w, scale_h, 1.0)  # Don't upscale
                
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                # Resize image
                img_resized = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Convert PIL image to QPixmap
                img_resized.save('temp_preview.png')  # Temporary save
                pixmap = QPixmap('temp_preview.png')
                os.remove('temp_preview.png')  # Clean up
                
                # Update preview
                self.preview_label.setPixmap(pixmap)
                self.preview_label.setText("")  # Clear text
                
        except Exception as e:
            self.clear_preview()
            self.preview_label.setText(f"Error loading image:\n{str(e)}")
            self.image_info_label.setText(f"Error: {str(e)}")

    def clear_preview(self):
        """Clear the image preview"""
        self.preview_label.clear()
        self.preview_label.setText("Select an image to preview")
        self.image_info_label.setText("No image selected")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageConverterApp()
    ex.show()
    sys.exit(app.exec_())