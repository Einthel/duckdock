"""
Модульные тесты индивидуального звука клика и предпрослушки DuckDeck (DeckSoundEngine).
Проверяют DeckSoundEngine (preview_sound, stop_preview, is_preview_playing, play_tap с sound_override).
"""
import struct
import pytest
from PySide6.QtWidgets import QApplication

from modules.deck.sound_engine import DeckSoundEngine


def _create_valid_wav(path):
    """Генерирует валидный минимальный 44-байтный WAV PCM файл для тестов."""
    num_samples = 100
    data = b"\x00" * (num_samples * 2)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(data),
        b"WAVE",
        b"fmt ",
        16,
        1,       # PCM
        1,       # 1 channel
        8000,    # sample rate
        16000,   # byte rate
        2,       # block align
        16,      # bits per sample
        b"data",
        len(data),
    )
    with open(path, "wb") as f:
        f.write(header + data)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_sound_engine_preview(qapp, tmp_path):
    """Проверка предпрослушки (preview_sound, stop_preview, is_preview_playing)."""
    test_wav = tmp_path / "preview.wav"
    _create_valid_wav(str(test_wav))
    file_path = str(test_wav)

    engine = DeckSoundEngine()
    engine.stop_preview()
    assert engine.is_preview_playing() is False

    started = engine.preview_sound(file_path, volume=0.5)
    assert started is True
    assert engine.is_preview_playing() is True

    engine.stop_preview()
    assert engine.is_preview_playing() is False


def test_sound_engine_tap_sound_override(qapp, tmp_path, monkeypatch):
    """Проверка флага sound_override в методе play_tap."""
    engine = DeckSoundEngine()
    engine._sound_enabled = True

    played_effects = []

    # 1. sound_override == "muted" -> звук не должен воспроизводиться
    played_effects.clear()
    engine.play_tap(sound_override="muted")
    assert len(played_effects) == 0

    # 2. sound_override == None -> воспроизводится дефолтный звук тапа
    played_effects.clear()
    tap_eff = engine.get_effect("tap")
    if tap_eff:
        monkeypatch.setattr(tap_eff, "play", lambda: played_effects.append("tap"))
        engine.play_tap(sound_override=None)
        assert "tap" in played_effects

    # 3. sound_override == "custom.wav"
    test_wav = tmp_path / "custom.wav"
    _create_valid_wav(str(test_wav))
    played_effects.clear()
    engine.play_tap(sound_override=str(test_wav))
    # Кастомный эффект создан и закэширован
    assert engine.get_effect(str(test_wav)) is not None
