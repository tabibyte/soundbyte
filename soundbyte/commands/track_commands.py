from .base import Command
from PyQt6.QtWidgets import QListWidgetItem, QMessageBox
from PyQt6.QtCore import Qt
from gui.track_widget import TrackWidget

class AddTrackCommand(Command):
    def __init__(self, window, file_path):
        self.window = window
        self.file_path = file_path
        self.track_id = None
        
    def execute(self):
        try:
            self.track_id = self.window.audio_engine.add_track(self.file_path)
            track_widget = TrackWidget(self.track_id, self.window.audio_engine)
            self.window.tracks_layout.addWidget(track_widget)
            self.window.track_list.addItem(f"Track {self.track_id}")
            self.window.play_button.setEnabled(True)
            return self.track_id
        except Exception as e:
            QMessageBox.critical(self.window, "Error", f"Failed to add track: {str(e)}")
            return None
        
    def undo(self):
        if self.track_id is not None:
            # Remove from engine
            del self.window.audio_engine.tracks[self.track_id]
            
            # Remove widget
            for i in reversed(range(self.window.tracks_layout.count())): 
                widget = self.window.tracks_layout.itemAt(i).widget()
                if isinstance(widget, TrackWidget) and widget.track_id == self.track_id:
                    widget.deleteLater()
                    break
                    
            # Remove from list
            items = self.window.track_list.findItems(f"Track {self.track_id}", Qt.MatchExactly)
            if items:
                self.window.track_list.takeItem(self.window.track_list.row(items[0]))
            
            if not self.window.audio_engine.tracks:
                self.window.play_button.setEnabled(False)