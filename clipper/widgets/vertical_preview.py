from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QCursor, QPolygon


class VerticalPreviewWidget(QWidget):
    """Widget to show vertical preview with integrated ratio slider on split line"""
    
    # Signal emitted when ratio changes
    ratio_changed = pyqtSignal(float)
    
    # Aspect ratio presets: (width_ratio, height_ratio, name)
    ASPECT_9_16 = (9, 16, "9:16")
    ASPECT_3_4 = (3, 4, "3:4")
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.source_pixmap = None
        self.top_crop = None
        self.bottom_crop = None
        self.ratio = 0.5  # 50% top, 50% bottom
        
        # Output aspect ratio (width, height)
        self.aspect_w = 9
        self.aspect_h = 16
        
        # Slider state
        self.dragging_slider = False
        self.slider_hover = False
        self.slider_height = 20  # Height of draggable slider area
        
        self.setMinimumWidth(200)
        self.setMinimumHeight(400)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setMouseTracking(True)
    
    def set_aspect_ratio(self, width_ratio, height_ratio):
        """Set the output aspect ratio"""
        self.aspect_w = width_ratio
        self.aspect_h = height_ratio
        self.update()
    
    def set_source(self, pixmap):
        self.source_pixmap = pixmap
        self.update()
    
    def set_crops(self, top_rect, bottom_rect):
        self.top_crop = top_rect
        self.bottom_crop = bottom_rect
        self.update()
    
    def set_ratio(self, ratio):
        """Set ratio without emitting signal (for external updates)"""
        self.ratio = max(0.1, min(0.9, ratio))
        self.update()
    
    def _get_preview_rect(self):
        """Calculate the preview rectangle based on current aspect ratio"""
        margin = 10
        available_height = self.height() - 2 * margin
        preview_height = available_height
        preview_width = int(preview_height * self.aspect_w / self.aspect_h)
        
        if preview_width > self.width() - 2 * margin:
            preview_width = self.width() - 2 * margin
            preview_height = int(preview_width * self.aspect_h / self.aspect_w)
        
        offset_x = (self.width() - preview_width) // 2
        offset_y = (self.height() - preview_height) // 2
        
        return QRect(offset_x, offset_y, preview_width, preview_height)
    
    def _get_slider_rect(self):
        """Get the slider handle rectangle on the split line"""
        preview_rect = self._get_preview_rect()
        split_y = preview_rect.top() + int(preview_rect.height() * self.ratio)
        
        # Slider extends beyond preview for easier grabbing
        slider_width = preview_rect.width() + 40
        slider_x = preview_rect.left() - 20
        
        return QRect(slider_x, split_y - self.slider_height // 2, 
                    slider_width, self.slider_height)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        painter.fillRect(self.rect(), QColor(30, 30, 30))
        
        preview_rect = self._get_preview_rect()
        
        if not self.source_pixmap or not self.top_crop or not self.bottom_crop:
            painter.setPen(Qt.white)
            painter.drawText(self.rect(), Qt.AlignCenter, f"{self.aspect_w}:{self.aspect_h}\nPreview")
            
            # Still draw the frame outline
            painter.setPen(QPen(QColor(100, 100, 100), 2))
            painter.drawRect(preview_rect)
            return
        
        offset_x = preview_rect.left()
        offset_y = preview_rect.top()
        preview_width = preview_rect.width()
        preview_height = preview_rect.height()
        
        # Draw border for preview frame
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawRect(preview_rect.adjusted(-2, -2, 2, 2))
        
        # Calculate heights based on ratio
        top_height = int(preview_height * self.ratio)
        bottom_height = preview_height - top_height
        
        # Crop and draw top section
        if self.top_crop.width() > 0 and self.top_crop.height() > 0:
            top_cropped = self.source_pixmap.copy(self.top_crop)
            top_scaled = top_cropped.scaled(preview_width, top_height,
                                            Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(offset_x, offset_y, top_scaled)
        
        # Crop and draw bottom section
        if self.bottom_crop.width() > 0 and self.bottom_crop.height() > 0:
            bottom_cropped = self.source_pixmap.copy(self.bottom_crop)
            bottom_scaled = bottom_cropped.scaled(preview_width, bottom_height,
                                                  Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(offset_x, offset_y + top_height, bottom_scaled)
        
        # Draw the slider on the split line
        split_y = offset_y + top_height
        slider_rect = self._get_slider_rect()
        
        # Slider background (semi-transparent)
        slider_color = QColor(255, 255, 255, 180) if self.slider_hover or self.dragging_slider else QColor(255, 255, 255, 120)
        
        # Draw slider handle - a horizontal bar with grip lines
        handle_rect = QRect(slider_rect.left() + 10, split_y - 4, slider_rect.width() - 20, 8)
        painter.fillRect(handle_rect, slider_color)
        
        # Draw grip lines on the handle
        grip_color = QColor(80, 80, 80)
        painter.setPen(QPen(grip_color, 1))
        center_x = handle_rect.center().x()
        for dx in [-15, -8, 0, 8, 15]:
            painter.drawLine(center_x + dx, split_y - 2, center_x + dx, split_y + 2)
        
        # Draw triangles on left and right edges as drag indicators
        painter.setBrush(slider_color)
        painter.setPen(Qt.NoPen)
        
        # Left triangle
        left_triangle = QPolygon([
            QPoint(slider_rect.left(), split_y),
            QPoint(slider_rect.left() + 12, split_y - 6),
            QPoint(slider_rect.left() + 12, split_y + 6),
        ])
        painter.drawPolygon(left_triangle)
        
        # Right triangle  
        right_triangle = QPolygon([
            QPoint(slider_rect.right(), split_y),
            QPoint(slider_rect.right() - 12, split_y - 6),
            QPoint(slider_rect.right() - 12, split_y + 6),
        ])
        painter.drawPolygon(right_triangle)
        
        # Draw ratio text
        painter.setPen(Qt.white)
        font = QFont("Arial", 9)
        painter.setFont(font)
        
        top_pct = int(self.ratio * 100)
        bottom_pct = 100 - top_pct
        
        # Draw percentage labels on left side
        painter.drawText(slider_rect.left() - 35, split_y - 15, f"{top_pct}%")
        painter.drawText(slider_rect.left() - 35, split_y + 20, f"{bottom_pct}%")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            slider_rect = self._get_slider_rect()
            if slider_rect.contains(event.pos()):
                self.dragging_slider = True
                self.update()
    
    def mouseMoveEvent(self, event):
        slider_rect = self._get_slider_rect()
        was_hover = self.slider_hover
        self.slider_hover = slider_rect.contains(event.pos())
        
        if self.slider_hover or self.dragging_slider:
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        
        if was_hover != self.slider_hover:
            self.update()
        
        if self.dragging_slider:
            preview_rect = self._get_preview_rect()
            
            # Calculate new ratio based on mouse position
            relative_y = event.pos().y() - preview_rect.top()
            new_ratio = relative_y / preview_rect.height()
            new_ratio = max(0.1, min(0.9, new_ratio))
            
            if abs(new_ratio - self.ratio) > 0.001:
                self.ratio = new_ratio
                self.update()
                self.ratio_changed.emit(self.ratio)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging_slider = False
            self.update()
