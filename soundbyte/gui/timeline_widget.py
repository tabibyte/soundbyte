from PyQt6.QtWidgets import QWidget, QScrollArea
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush
from PyQt6.QtCore import Qt, QRect, QSize

class TimelineWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(40)
        self.zoom_level = 50
        self.grid_size = 16
        self.track_height = 40
        self.tracks = []
        self.clips = {}
        self.playhead_pos = 0
        self.setAcceptDrops(True)
        self.pending_clip_import = None
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Drag state
        self.drag_start = None
        self.dragged_clip = None
        self.drag_offset = 0
        
    def draw_grid(self, painter):
        """Draw timeline grid"""
        # Set grid pen
        grid_pen = QPen(QColor(40, 40, 40))
        painter.setPen(grid_pen)
        
        # Draw background
        painter.fillRect(self.rect(), QColor(30, 30, 30))
        
        # Draw vertical time divisions
        seconds_visible = self.width() / self.zoom_level
        for x in range(0, self.width(), int(self.zoom_level)):
            # Major lines every second
            if x % self.zoom_level == 0:
                painter.setPen(QPen(QColor(60, 60, 60), 2))
            else:
                # Minor lines for subdivisions
                painter.setPen(QPen(QColor(40, 40, 40)))
            painter.drawLine(x, 0, x, self.height())
            
        # Draw horizontal track divisions
        for y in range(0, len(self.tracks) * self.track_height, self.track_height):
            painter.setPen(QPen(QColor(60, 60, 60)))
            painter.drawLine(0, y, self.width(), y)

    def draw_clips(self, painter):
        """Draw audio clips"""
        clip_brush = QBrush(QColor(60, 100, 160))
        
        for track_id, track_clips in self.clips.items():
            y = track_id * self.track_height
            
            for start_time, end_time, clip_data in track_clips:
                x = int(start_time * self.zoom_level)
                width = int((end_time - start_time) * self.zoom_level)
                painter.fillRect(x, y + 5, width, self.track_height - 10, clip_brush)
                   
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw grid
        self.draw_grid(painter)
        
        # Draw clips
        self.draw_clips(painter)
        
        # Draw playhead
        if self.playhead_pos > 0:
            painter.setPen(QPen(Qt.GlobalColor.red, 2))
            x = int(self.playhead_pos * self.zoom_level)
            painter.drawLine(x, 0, x, self.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            track_idx = event.y() // self.track_height
            time_pos = event.x() / self.zoom_level
            self.clip_clicked.emit(track_idx, time_pos)
        
    def sizeHint(self):
        width = int(60 * self.zoom_level)  # 60 seconds default width
        height = len(self.tracks) * self.track_height
        return QSize(width, height)
    
    def set_pending_clip(self, track_id: int, file_path: str):
        """Set clip waiting for placement"""
        self.pending_clip_import = (track_id, file_path)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.Left and self.pending_clip_import:
            track_id, file_path = self.pending_clip_import
            click_time = event.x() / self.zoom_level
            start_frame = int(click_time * self.engine.sample_rate)
            
            # Add clip at clicked position
            self.engine.add_clip(track_id, file_path, start_frame)
            self.pending_clip_import = None
            self.update()
        
    def mouseMoveEvent(self, event):
        if self.drag_start:
            delta = event.position() - self.drag_start
            # Update clip position
            
    def update_playhead(self, position):
        self.playhead_pos = position
        self.update()
        
    def snap_to_grid(self, x_pos):
        """Snap position to nearest grid line"""
        grid_pixels = self.zoom_level / self.grid_size
        return round(x_pos / grid_pixels) * grid_pixels
