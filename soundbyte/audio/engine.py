import sounddevice as sd
import soundfile as sf
import numpy as np
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from threading import Lock
import os

@dataclass
class AudioClip:
    data: np.ndarray
    start_frame: int
    length: int
    track_id: int
    name: str = ""

@dataclass 
class AudioTrack:
    data: np.ndarray
    sample_rate: int
    name: str
    clips: List[AudioClip]
    muted: bool = False
    solo: bool = False
    volume: float = 1.0

class AudioEngine:
    def __init__(self, sample_rate=44100, channels=2, buffer_size=1024):
        print(f"Initializing AudioEngine with {sample_rate}Hz")  # Debug
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer_size = buffer_size
        self.tracks = {}
        self.current_frame = 0
        self.playing = False
        self.lock = Lock()
        
        try:
            self.stream = sd.OutputStream(
                channels=channels,
                samplerate=sample_rate,
                blocksize=buffer_size,
                callback=self._audio_callback
            )
            print("Audio stream created successfully")  # Debug
        except Exception as e:
            print(f"Failed to create audio stream: {e}")
            raise

    def play(self):
        print("Play requested")  # Debug
        with self.lock:
            if not self.tracks:
                print("No tracks to play")
                return
                
            print(f"Starting playback at frame {self.current_frame}")
            self.playing = True
            self.stream.start()

    def stop(self):
        """Stop audio playback and reset position"""
        with self.lock:
            self.playing = False
            self.stream.stop()
            self.current_frame = 0

    def pause(self):
        """Pause audio playback"""
        with self.lock:
            self.playing = False
            self.stream.stop()
              
    def add_track(self, file_path: str, name: str = "") -> int:
        """
        Add a new audio track from file
        
        Args:
            file_path: Path to audio file
            name: Optional track name
        
        Returns:
            track_id: Unique ID for the new track
        """
        print(f"Loading track from {file_path}")  # Debug
        data, sr = sf.read(file_path)
        print(f"Loaded audio: {data.shape}, {sr}Hz")  # Debug
        
        if data.dtype != np.float32:
            data = np.memmap(file_path, dtype='float32', mode='r')
        if len(data.shape) == 1:
            data = np.column_stack((data, data))
            
        track_id = max(self.tracks.keys(), default=-1) + 1
        self.tracks[track_id] = AudioTrack(
            data=data,
            sample_rate=sr,
            name=name or os.path.basename(file_path),
            clips=[]
        )
        return track_id

    def set_track_volume(self, track_id: int, volume: float):
        """Set volume for a track (0.0 to 1.0)"""
        if track_id in self.tracks:
            self.tracks[track_id].volume = max(0.0, min(1.0, volume))

    def set_track_mute(self, track_id: int, muted: bool):
        """Mute/unmute a track"""
        if track_id in self.tracks:
            self.tracks[track_id].muted = muted
            # Unsolo if muting
            if muted:
                self.tracks[track_id].solo = False

    def set_track_solo(self, track_id: int, solo: bool):
        """Solo/unsolo a track"""
        if track_id in self.tracks:
            self.tracks[track_id].solo = solo
            # Unmute if soloing
            if solo:
                self.tracks[track_id].muted = False

    def seek(self, frame: int):
        """Seek to specific frame"""
        with self.lock:
            self.current_frame = max(0, min(frame, self.get_total_frames()))

    def get_total_frames(self) -> int:
        """Get total length in frames"""
        if not self.tracks:
            return 0
        return max(len(track.data) for track in self.tracks.values())
    
    def add_clip(self, track_id: int, file_path: str, start_frame: int = 0):
        """Add audio clip to track at specified position"""
        if track_id in self.tracks:
            try:
                data, sr = sf.read(file_path)
                if data.dtype != np.float32:
                    data = data.astype(np.float32)
                if len(data.shape) == 1:  # Mono to stereo
                    data = np.column_stack((data, data))
                    
                clip = AudioClip(
                    data=data,
                    start_frame=start_frame,
                    length=len(data),
                    track_id=track_id,
                    name=os.path.basename(file_path)
                )
                self.tracks[track_id].clips.append(clip)
                return True
            except Exception as e:
                print(f"Failed to load audio: {e}")
                return False
        return False
        
    def move_clip(self, track_id: int, clip_index: int, new_start: int):
        """Move a clip to a new position"""
        if track_id in self.tracks and clip_index < len(self.tracks[track_id].clips):
            self.tracks[track_id].clips[clip_index].start_frame = new_start

    def remove_clip(self, track_id: int, clip_index: int):
            """Remove a clip from a track"""
            if track_id in self.tracks and clip_index < len(self.tracks[track_id].clips):
                self.tracks[track_id].clips.pop(clip_index)
                
    def _audio_callback(self, outdata, frames, time, status):
        if status:
            print(f"Audio callback status: {status}")
            
        with self.lock:
            if not self.playing:
                outdata.fill(0)
                return
                
            mixed = np.zeros((frames, self.channels), dtype=np.float32)
            
            for track in self.tracks.values():
                if track.muted:
                    continue
                    
                chunk_start = self.current_frame
                chunk_end = chunk_start + frames
                
                if chunk_start < len(track.data):
                    chunk = track.data[chunk_start:chunk_end]
                    if len(chunk) < frames:
                        chunk = np.pad(chunk, ((0, frames - len(chunk)), (0, 0)))
                    mixed += chunk * track.volume
            
            if np.max(np.abs(mixed)) > 1.0:
                mixed /= np.max(np.abs(mixed))
                
            outdata[:] = mixed
            self.current_frame += frames