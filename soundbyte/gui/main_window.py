from PyQt6.QtWidgets import (QMainWindow,   QWidget, QVBoxLayout, QPushButton, QHBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from audio.engine import AudioEngine

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SoundByte")
        self.setGeometry(100, 100, 800, 600)
        
        # Initialize audio engine
        self.audio_engine = AudioEngine()
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add transport controls
        transport_layout = QHBoxLayout()
        play_button = QPushButton("Play")
        stop_button = QPushButton("Stop")
        pause_button = QPushButton("Pause")
        
        play_button.clicked.connect(self.audio_engine.play)
        stop_button.clicked.connect(self.audio_engine.stop)
        pause_button.clicked.connect(self.audio_engine.pause)
        
        transport_layout.addWidget(play_button)
        transport_layout.addWidget(stop_button)
        transport_layout.addWidget(pause_button)
        layout.addLayout(transport_layout)
        
        # Add menu bar
        self.create_menu_bar()
    
    def create_menu_bar(self):
        """Create and setup the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New Project", self)
        new_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open Project", self)
        open_action.setShortcut("Ctrl+O")
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save Project", self)
        save_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("&Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        edit_menu.addAction(redo_action)