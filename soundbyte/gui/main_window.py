from PyQt6.QtWidgets import (QMainWindow,   QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QListWidget, QFileDialog, QMessageBox, QScrollArea, QSlider, QSplitter)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction
from audio.engine import AudioEngine
import json
import os
from pathlib import Path
import soundfile as sf
from commands.base import Command
from commands.track_commands import AddTrackCommand
from .timeline_widget import TimelineWidget
from .track_widget import TrackWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SoundByte")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize core components
        self.undo_stack = []
        self.redo_stack = []
        self.audio_engine = AudioEngine()
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Transport controls at top
        transport_widget = QWidget()
        transport_widget.setFixedHeight(32)
        transport_widget.setStyleSheet("""
        QWidget {
            background-color: #282828;
            min-height: 32px;
            max-height: 32px;
        }
        """)
        transport_layout = QHBoxLayout(transport_widget)
        transport_layout.setContentsMargins(4, 0, 4, 0)
        transport_layout.setSpacing(2)
        
        self.play_button = QPushButton("▶")
        self.stop_button = QPushButton("■")
        self.pause_button = QPushButton("❚❚")
        
        for btn in [self.play_button, self.stop_button, self.pause_button]:
            btn.setFixedSize(32, 32)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #383838;
                    border: none;
                    color: #ddd;
                    border-radius: 4px;
                }
                QPushButton:hover { background-color: #404040; }
                QPushButton:pressed { background-color: #505050; }
                QPushButton:disabled { color: #666; }
            """)
        
        self.play_button.clicked.connect(self.play)
        self.stop_button.clicked.connect(self.stop)
        self.pause_button.clicked.connect(self.pause)
        
        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        
        transport_layout.addWidget(self.play_button)
        transport_layout.addWidget(self.stop_button)
        transport_layout.addWidget(self.pause_button)
        
        # Time display
        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet("color: #ddd; font-family: monospace; font-size: 14px;")
        transport_layout.addWidget(self.time_label)
        
        # Seek slider
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #383838;
                height: 4px;
            }
            QSlider::handle:horizontal {
                background: #ddd;
                width: 12px;
                margin: -4px 0;
            }
        """)
        self.seek_slider.setRange(0, 100)
        self.seek_slider.valueChanged.connect(self.seek_changed)
        transport_layout.addWidget(self.seek_slider)
        transport_layout.addStretch()
        
        main_layout.addWidget(transport_widget)
        
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #383838;
            }
        """)
        
        # Tracks panel (left side)
        tracks_panel = QWidget()
        tracks_panel.setStyleSheet("background-color: #282828;")
        self.tracks_layout = QVBoxLayout(tracks_panel)
        self.tracks_layout.setSpacing(0)
        self.tracks_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add track button
        add_track_btn = QPushButton("+ Add Track")
        add_track_btn.setStyleSheet("""
            QPushButton {
                background-color: #383838;
                border: none;
                color: #ddd;
                padding: 8px;
                text-align: left;
            }
            QPushButton:hover { background-color: #404040; }
        """)
        add_track_btn.clicked.connect(self.add_track)
        self.tracks_layout.addWidget(add_track_btn)
        self.tracks_layout.addStretch()
        
        # Sequencer/Timeline panel (right side)
        sequencer_panel = QWidget()
        sequencer_panel.setStyleSheet("background-color: #1e1e1e;")
        sequencer_layout = QVBoxLayout(sequencer_panel)
        sequencer_layout.setContentsMargins(0, 0, 0, 0)
        
        self.timeline = TimelineWidget()
        sequencer_layout.addWidget(self.timeline)
        
        # Add both panels to splitter
        splitter.addWidget(tracks_panel)
        splitter.addWidget(sequencer_panel)
        splitter.setSizes([300, 900])  # Initial split ratio
        
        main_layout.addWidget(splitter)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time_display)
        self.timer.start(100)  # Update every 100ms
        
        self.current_project_path = None
        self.project_modified = False
    
        def connect_track_signals(track_widget):
            track_widget.clip_import_requested.connect(self.timeline.set_pending_clip)
    
        def add_track(self):
            track_id = len(self.tracks_layout)
            track_widget = TrackWidget(track_id, self.audio_engine)
            connect_track_signals(track_widget)
            self.tracks_layout.addWidget(track_widget)
        
    def create_menu_bar(self):
        """Create and setup the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New Project", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open Project", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save Project", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("&Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        edit_menu.addAction(redo_action)
    
        undo_action.triggered.connect(self.undo)
        redo_action.triggered.connect(self.redo)

    def closeEvent(self, event):
        if self.project_modified:
            reply = QMessageBox.question(
                self, 'Save Changes?',
                'Do you want to save changes before closing?',
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self.save_project()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        event.accept()
     
    def add_track(self):
        track_id = len(self.tracks_layout)
        track_widget = TrackWidget(track_id, self.audio_engine)
        self.tracks_layout.addWidget(track_widget)
    
    def update_playhead(self):
        if self.audio_engine.playing:
            self.timeline.playhead_pos = (
                self.audio_engine.current_frame / 
                self.audio_engine.sample_rate
            )
            self.timeline.update()
            
    def seek_changed(self, value):
        frame = int((value / 100.0) * self.audio_engine.get_total_frames())
        self.audio_engine.seek(frame)
         
    def update_time_display(self):
        self.timeline.current_position = self.audio_engine.current_frame
        self.timeline.update()
        
        if self.audio_engine.playing:
            seconds = self.audio_engine.current_frame / self.audio_engine.sample_rate
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = int(seconds % 60)
            self.time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
            # Check if playback finished
            if self.audio_engine.current_frame >= max(len(track.data) for track in self.audio_engine.tracks.values()):
                self.stop()
    
    def clear_tracks(self):
        """Clear all tracks from layout"""
        while self.tracks_layout.count():
            item = self.tracks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                        
    def new_project(self):
        if self.project_modified:
            reply = QMessageBox.question(
                self, 'Save Changes?',
                'Do you want to save changes to the current project?',
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self.save_project()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        self.audio_engine.stop()
        self.audio_engine = AudioEngine()
        self.clear_tracks()
        self.current_project_path = None
        self.project_modified = False
        self.setWindowTitle("SoundByte - New Project")

    def open_project(self):
        if self.project_modified:
            reply = QMessageBox.question(
                self, 'Save Changes?',
                'Do you want to save changes to the current project?',
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_project():
                    return  # Don't proceed if save failed
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            "SoundByte Project (*.sbp);;All Files (*.*)"
        )
        
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    project_data = json.load(f)
                
                self.audio_engine.stop()
                self.audio_engine = AudioEngine(
                    sample_rate=project_data.get('sample_rate', 44100)
                )
                
                self.track_list.clear()
                
                project_dir = os.path.dirname(file_name)
                load_success = True

                for track in project_data['tracks']:
                    track_path = os.path.join(project_dir, track['file'])
                    if os.path.exists(track_path):
                        try:
                            track_id = self.audio_engine.add_track(
                                track_path,
                                track['name']
                            )
                            self.track_list.addItem(track['name'])
                            
                            audio_track = self.audio_engine.tracks[track_id]
                            audio_track.volume = track['volume']
                            audio_track.muted = track['muted']
                            audio_track.solo = track['solo']
                        except Exception as e:
                            QMessageBox.warning(
                                self,
                                "Track Load Warning",
                                f"Failed to load track {track['name']}: {str(e)}"
                            )
                            load_success = False
                    else:
                        QMessageBox.warning(
                            self,
                            "Track Load Warning",
                            f"Track file not found: {track['file']}"
                        )
                        load_success = False
                
                self.current_project_path = file_name
                self.project_modified = False
                self.setWindowTitle(f"SoundByte - {os.path.basename(file_name)}")
                
                # Update transport controls after loading
                self.update_transport_controls()
                
                if not load_success:
                    QMessageBox.warning(
                        self,
                        "Project Load Warning",
                        "Some tracks could not be loaded. Check file paths and permissions."
                    )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to load project: {str(e)}"
                )
    
    def update_transport_controls(self):
        """Update transport button states based on playback state"""
        has_tracks = bool(self.audio_engine.tracks)
        is_playing = self.audio_engine.playing
        
        # Update button states
        self.play_button.setEnabled(has_tracks and not is_playing)
        self.stop_button.setEnabled(is_playing)
        self.pause_button.setEnabled(is_playing)
        
        # Update seek position
        if self.audio_engine.get_total_frames() > 0:
            position = (self.audio_engine.current_frame / 
                    self.audio_engine.get_total_frames()) * 100
            self.seek_slider.setValue(int(position))

    def play(self):
        if self.audio_engine.tracks:
            self.audio_engine.play()
            self.update_transport_controls()

    def stop(self):
        self.audio_engine.stop()
        self.update_transport_controls()
        self.time_label.setText("00:00:00")

    def pause(self):
        self.audio_engine.pause()
        self.update_transport_controls()
    
    def save_project(self):
        if not self.current_project_path:
            return self.save_project_as()
            
        try:
            project_dir = os.path.dirname(self.current_project_path)
            
            project_data = {
                'version': '1.0',
                'sample_rate': self.audio_engine.sample_rate,
                'tracks': []
            }
            
            for track_id, track in self.audio_engine.tracks.items():
                track_filename = f"track_{track_id}.wav"
                track_path = os.path.join(project_dir, track_filename)
                sf.write(track_path, track.data, track.sample_rate)
                
                track_data = {
                    'name': track.name,
                    'file': track_filename,
                    'volume': track.volume,
                    'muted': track.muted,
                    'solo': track.solo
                }
                project_data['tracks'].append(track_data)
            
            with open(self.current_project_path, 'w') as f:
                json.dump(project_data, f, indent=4)
                
            self.project_modified = False
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save project: {str(e)}"
            )
            return False
        return True

    def save_project_as(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            "",
            "SoundByte Project (*.sbp);;All Files (*.*)"
        )
        
        if file_name:
            if not file_name.endswith('.sbp'):
                file_name += '.sbp'
            
            self.current_project_path = file_name
            if self.save_project():
                self.setWindowTitle(f"SoundByte - {os.path.basename(file_name)}")
                return True
        return False

    def undo(self):
        if self.undo_stack:
            command = self.undo_stack.pop()
            command.undo()
            self.redo_stack.append(command)
            self.mark_project_modified()
    
    def redo(self):
        if self.redo_stack:
            command = self.redo_stack.pop()
            command.execute()
            self.undo_stack.append(command)
            self.mark_project_modified()
    
    def update_edit_actions(self):
        if hasattr(self, 'undo_action'):
            self.undo_action.setEnabled(bool(self.undo_stack))
        if hasattr(self, 'redo_action'):
            self.redo_action.setEnabled(bool(self.redo_stack))
    
    def mark_project_modified(self):
        """Call this whenever project state changes"""
        self.project_modified = True
        if self.current_project_path:
            self.setWindowTitle(f"SoundByte - {os.path.basename(self.current_project_path)}*")
        else:
            self.setWindowTitle("SoundByte - New Project*")
            
    def zoom_in(self):
        self.timeline.zoom_level *= 1.2
        self.timeline.update()
        
    def zoom_out(self):
        self.timeline.zoom_level /= 1.2
        self.timeline.update()

    def autosave_project(self):
        if self.current_project_path and self.project_modified:
            self.save_project()
        
    def add_clip_to_timeline(self, track_id, start_time, audio_data):
        if track_id not in self.timeline.clips:
            self.timeline.clips[track_id] = []
            
        duration = len(audio_data) / self.audio_engine.sample_rate
        clip = (start_time, start_time + duration, audio_data)
        self.timeline.clips[track_id].append(clip)
        self.timeline.update()