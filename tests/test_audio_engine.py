from soundbyte.audio.engine import AudioEngine

def test_add_track():
    engine = AudioEngine()
    track_id = engine.add_track("test.wav")
    assert track_id is not None
    assert track_id in engine.tracks

def test_playback():
    engine = AudioEngine()
    track_id = engine.add_track("test.wav")
    engine.play()
    assert engine.playing
    engine.stop()
    assert not engine.playing