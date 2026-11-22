"""
Модульные тесты саундборда и индивидуального звука клика DuckDeck (Спринт 7.2).
Проверяют DeckSoundEngine (soundboard pool до 8 звуков, stop_soundboard, preview, sound_override),
SoundboardSubform и диспетчеризацию play_audio/stop_audio.
"""
import os
import struct
import pytest
from PySide6.QtWidgets import QApplication

from modules.deck.action_dispatcher import (
    ActionRunnable,
    DeckActionDispatcher,
    WorkerSignals,
)
from modules.deck.editor.widgets.button_property_form import SoundboardSubform
from modules.deck.models import DeckActionConfig, SoundboardParams
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


def test_sound_engine_soundboard_pool_limit(qapp, tmp_path):
    """Проверка пула воспроизведения саундборда (до 8 эффектов с авто-очисткой)."""
    test_wav = tmp_path / "sound.wav"
    _create_valid_wav(str(test_wav))
    file_path = str(test_wav)

    engine = DeckSoundEngine()
    engine._sound_enabled = True

    # Запускаем 10 звуков подряд
    for _ in range(10):
        engine.play_soundboard(file_path, volume=0.5, stop_others=False)

    # Пул должен быть ограничен 8 элементами
    assert len(engine._soundboard_pool) <= 8

    # Остановка саундборда
    engine.stop_soundboard()
    assert len(engine._soundboard_pool) == 0


def test_sound_engine_stop_others(qapp, tmp_path):
    """Проверка флага stop_others=True для остановки предыдущих звуков саундборда."""
    test_wav = tmp_path / "sound.wav"
    _create_valid_wav(str(test_wav))
    file_path = str(test_wav)

    engine = DeckSoundEngine()
    engine._sound_enabled = True

    engine.play_soundboard(file_path, volume=0.8, stop_others=False)
    engine.play_soundboard(file_path, volume=0.8, stop_others=False)
    assert len(engine._soundboard_pool) >= 2

    # Запуск с stop_others=True
    engine.play_soundboard(file_path, volume=0.8, stop_others=True)
    assert len(engine._soundboard_pool) == 1

    engine.stop_soundboard()


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


def test_soundboard_subform_ui(qapp, tmp_path):
    """Проверка подформы параметров саундборда SoundboardSubform."""
    subform = SoundboardSubform()

    received = []
    subform.params_changed.connect(lambda p: received.append(p))

    subform.set_params({"file_path": "C:/sounds/effect.wav", "volume": 0.75})
    assert subform.get_params()["file_path"] == "C:/sounds/effect.wav"
    assert subform.get_params()["volume"] == 0.75
    assert subform.slider_vol.value() == 75
    assert subform.lbl_vol_val.text() == "75%"

    # Изменение пути
    subform.edit_sound_path.setText("D:/sounds/fanfare.wav")
    subform.edit_sound_path.textEdited.emit("D:/sounds/fanfare.wav")
    assert len(received) > 0
    assert received[-1]["file_path"] == "D:/sounds/fanfare.wav"

    # Изменение громкости
    subform.slider_vol.setValue(50)
    assert received[-1]["volume"] == 0.5


def test_action_dispatcher_soundboard_actions(qapp, tmp_path):
    """Проверка диспетчеризации действий play_audio и stop_audio через сигналы."""
    test_wav = tmp_path / "action.wav"
    _create_valid_wav(str(test_wav))

    action_cfg = DeckActionConfig(
        action_type="play_audio",
        params={"file_path": str(test_wav), "volume": 0.6, "stop_others": True},
    )

    signals = WorkerSignals()
    runnable = ActionRunnable(button_id="btn_1", action_config=action_cfg, signals=signals)
    play_signals = []
    signals.play_sound_requested.connect(
        lambda p, v, s: play_signals.append((p, v, s))
    )
    runnable.run()

    assert len(play_signals) == 1
    assert play_signals[0] == (str(test_wav), 0.6, True)

    # Проверка stop_audio
    stop_cfg = DeckActionConfig(action_type="stop_audio")
    stop_signals_obj = WorkerSignals()
    stop_runnable = ActionRunnable(button_id="btn_2", action_config=stop_cfg, signals=stop_signals_obj)
    stop_signals = []
    stop_signals_obj.stop_sound_requested.connect(lambda: stop_signals.append(True))
    stop_runnable.run()

    assert len(stop_signals) == 1
