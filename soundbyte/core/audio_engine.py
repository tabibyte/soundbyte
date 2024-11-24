from core import constants
import pyaudio
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, Any, List
from collections import deque

@dataclass
class EnvelopeSettings:
    attack: float = 0.1
    decay: float = 0.1
    sustain: float = 0.7
    release: float = 0.2

class AudioEngine:
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.is_playing = False
        self.is_looping = True
        
        # ADSR envelope settings
        self.attack = 0.1  # seconds
        self.decay = 0.1
        self.sustain = 0.7  # level 0-1
        self.release = 0.2
        self.envelope_phase = 0.0
        self.note_on = False
        
        # Audio settings from constants
        self.sample_rate = constants.SAMPLE_RATE
        self.channels = constants.CHANNELS
        self.chunk_size = constants.CHUNK_SIZE
        
        # Phase accumulator for basic sine test tone
        self.phase = 0.0
        self.volume = 0.5
        self.frequency = 440.0  # A4 note
        self.osc_type = "sine"

        # Buffer settings
        self.buffer_size = 2048
        self.audio_buffer = deque(maxlen=self.buffer_size)
        
        # Metering
        self.peak_level = 0.0
        self.rms_level = 0.0
        
        # Envelope
        self.envelope = EnvelopeSettings()
        self.envelope_phase = 0.0
        self.note_on = False
        
    def set_looping(self, loop: bool) -> None:
        """Enable/disable looping playback"""
        self.is_looping = loop
        
    def audio_callback(self, in_data: Any, 
                      frame_count: int,
                      time_info: dict,
                      status: int) -> Tuple[bytes, int]:
        if self.is_playing:
            # Generate test sine wave
            t = np.arange(frame_count) / self.sample_rate + self.phase
            data = np.sin(2 * np.pi * self.frequency * t)
            
            # Update phase for continuity
            self.phase = t[-1] + 1/self.sample_rate
            
            # Convert to stereo and float32
            data = np.tile(data, (self.channels, 1)).T
            return (data.astype(np.float32).tobytes(), pyaudio.paContinue)
        
        return (np.zeros(frame_count * self.channels, dtype=np.float32).tobytes(), 
                pyaudio.paComplete)
    
    def set_oscillator_type(self, osc_type: str) -> None:
        """Set oscillator type (sine, square, sawtooth, triangle)"""
        if osc_type in ["sine", "square", "sawtooth", "triangle"]:
            self.osc_type = osc_type
        
    def generate_waveform(self, t: np.ndarray) -> np.ndarray:
        if self.osc_type == "sine":
            return np.sin(2 * np.pi * self.frequency * t) * self.volume
        elif self.osc_type == "square":
            return np.sign(np.sin(2 * np.pi * self.frequency * t)) * self.volume
        elif self.osc_type == "sawtooth":
            return ((2 * self.frequency * t) % 2 - 1) * self.volume
        elif self.osc_type == "triangle":
            return (2 * abs(2 * (self.frequency * t % 1) - 1) - 1) * self.volume
           
    def start(self):
        """Start audio playback"""
        if not self.stream:
            self.stream = self.pa.open(
                format=pyaudio.paFloat32,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self.audio_callback
            )
        self.is_playing = True
        self.stream.start_stream()

    def note_on_event(self):
        """Trigger note on"""
        self.note_on = True
        self.envelope_phase = 0.0
        
    def note_off_event(self):
        """Trigger note off"""
        self.note_on = False
        
    def get_envelope(self, t):
        """Calculate ADSR envelope value"""
        if not self.note_on:
            return max(0, self.sustain - (t / self.release))
            
        if t < self.attack:
            return t / self.attack
        t -= self.attack
        
        if t < self.decay:
            return 1.0 - (1.0 - self.sustain) * (t / self.decay)
        return self.sustain
    
    def stop(self):
        """Stop audio playback"""
        self.is_playing = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def __del__(self):
        """Cleanup resources"""
        self.stop()
        if self.pa:
            self.pa.terminate()
            
    def set_volume(self, value: float) -> None:
        """Set volume between 0.0 and 1.0"""
        self.volume = max(0.0, min(1.0, value))
        
    def set_frequency(self, value: float) -> None:
        """Set frequency in Hz"""
        self.frequency = max(20.0, min(20000.0, value))
    
    def audio_callback(self, in_data: Any, 
                      frame_count: int,
                      time_info: dict,
                      status: int) -> Tuple[bytes, int]:
        try:
            if self.is_playing:
                # Generate waveform
                t = np.arange(frame_count) / self.sample_rate + self.phase
                data = self.generate_waveform(t)
                
                # Apply envelope
                env = self._calculate_envelope(t)
                data *= env
                
                # Update buffer and measurements
                self._update_buffer(data)
                self._update_meters(data)
                
                # Update phase and handle looping
                self.phase = t[-1] + 1/self.sample_rate
                
                # Return appropriate status based on looping
                return (np.tile(data, (self.channels, 1)).T.astype(np.float32).tobytes(),
                       pyaudio.paContinue if self.is_looping else pyaudio.paComplete)
        except BufferError as be:
            print(f"Buffer underrun: {be}")
            return (self._generate_silence(frame_count), pyaudio.paContinue)
        except Exception as e:
            print(f"Critical error in audio callback: {e}")
            self.stop()
            
        return (self._generate_silence(frame_count), pyaudio.paComplete)

    def _calculate_envelope(self, t: np.ndarray) -> np.ndarray:
        """Calculate ADSR envelope values for given time points"""
        if not self.note_on:
            return np.exp(-t / self.envelope.release) * self.envelope.sustain
            
        mask_a = t < self.envelope.attack
        mask_d = (t >= self.envelope.attack) & (t < (self.envelope.attack + self.envelope.decay))
        
        env = np.ones_like(t) * self.envelope.sustain
        env[mask_a] = t[mask_a] / self.envelope.attack
        env[mask_d] = 1.0 - (1.0 - self.envelope.sustain) * \
                     ((t[mask_d] - self.envelope.attack) / self.envelope.decay)
        return env
        
    def _update_buffer(self, data: np.ndarray) -> None:
        """Update circular audio buffer"""
        self.audio_buffer.extend(data)
        
    def _update_meters(self, data: np.ndarray) -> None:
        """Update audio meters"""
        self.peak_level = max(np.abs(data))
        self.rms_level = np.sqrt(np.mean(data ** 2))
        
    def _generate_silence(self, frame_count: int) -> bytes:
        """Generate silence in case of errors"""
        return np.zeros(frame_count * self.channels, dtype=np.float32).tobytes()