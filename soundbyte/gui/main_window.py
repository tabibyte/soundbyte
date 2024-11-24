from core.audio_engine import AudioEngine
from PyQt6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QSlider, QDial, QLabel, QComboBox, QGroupBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
import pyqtgraph as pg
import numpy as np

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SoundByte")
        self.setGeometry(100, 100, 800, 600)
        
        self.audio_engine = AudioEngine()
        self.setup_ui()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Transport controls group
        transport_layout = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.stop_button = QPushButton("Stop")
        self.play_button.setFixedSize(60, 60)
        self.stop_button.setFixedSize(60, 60)
        self.play_button.clicked.connect(self.on_play)
        self.stop_button.clicked.connect(self.on_stop)
        transport_layout.addWidget(self.play_button)
        transport_layout.addWidget(self.stop_button)
        transport_layout.addStretch()
        main_layout.addLayout(transport_layout)
        
        self.loop_button = QPushButton("Loop")
        self.loop_button.setCheckable(True)
        self.loop_button.setChecked(True)
        self.loop_button.clicked.connect(self.on_loop_toggle)
        transport_layout.addWidget(self.loop_button)
        
        # Controls group
        controls_layout = QHBoxLayout()
        
        # Volume control
        volume_layout = QVBoxLayout()
        volume_label = QLabel("Volume")
        self.volume_slider = QSlider(Qt.Orientation.Vertical)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.on_volume_change)
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        controls_layout.addLayout(volume_layout)
        
        # Frequency control
        freq_layout = QVBoxLayout()
        freq_label = QLabel("Frequency")
        self.freq_dial = QDial()
        self.freq_dial.setRange(20, 2000)
        self.freq_dial.setValue(440)
        self.freq_value = QLabel("440 Hz")
        self.freq_dial.valueChanged.connect(self.on_frequency_change)
        freq_layout.addWidget(freq_label)
        freq_layout.addWidget(self.freq_dial)
        freq_layout.addWidget(self.freq_value)
        controls_layout.addLayout(freq_layout)
        
        # Add controls to main layout
        main_layout.addLayout(controls_layout)
        main_layout.addStretch()
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Initial button states
        self.stop_button.setEnabled(False)

        # Oscillator type selector
        osc_layout = QVBoxLayout()
        osc_label = QLabel("Oscillator")
        self.osc_type = QComboBox()
        self.osc_type.addItems(["Sine", "Square", "Sawtooth", "Triangle"])
        self.osc_type.currentTextChanged.connect(self.on_osc_type_change)
        osc_layout.addWidget(osc_label)
        osc_layout.addWidget(self.osc_type)
        controls_layout.addLayout(osc_layout)

        # Waveform display
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_curve = self.plot_widget.plot(pen='b')
        main_layout.addWidget(self.plot_widget)

        # Output device selector
        device_layout = QHBoxLayout()
        device_label = QLabel("Output Device:")
        self.device_selector = QComboBox()
        self.populate_audio_devices()
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_selector)
        main_layout.addLayout(device_layout)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Space"), self, self.toggle_playback)
        QShortcut(QKeySequence("Escape"), self, self.on_stop)

        # Setup waveform update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_waveform)
        self.update_timer.start(50)  # 50ms refresh rate
    
    def populate_audio_devices(self):
        devices = self.audio_engine.pa.get_device_count()
        for i in range(devices):
            device_info = self.audio_engine.pa.get_device_info_by_index(i)
            if device_info['maxOutputChannels'] > 0:
                self.device_selector.addItem(device_info['name'], i)

    def on_loop_toggle(self, checked):
        self.audio_engine.set_looping(checked)
    def toggle_playback(self):
        if self.audio_engine.is_playing:
            self.on_stop()
        else:
            self.on_play()

    def on_osc_type_change(self, type_name):
        self.audio_engine.set_oscillator_type(type_name.lower())

    def update_waveform(self):
        if self.audio_engine.is_playing:
            # Get current waveform data
            t = np.linspace(0, 0.01, 1000)
            data = self.audio_engine.generate_waveform(t)
            self.plot_curve.setData(t, data)
            
    def on_play(self):
        self.audio_engine.start()
        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def on_stop(self):
        self.audio_engine.stop()
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
    def on_volume_change(self, value):
        self.audio_engine.set_volume(value / 100.0)
        
    def on_frequency_change(self, value):
        self.freq_value.setText(f"{value} Hz")
        self.audio_engine.set_frequency(float(value))