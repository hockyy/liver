import sys
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QPushButton, QFileDialog, 
                             QVBoxLayout, QHBoxLayout, QMessageBox, QSlider, QComboBox, QListWidget,
                             QListWidgetItem, QGridLayout)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
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
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Batch Image to WebP Converter')
        self.setGeometry(300, 300, 600, 500)

        layout = QVBoxLayout()

        # Image list
        self.image_list = QListWidget()
        layout.addWidget(QLabel('Selected Images:'))
        layout.addWidget(self.image_list)

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

    def apply_resize_to_all(self):
        try:
            max_width = int(self.width_edit.text())
            max_height = int(self.height_edit.text())
            for index in range(self.image_list.count()):
                item = self.image_list.item(index)
                new_size = self.calculate_new_size(item.original_size, max_width, max_height)
                item.update_new_size(*new_size)
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageConverterApp()
    ex.show()
    sys.exit(app.exec_())