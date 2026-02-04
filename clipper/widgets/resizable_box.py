from PyQt5.QtCore import QRect, QPoint
from PyQt5.QtGui import QColor


class ResizableBox:
    """Represents a resizable and draggable crop box on the preview"""
    
    # Handle positions
    HANDLE_NONE = 0
    HANDLE_TOP_LEFT = 1
    HANDLE_TOP_RIGHT = 2
    HANDLE_BOTTOM_LEFT = 3
    HANDLE_BOTTOM_RIGHT = 4
    HANDLE_TOP = 5
    HANDLE_BOTTOM = 6
    HANDLE_LEFT = 7
    HANDLE_RIGHT = 8
    HANDLE_MOVE = 9  # Dragging the whole box
    
    HANDLE_SIZE = 12  # Size of corner/edge handles in pixels
    
    def __init__(self, x, y, width, height, color, label):
        self.rect = QRect(x, y, width, height)
        self.color = color
        self.label = label
        self.aspect_ratio = width / height if height > 0 else 1.0  # w/h ratio
        self.active_handle = self.HANDLE_NONE
        self.drag_start_pos = QPoint(0, 0)
        self.drag_start_rect = QRect()
    
    def set_aspect_ratio(self, aspect_ratio):
        """Set aspect ratio and adjust current rect to match"""
        self.aspect_ratio = aspect_ratio
        new_height = int(self.rect.width() / aspect_ratio)
        self.rect.setHeight(new_height)
    
    def get_handle_at(self, point, scale=1.0):
        """Determine which handle (if any) is at the given point"""
        handle_size = int(self.HANDLE_SIZE / scale) if scale > 0 else self.HANDLE_SIZE
        
        r = self.rect
        
        # Check corners first (higher priority)
        corners = [
            (self.HANDLE_TOP_LEFT, QRect(r.left() - handle_size//2, r.top() - handle_size//2, handle_size, handle_size)),
            (self.HANDLE_TOP_RIGHT, QRect(r.right() - handle_size//2, r.top() - handle_size//2, handle_size, handle_size)),
            (self.HANDLE_BOTTOM_LEFT, QRect(r.left() - handle_size//2, r.bottom() - handle_size//2, handle_size, handle_size)),
            (self.HANDLE_BOTTOM_RIGHT, QRect(r.right() - handle_size//2, r.bottom() - handle_size//2, handle_size, handle_size)),
        ]
        
        for handle, rect in corners:
            if rect.contains(point):
                return handle
        
        # Check edges
        edges = [
            (self.HANDLE_TOP, QRect(r.left() + handle_size, r.top() - handle_size//2, r.width() - 2*handle_size, handle_size)),
            (self.HANDLE_BOTTOM, QRect(r.left() + handle_size, r.bottom() - handle_size//2, r.width() - 2*handle_size, handle_size)),
            (self.HANDLE_LEFT, QRect(r.left() - handle_size//2, r.top() + handle_size, handle_size, r.height() - 2*handle_size)),
            (self.HANDLE_RIGHT, QRect(r.right() - handle_size//2, r.top() + handle_size, handle_size, r.height() - 2*handle_size)),
        ]
        
        for handle, rect in edges:
            if rect.contains(point):
                return handle
        
        # Check if inside the box (for moving)
        if self.rect.contains(point):
            return self.HANDLE_MOVE
        
        return self.HANDLE_NONE
    
    def start_drag(self, point, handle):
        """Start a drag operation"""
        self.active_handle = handle
        self.drag_start_pos = point
        self.drag_start_rect = QRect(self.rect)
    
    def update_drag(self, point, bounds, maintain_aspect=True):
        """Update the box based on drag movement"""
        if self.active_handle == self.HANDLE_NONE:
            return
        
        dx = point.x() - self.drag_start_pos.x()
        dy = point.y() - self.drag_start_pos.y()
        
        if self.active_handle == self.HANDLE_MOVE:
            new_rect = QRect(self.drag_start_rect)
            new_rect.translate(dx, dy)
            self.rect = new_rect
        else:
            new_rect = QRect(self.drag_start_rect)
            
            if self.active_handle in [self.HANDLE_TOP_LEFT, self.HANDLE_TOP, self.HANDLE_TOP_RIGHT]:
                new_rect.setTop(self.drag_start_rect.top() + dy)
            if self.active_handle in [self.HANDLE_BOTTOM_LEFT, self.HANDLE_BOTTOM, self.HANDLE_BOTTOM_RIGHT]:
                new_rect.setBottom(self.drag_start_rect.bottom() + dy)
            if self.active_handle in [self.HANDLE_TOP_LEFT, self.HANDLE_LEFT, self.HANDLE_BOTTOM_LEFT]:
                new_rect.setLeft(self.drag_start_rect.left() + dx)
            if self.active_handle in [self.HANDLE_TOP_RIGHT, self.HANDLE_RIGHT, self.HANDLE_BOTTOM_RIGHT]:
                new_rect.setRight(self.drag_start_rect.right() + dx)
            
            if maintain_aspect and self.aspect_ratio > 0:
                new_rect = self._adjust_for_aspect_ratio(new_rect)
            
            if new_rect.width() >= 50 and new_rect.height() >= 50:
                self.rect = new_rect
        
        self.constrain_to(bounds)
    
    def _adjust_for_aspect_ratio(self, rect):
        """Adjust rectangle to maintain aspect ratio"""
        current_ratio = rect.width() / rect.height() if rect.height() > 0 else 1.0
        
        if abs(current_ratio - self.aspect_ratio) < 0.01:
            return rect
        
        if self.active_handle in [self.HANDLE_LEFT, self.HANDLE_RIGHT]:
            new_height = int(rect.width() / self.aspect_ratio)
            center_y = rect.center().y()
            rect.setTop(center_y - new_height // 2)
            rect.setBottom(center_y + new_height // 2)
        elif self.active_handle in [self.HANDLE_TOP, self.HANDLE_BOTTOM]:
            new_width = int(rect.height() * self.aspect_ratio)
            center_x = rect.center().x()
            rect.setLeft(center_x - new_width // 2)
            rect.setRight(center_x + new_width // 2)
        else:
            new_height = int(rect.width() / self.aspect_ratio)
            if self.active_handle in [self.HANDLE_TOP_LEFT, self.HANDLE_TOP_RIGHT]:
                rect.setTop(rect.bottom() - new_height)
            else:
                rect.setBottom(rect.top() + new_height)
        
        return rect
    
    def end_drag(self):
        """End drag operation"""
        self.active_handle = self.HANDLE_NONE
    
    def constrain_to(self, bounds):
        """Constrain the box within bounds"""
        if self.rect.left() < bounds.left():
            self.rect.moveLeft(bounds.left())
        if self.rect.top() < bounds.top():
            self.rect.moveTop(bounds.top())
        if self.rect.right() > bounds.right():
            self.rect.moveRight(bounds.right())
        if self.rect.bottom() > bounds.bottom():
            self.rect.moveBottom(bounds.bottom())
    
    def resize_with_aspect_ratio(self, new_aspect_ratio, bounds):
        """Resize box to new aspect ratio, keeping center and area roughly same"""
        center = self.rect.center()
        area = self.rect.width() * self.rect.height()
        
        new_width = int((area * new_aspect_ratio) ** 0.5)
        new_height = int((area / new_aspect_ratio) ** 0.5)
        
        new_width = max(100, new_width)
        new_height = max(100, new_height)
        
        self.rect = QRect(
            center.x() - new_width // 2,
            center.y() - new_height // 2,
            new_width,
            new_height
        )
        self.aspect_ratio = new_aspect_ratio
        self.constrain_to(bounds)
