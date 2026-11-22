"""
Модульные тесты для звукового движка DuckDeck (DeckSoundEngine) - Шаг 4.2.
Проверяют:
1. Предзагрузку WAV-семплов (button_click, button_sw_page, button_offline) в RAM.
2. Управление громкостью (0.0..1.0) и флагом enabled из SoundSettings.
3. Воспроизведение звуков клика (с поддержкой sound_override), смены страницы, ошибок.
4. Интеграцию DeckSoundEngine с DeckView (клик, свайп/пагинация, ошибка экшена).
5. Работу Re-export Shim core.deck.sound_engine.
6. Безопасность при отсутствии файлов и корректность cleanup().
"""
import os
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtMultimedia import QSoundEffect

from modules.deck.models import DeckActionConfig, DeckButtonConfig, SoundSettings
from modules.deck.sound_engine import DeckSoundEngine


def test_deck_sound_engine_initialization_and_preloading(qapp):
    """
    Проверка инициализации DeckSoundEngine и предзагрузки семплов в RAM:
    - button_click.wav (tap)
    - button_sw_page.wav (page_switch)
    - button_offline.wav (error)
    - button_online.wav (success)
    - Корректность начальной громкости и флага enabled.
    """
    settings = SoundSettings(
        enabled=True,
        volume=0.75,
        default_tap_sound="resources/deck/sounds/button_click.wav",
        page_switch_sound="resources/deck/sounds/button_sw_page.wav",
        error_sound="resources/deck/sounds/button_offline.wav",
        success_sound="resources/deck/sounds/button_online.wav",
    )
    engine = DeckSoundEngine(sound_settings=settings)

    try:
        assert engine.enabled is True
        assert engine.volume == pytest.approx(0.75, abs=0.01)

        loaded = engine.get_loaded_sounds()
        assert DeckSoundEngine.SOUND_TAP in loaded
        assert DeckSoundEngine.SOUND_PAGE_SWITCH in loaded
        assert DeckSoundEngine.SOUND_ERROR in loaded
        assert DeckSoundEngine.SOUND_SUCCESS in loaded

        # Проверяем, что файлы действительно существуют на диске
        for key, path in loaded.items():
            assert os.path.isfile(path), f"Файл для '{key}' должен существовать: {path}"

        # Проверяем наличие объектов QSoundEffect и их параметры
        tap_effect = engine.get_effect(DeckSoundEngine.SOUND_TAP)
        assert isinstance(tap_effect, QSoundEffect)
        assert tap_effect.volume() == pytest.approx(0.75, abs=0.01)

    finally:
        engine.cleanup()


def test_deck_sound_engine_volume_clamping_and_enabled_toggle(qapp):
    """
    Проверка регулировки громкости и флага enabled:
    - Изменение громкости обновляет громкость всех предзагруженных QSoundEffect.
    - Ограничение (clamping) диапазона 0.0 <= volume <= 1.0.
    - При enabled=False или volume=0.0 вызовы play не активируют QSoundEffect.
    """
    engine = DeckSoundEngine()
    try:
        # 1. Изменение громкости
        engine.set_volume(0.4)
        assert engine.volume == pytest.approx(0.4, abs=0.01)
        for key in (DeckSoundEngine.SOUND_TAP, DeckSoundEngine.SOUND_PAGE_SWITCH, DeckSoundEngine.SOUND_ERROR):
            effect = engine.get_effect(key)
            if effect:
                assert effect.volume() == pytest.approx(0.4, abs=0.01)

        # 2. Клампинг громкости
        engine.set_volume(1.8)
        assert engine.volume == 1.0

        engine.set_volume(-0.5)
        assert engine.volume == 0.0

        # 3. Флаг enabled
        engine.set_volume(0.8)
        engine.set_enabled(False)
        assert engine.enabled is False

        # При enabled=False вызов play_tap не должен вызывать effect.play()
        tap_effect = engine.get_effect(DeckSoundEngine.SOUND_TAP)
        with patch.object(tap_effect, "play") as mock_play:
            engine.play_tap()
            mock_play.assert_not_called()

        # При volume=0.0 вызов play_tap не должен вызывать effect.play()
        engine.set_enabled(True)
        engine.set_volume(0.0)
        with patch.object(tap_effect, "play") as mock_play:
            engine.play_tap()
            mock_play.assert_not_called()

    finally:
        engine.cleanup()


def test_deck_sound_engine_playback_methods_and_sound_override(qapp):
    """
    Проверка методов воспроизведения:
    - play_tap() вызывает play() на tap-эффекте.
    - play_page_switch() вызывает play() на page_switch-эффекте.
    - play_error() вызывает play() на error-эффекте.
    - play_success() вызывает play() на success-эффекте.
    - play_tap(sound_override=...) динамически загружает и воспроизводит переопределенный звук.
    """
    engine = DeckSoundEngine()
    try:
        tap_effect = engine.get_effect(DeckSoundEngine.SOUND_TAP)
        page_effect = engine.get_effect(DeckSoundEngine.SOUND_PAGE_SWITCH)
        err_effect = engine.get_effect(DeckSoundEngine.SOUND_ERROR)
        succ_effect = engine.get_effect(DeckSoundEngine.SOUND_SUCCESS)

        with patch.object(tap_effect, "play") as mock_tap_play, \
             patch.object(page_effect, "play") as mock_page_play, \
             patch.object(err_effect, "play") as mock_err_play, \
             patch.object(succ_effect, "play") as mock_succ_play:

            engine.play_tap()
            mock_tap_play.assert_called_once()

            engine.play_page_switch()
            mock_page_play.assert_called_once()

            engine.play_error()
            mock_err_play.assert_called_once()

            engine.play_success()
            mock_succ_play.assert_called_once()

        # Проверка sound_override
        override_path = "resources/deck/sounds/button_click2.wav"
        engine.play_tap(sound_override=override_path)
        assert override_path in engine.get_loaded_sounds()

    finally:
        engine.cleanup()


def test_deck_sound_engine_safe_fallback_for_missing_files(qapp):
    """
    Проверка безопасного поведения при отсутствии файла или некорректном пути:
    - Не возникает исключений.
    - play_sound корректно игнорирует отсутствующий файл.
    """
    engine = DeckSoundEngine()
    try:
        # Несуществующий файл
        missing_file = "resources/deck/sounds/non_existent_sound_12345.wav"
        resolved = engine.resolve_sound_path(missing_file)
        assert resolved is None

        # Вызов play не падает
        engine.play_sound(missing_file)

        # Пустой путь
        assert engine.resolve_sound_path("") is None
        assert engine.resolve_sound_path(None) is None
    finally:
        engine.cleanup()


def test_deck_sound_engine_reexport_shim():
    """Проверка доступности DeckSoundEngine через Re-export Shim core.deck.sound_engine."""
    from core.deck.sound_engine import DeckSoundEngine as ShimEngine
    from modules.deck.sound_engine import DeckSoundEngine as DirectEngine

    assert ShimEngine is DirectEngine


def test_deck_view_sound_engine_integration(qapp, sample_two_page_deck_config_path):
    """
    Интеграционный тест интеграции DeckSoundEngine в DeckView:
    - Клик по плитке воспроизводит play_tap().
    - Смена страницы воспроизводит play_page_switch().
    - Ошибка выполнения действия воспроизводит play_error().
    - cleanup() DeckView вызывает cleanup() у DeckSoundEngine.
    """
    from modules.deck.view import DeckView

    mock_sound_engine = MagicMock(spec=DeckSoundEngine)
    view = DeckView(
        config_path=sample_two_page_deck_config_path,
        sound_engine=mock_sound_engine,
    )

    try:
        # 1. Клик по кнопке плитки
        btn = view.grid.get_button("btn_toggle_audio_device")
        assert btn is not None

        view._on_button_triggered(btn.button_config)
        mock_sound_engine.play_tap.assert_called_with(sound_override=btn.button_config.sound_override)

        # 2. Смена страницы
        mock_sound_engine.play_page_switch.reset_mock()
        view.set_active_page("grid4x6")
        mock_sound_engine.play_page_switch.assert_called_once()

        # 3. Ошибка выполнения действия
        mock_sound_engine.play_error.reset_mock()
        view._on_action_finished(btn.button_config.id, success=False, message="Action failed")
        mock_sound_engine.play_error.assert_called_once()

    finally:
        view.cleanup()
        mock_sound_engine.cleanup.assert_called_once()
        view.close()
