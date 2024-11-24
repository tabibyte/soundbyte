from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, 
                           QSlider, QPushButton, QLabel, QFileDialog,QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
import os

class TrackWidget(QWidget):
    clip_import_requested = pyqtSignal(int, str, int)
    
    def __init__(self, track_id: int, engine, parent=None):
        super().__init__(parent)
        self.track_id = track_id
        self.engine = engine
        self.setFixedHeight(80)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Track name label
        self.name_label = QLabel(f"Track {track_id + 1}")
        self.name_label.setStyleSheet("""
            QLabel {
                color: #ddd;
                font-size: 11px;
                min-width: 80px;
                padding: 2px;
            }
        """)
        
        # Controls layout
        controls = QHBoxLayout()
        controls.setSpacing(4)
        
        # Volume, Mute, Solo controls...
        self.volume_slider = QSlider(Qt.Orientation.Vertical)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.valueChanged.connect(self.volume_changed)
        
        self.mute_btn = QPushButton("M")
        self.mute_btn.setCheckable(True)
        self.mute_btn.setFixedSize(24, 24)
        self.mute_btn.toggled.connect(self.mute_toggled)
        
        self.solo_btn = QPushButton("S")
        self.solo_btn.setCheckable(True)
        self.solo_btn.setFixedSize(24, 24)
        self.solo_btn.toggled.connect(self.solo_toggled)
        
        # Import button
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.import_audio)

        # Add widgets to layout
        layout.addWidget(self.name_label)
        controls.addWidget(self.volume_slider)
        controls.addWidget(self.mute_btn)
        controls.addWidget(self.solo_btn)
        controls.addWidget(import_btn)
        layout.addLayout(controls)

    def mute_toggled(self, checked: bool):
        """Handle mute button toggle"""
        self.engine.set_track_mute(self.track_id, checked)
        
    def solo_toggled(self, checked: bool):
        """Handle solo button toggle"""
        self.engine.set_track_solo(self.track_id, checked)
        
    def volume_changed(self, value):
        """Add volume level indicator"""
        volume = value / 100.0
        self.engine.set_track_volume(self.track_id, volume)
        self.volume_slider.setToolTip(f"{value}%")
        
    def import_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Audio",
            "", "Audio Files (*.wav *.mp3 *.ogg)"
        )
        if file_path:
            self.name_label.setText(os.path.splitext(os.path.basename(file_path))[0])
            # Default to start at frame 0
            self.clip_import_requested.emit(self.track_id, file_path, 0)