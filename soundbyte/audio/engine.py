import sounddevice as sd
import soundfile as sf
import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass
from threading import Lock

@dataclass
class AudioTrack:
    data: np.ndarray
    sample_rate: int
    name: str
    muted: bool = False
    solo: bool = False
    volume: float = 1.0

class AudioEngine:
    def __init__(self, sample_rate=44100, channels=2, buffer_size=1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer_size = buffer_size
        self.tracks: Dict[int, AudioTrack] = {}
        self.playing = False
        self.current_frame = 0
        self.lock = Lock()
        
        # Initialize audio stream
        self.stream = sd.OutputStream(
            samplerate=sample_rate,
            channels=channels,
            callback=self._audio_callback,
            blocksize=buffer_size
        )
    
    def add_track(self, file_path: str, name: Optional[str] = None) -> int:
        """Add new audio track from file"""
        data, sr = sf.read(file_path)
        if sr != self.sample_rate:
            # TODO: implement resampling
            pass
            
        # Convert mono to stereo if needed
        if len(data.shape) == 1:
            data = np.column_stack((data, data))
            
        track_id = len(self.tracks)
        self.tracks[track_id] = AudioTrack(
            data=data,
            sample_rate=sr,
            name=name or f"Track {track_id}"
        )
        return track_id
    
    def play(self):
        """Start playback"""
        if not self.playing:
            self.stream.start()
            self.playing = True
    
    def stop(self):
        """Stop playback"""
        if self.playing:
            self.stream.stop()
            self.playing = False
            self.current_frame = 0
    
    def pause(self):
        """Pause playback"""
        if self.playing:
            self.stream.stop()
            self.playing = False
    
    def _audio_callback(self, outdata, frames, time, status):
        """Audio callback for sounddevice"""
        if status:
            print(status)
            
        with self.lock:
            # Mix all active tracks
            mixed = np.zeros((frames, self.channels))
            
            for track in self.tracks.values():
                if track.muted or (any(t.solo for t in self.tracks.values()) and not track.solo):
                    continue
                    
                if self.current_frame < len(track.data):
                    end_frame = min(self.current_frame + frames, len(track.data))
                    chunk = track.data[self.current_frame:end_frame]
                    
                    # Pad with zeros if chunk is smaller than buffer
                    if len(chunk) < frames:
                        chunk = np.pad(chunk, ((0, frames - len(chunk)), (0, 0)))
                        
                    mixed += chunk * track.volume
            
            # Prevent clipping
            if np.max(np.abs(mixed)) > 1.0:
                mixed /= np.max(np.abs(mixed))
                
            outdata[:] = mixed
            self.current_frame += frames