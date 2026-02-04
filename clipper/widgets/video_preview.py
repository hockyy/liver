from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QFont

from .resizable_box import ResizableBox


class VideoPreviewWidget(QWidget):
    """Widget to display video frame with resizable crop boxes"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = None
        self.scaled_pixmap = None
        self.image_rect = QRect()
        
        # Source video dimensions
        self.video_width = 1920
        self.video_height = 1080
        
        # Output aspect ratio (width:height)
        self.output_aspect_w = 9
        self.output_aspect_h = 16
        
        # Top/bottom split ratio (0.5 = 50% each)
        self.split_ratio = 0.5
        
        # Whether to show crop boxes (only in vertical mode)
        self.show_boxes = True
        
        # Calculate initial aspect ratios for boxes
        top_aspect = self.output_aspect_w / (self.output_aspect_h * self.split_ratio)
        bottom_aspect = self.output_aspect_w / (self.output_aspect_h * (1 - self.split_ratio))
        
        # Create two resizable boxes for top and bottom crops
        box_height = 400
        top_width = int(box_height * top_aspect)
        bottom_width = int(box_height * bottom_aspect)
        
        self.top_box = ResizableBox(100, 100, top_width, box_height, 
                                     QColor(255, 100, 100, 180), "TOP")
        self.top_box.aspect_ratio = top_aspect
        
        self.bottom_box = ResizableBox(600, 100, bottom_width, box_height,
                                        QColor(100, 100, 255, 180), "BOTTOM")
        self.bottom_box.aspect_ratio = bottom_aspect
        
        self.active_box = None
        
        self.setMinimumSize(640, 360)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Callback for when boxes change
        self.on_boxes_changed = None
    
    def set_boxes_visible(self, visible):
        """Show or hide crop boxes"""
        self.show_boxes = visible
        self.update()
    
    def set_output_aspect(self, width_ratio, height_ratio):
        """Set the output aspect ratio and update crop boxes"""
        self.output_aspect_w = width_ratio
        self.output_aspect_h = height_ratio
        # Recalculate box aspect ratios with new output aspect
        self.set_split_ratio(self.split_ratio)
    
    def set_split_ratio(self, ratio):
        """Update the split ratio and adjust box aspect ratios"""
        self.split_ratio = ratio
        
        # Calculate aspect ratios based on output format
        # For output W:H, top section covers (ratio * H), bottom covers ((1-ratio) * H)
        # Top box aspect = W / (H * ratio), Bottom box aspect = W / (H * (1-ratio))
        w = self.output_aspect_w
        h = self.output_aspect_h
        
        top_aspect = w / (h * ratio) if ratio > 0.05 else w / (h * 0.05)
        bottom_aspect = w / (h * (1 - ratio)) if (1 - ratio) > 0.05 else w / (h * 0.05)
        
        video_bounds = QRect(0, 0, self.video_width, self.video_height)
        
        self.top_box.resize_with_aspect_ratio(top_aspect, video_bounds)
        self.bottom_box.resize_with_aspect_ratio(bottom_aspect, video_bounds)
        
        self.update()
        self._notify_change()
    
    def set_image(self, image_path, video_width, video_height):
        """Load an image and set video dimensions"""
        self.video_width = video_width
        self.video_height = video_height
        self.pixmap = QPixmap(image_path)
        
        w = self.output_aspect_w
        h = self.output_aspect_h
        top_aspect = w / (h * self.split_ratio)
        bottom_aspect = w / (h * (1 - self.split_ratio))
        
        box_height = int(video_height * 0.7)
        top_width = min(int(box_height * top_aspect), int(video_width * 0.4))
        bottom_width = min(int(box_height * bottom_aspect), int(video_width * 0.4))
        
        top_height = int(top_width / top_aspect)
        bottom_height = int(bottom_width / bottom_aspect)
        
        self.top_box.rect = QRect(50, (video_height - top_height) // 2, top_width, top_height)
        self.top_box.aspect_ratio = top_aspect
        
        self.bottom_box.rect = QRect(video_width - bottom_width - 50, 
                                      (video_height - bottom_height) // 2, 
                                      bottom_width, bottom_height)
        self.bottom_box.aspect_ratio = bottom_aspect
        
        self.update()
        self._notify_change()
    
    def _get_scale_factor(self):
        """Get the scale factor from video coordinates to widget coordinates"""
        if not self.pixmap:
            return 1.0
        
        available_width = self.width() - 20
        available_height = self.height() - 20
        
        scale_x = available_width / self.video_width
        scale_y = available_height / self.video_height
        return min(scale_x, scale_y)
    
    def _video_to_widget(self, rect):
        """Convert video coordinates to widget coordinates"""
        scale = self._get_scale_factor()
        offset_x = (self.width() - self.video_width * scale) / 2
        offset_y = (self.height() - self.video_height * scale) / 2
        
        return QRect(
            int(rect.x() * scale + offset_x),
            int(rect.y() * scale + offset_y),
            int(rect.width() * scale),
            int(rect.height() * scale)
        )
    
    def _widget_to_video(self, point):
        """Convert widget coordinates to video coordinates"""
        scale = self._get_scale_factor()
        offset_x = (self.width() - self.video_width * scale) / 2
        offset_y = (self.height() - self.video_height * scale) / 2
        
        return QPoint(
            int((point.x() - offset_x) / scale),
            int((point.y() - offset_y) / scale)
        )
    
    def _get_cursor_for_handle(self, handle):
        """Get appropriate cursor for a handle type"""
        if handle == ResizableBox.HANDLE_NONE:
            return Qt.ArrowCursor
        elif handle == ResizableBox.HANDLE_MOVE:
            return Qt.SizeAllCursor
        elif handle in [ResizableBox.HANDLE_TOP_LEFT, ResizableBox.HANDLE_BOTTOM_RIGHT]:
            return Qt.SizeFDiagCursor
        elif handle in [ResizableBox.HANDLE_TOP_RIGHT, ResizableBox.HANDLE_BOTTOM_LEFT]:
            return Qt.SizeBDiagCursor
        elif handle in [ResizableBox.HANDLE_TOP, ResizableBox.HANDLE_BOTTOM]:
            return Qt.SizeVerCursor
        elif handle in [ResizableBox.HANDLE_LEFT, ResizableBox.HANDLE_RIGHT]:
            return Qt.SizeHorCursor
        return Qt.ArrowCursor
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.fillRect(self.rect(), QColor(40, 40, 40))
        
        if self.pixmap:
            scale = self._get_scale_factor()
            scaled_width = int(self.video_width * scale)
            scaled_height = int(self.video_height * scale)
            
            offset_x = (self.width() - scaled_width) // 2
            offset_y = (self.height() - scaled_height) // 2
            
            self.image_rect = QRect(offset_x, offset_y, scaled_width, scaled_height)
            scaled_pixmap = self.pixmap.scaled(scaled_width, scaled_height, 
                                                Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(offset_x, offset_y, scaled_pixmap)
            
            # Only draw crop boxes if visible (vertical mode enabled)
            if self.show_boxes:
                for box in [self.bottom_box, self.top_box]:
                    widget_rect = self._video_to_widget(box.rect)
                    
                    painter.fillRect(widget_rect, box.color)
                    
                    pen = QPen(box.color.darker(150))
                    pen.setWidth(3)
                    painter.setPen(pen)
                    painter.drawRect(widget_rect)
                    
                    # Draw resize handles
                    handle_size = 10
                    handle_color = QColor(255, 255, 255, 200)
                    
                    corners = [
                        (widget_rect.left(), widget_rect.top()),
                        (widget_rect.right() - handle_size, widget_rect.top()),
                        (widget_rect.left(), widget_rect.bottom() - handle_size),
                        (widget_rect.right() - handle_size, widget_rect.bottom() - handle_size),
                    ]
                    
                    for cx, cy in corners:
                        painter.fillRect(cx, cy, handle_size, handle_size, handle_color)
                        painter.setPen(QPen(box.color.darker(200), 1))
                        painter.drawRect(cx, cy, handle_size, handle_size)
                    
                    edge_handles = [
                        (widget_rect.center().x() - handle_size//2, widget_rect.top()),
                        (widget_rect.center().x() - handle_size//2, widget_rect.bottom() - handle_size),
                        (widget_rect.left(), widget_rect.center().y() - handle_size//2),
                        (widget_rect.right() - handle_size, widget_rect.center().y() - handle_size//2),
                    ]
                    
                    for ex, ey in edge_handles:
                        painter.fillRect(int(ex), int(ey), handle_size, handle_size, handle_color)
                        painter.setPen(QPen(box.color.darker(200), 1))
                        painter.drawRect(int(ex), int(ey), handle_size, handle_size)
                    
                    font = QFont("Arial", 12, QFont.Bold)
                    painter.setFont(font)
                    painter.setPen(Qt.white)
                    
                    aspect_text = f"{box.label}\n{box.rect.width()}x{box.rect.height()}"
                    painter.drawText(widget_rect, Qt.AlignCenter, aspect_text)
        else:
            painter.setPen(Qt.white)
            painter.drawText(self.rect(), Qt.AlignCenter, "Load a video to see preview")
    
    def mousePressEvent(self, event):
        if not self.show_boxes:
            return
            
        if event.button() == Qt.LeftButton:
            video_pos = self._widget_to_video(event.pos())
            scale = self._get_scale_factor()
            
            for box in [self.top_box, self.bottom_box]:
                handle = box.get_handle_at(video_pos, scale)
                if handle != ResizableBox.HANDLE_NONE:
                    self.active_box = box
                    box.start_drag(video_pos, handle)
                    break
    
    def mouseMoveEvent(self, event):
        if not self.show_boxes:
            self.setCursor(Qt.ArrowCursor)
            return
            
        video_pos = self._widget_to_video(event.pos())
        video_bounds = QRect(0, 0, self.video_width, self.video_height)
        scale = self._get_scale_factor()
        
        if self.active_box and self.active_box.active_handle != ResizableBox.HANDLE_NONE:
            self.active_box.update_drag(video_pos, video_bounds, maintain_aspect=True)
            self.update()
            self._notify_change()
        else:
            cursor = Qt.ArrowCursor
            for box in [self.top_box, self.bottom_box]:
                handle = box.get_handle_at(video_pos, scale)
                if handle != ResizableBox.HANDLE_NONE:
                    cursor = self._get_cursor_for_handle(handle)
                    break
            self.setCursor(cursor)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.active_box:
                self.active_box.end_drag()
                self.active_box = None
    
    def _notify_change(self):
        if self.on_boxes_changed:
            self.on_boxes_changed()
    
    def get_crop_params(self):
        """Return crop parameters for ffmpeg (x, y, w, h) for top and bottom boxes"""
        def make_even(val):
            return val if val % 2 == 0 else val - 1
        
        top = {
            'x': self.top_box.rect.x(),
            'y': self.top_box.rect.y(),
            'w': make_even(self.top_box.rect.width()),
            'h': make_even(self.top_box.rect.height())
        }
        bottom = {
            'x': self.bottom_box.rect.x(),
            'y': self.bottom_box.rect.y(),
            'w': make_even(self.bottom_box.rect.width()),
            'h': make_even(self.bottom_box.rect.height())
        }
        return top, bottom
