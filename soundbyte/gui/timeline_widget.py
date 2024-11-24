from PyQt6.QtWidgets import QWidget, QScrollArea
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush
from PyQt6.QtCore import Qt, QRect, QSize, QPointF
import os

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
        self.engine = None
        self.setAcceptDrops(True)
        self.pending_clip_import = None
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Drag state
        self.drag_start = None
        self.dragged_clip = None
        self.drag_offset = 0
    
    def set_engine(self, engine):
        """Set audio engine reference"""
        self.engine = engine
        
    def set_pending_clip(self, track_id: int, file_path: str):
        """Set clip waiting for placement"""
        print(f"Ready to place clip: track {track_id}, file {file_path}")
        self.pending_clip_import = (track_id, file_path)
        self.setCursor(Qt.CursorShape.CrossCursor)
           
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
            
            for start_time, end_time, file_path in track_clips:
                x = int(start_time * self.zoom_level)
                width = int((end_time - start_time) * self.zoom_level)
                
                # Draw clip background
                painter.fillRect(x, y + 2, width, self.track_height - 4, clip_brush)
                
                # Draw clip name
                painter.setPen(Qt.GlobalColor.white)
                clip_name = os.path.basename(file_path)
                painter.drawText(x + 4, y + self.track_height//2, clip_name)
                   
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
        if event.button() == Qt.MouseButton.LeftButton and self.pending_clip_import:
            if not self.engine:
                print("No engine reference set")
                return
                
            track_id, file_path = self.pending_clip_import
            click_time = event.x() / self.zoom_level
            start_frame = int(click_time * self.engine.sample_rate)
            
            print(f"Adding clip at frame {start_frame}")
            success = self.engine.add_clip(track_id, file_path, start_frame)
            
            if success:
                if track_id not in self.clips:
                    self.clips[track_id] = []
                    
                # Get audio file length
                import soundfile as sf
                audio_data, sr = sf.read(file_path)
                duration = len(audio_data) / sr
                
                self.clips[track_id].append((click_time, click_time + duration, file_path))
                
            self.pending_clip_import = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
            
            # For debugging
            print(f"Clips after adding: {self.clips}")
        
    def sizeHint(self):
        width = int(60 * self.zoom_level)  # 60 seconds default width
        height = len(self.tracks) * self.track_height
        return QSize(width, height)
    
    def set_pending_clip(self, track_id: int, file_path: str):
        """Set clip waiting for placement"""
        self.pending_clip_import = (track_id, file_path)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.pending_clip_import:
            track_id, file_path = self.pending_clip_import
            click_time = event.x() / self.zoom_level
            start_frame = int(click_time * self.engine.sample_rate)
            
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
