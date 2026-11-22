"""
Звуковой движок интерфейса DuckDeck (DeckSoundEngine).
Реализует аппаратное воспроизведение коротких звуковых эффектов (Zero-Latency Audio)
на базе PySide6.QtMultimedia.QSoundEffect с предзагрузкой WAV-семплов в оперативную память.
Управляется через модель SoundSettings (громкость, флаг включения, пути к семплам).
"""
import logging
import os
import sys
from typing import Dict, Optional

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect

from modules.deck.models import SoundSettings

logger = logging.getLogger("duckdock.deck.sound_engine")


class DeckSoundEngine(QObject):
    """
    Высокопроизводительный звуковой движок для сенсорного интерфейса DuckDeck.
    Инварианты:
      - Предзагрузка WAV в RAM через QSoundEffect (0 мс latency).
      - Не блокирует главный цикл Qt Event Loop.
      - Не отбирает фокус (Stealth Focus Invariant).
      - Безопасное подавление ошибок при отсутствии аудиоустройства или файлов.
    """

    SOUND_TAP = "tap"
    SOUND_PAGE_SWITCH = "page_switch"
    SOUND_ERROR = "error"
    SOUND_SUCCESS = "success"

    def __init__(
        self,
        sound_settings: Optional[SoundSettings] = None,
        base_dir: Optional[str] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.base_dir = base_dir or self._detect_base_dir()
        self._settings = sound_settings or SoundSettings()
        self._effects: Dict[str, QSoundEffect] = {}
        self._sound_paths: Dict[str, str] = {}
        self._soundboard_pool: list[QSoundEffect] = []
        self._preview_effect: Optional[QSoundEffect] = None

        self.apply_settings(self._settings)

    @staticmethod
    def _detect_base_dir() -> str:
        """Определение базового каталога приложения с поддержкой PyInstaller bundle."""
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return getattr(sys, "_MEIPASS")
        # Корень проекта duckdock: modules/deck/sound_engine.py -> duckdock
        current_file = os.path.abspath(__file__)
        return os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

    def resolve_sound_path(self, path: Optional[str]) -> Optional[str]:
        """
        Разрешение относительного пути к звуковому файлу в абсолютный.
        Проверяет наличие файла в файловой системе.
        """
        if not path:
            return None

        # 1. Абсолютный существующий путь
        if os.path.isabs(path) and os.path.isfile(path):
            return os.path.abspath(path)

        # 2. Поиск относительно base_dir
        candidate = os.path.join(self.base_dir, path)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

        # 3. Поиск относительно текущей рабочей директории
        candidate_cwd = os.path.abspath(path)
        if os.path.isfile(candidate_cwd):
            return candidate_cwd

        # 4. Fallback: поиск внутри resources/deck/sounds/ по basename
        basename = os.path.basename(path)
        candidate_sounds = os.path.join(self.base_dir, "resources", "deck", "sounds", basename)
        if os.path.isfile(candidate_sounds):
            return os.path.abspath(candidate_sounds)

        logger.debug("Звуковой файл не найден: %s (base_dir=%s)", path, self.base_dir)
        return None

    def _load_effect(self, sound_key: str, file_path: Optional[str]) -> Optional[QSoundEffect]:
        """Создание и предзагрузка QSoundEffect в память."""
        abs_path = self.resolve_sound_path(file_path)
        if not abs_path:
            return None

        try:
            effect = QSoundEffect(self)
            effect.setSource(QUrl.fromLocalFile(abs_path))
            effect.setVolume(self.volume)
            self._effects[sound_key] = effect
            self._sound_paths[sound_key] = abs_path
            return effect
        except Exception as e:
            logger.warning("Не удалось предзагрузить звук '%s' из '%s': %s", sound_key, abs_path, e)
            return None

    def apply_settings(self, settings: SoundSettings) -> None:
        """Применение новых настроек звука и предзагрузка семплов."""
        self._settings = settings

        # Предзагрузка основных семплов в RAM
        self._load_effect(self.SOUND_TAP, settings.default_tap_sound)
        self._load_effect(self.SOUND_PAGE_SWITCH, settings.page_switch_sound)
        self._load_effect(self.SOUND_ERROR, settings.error_sound)
        if settings.success_sound:
            self._load_effect(self.SOUND_SUCCESS, settings.success_sound)

        # Обновление громкости у всех предзагруженных эффектов
        self.set_volume(settings.volume)

    @property
    def settings(self) -> SoundSettings:
        """Текущие настройки звука."""
        return self._settings

    @property
    def enabled(self) -> bool:
        """Флаг активности звуковых эффектов."""
        return self._settings.enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self.set_enabled(value)

    def set_enabled(self, value: bool) -> None:
        """Включение или выключение звуков."""
        self._settings.enabled = bool(value)

    @property
    def volume(self) -> float:
        """Текущая громкость от 0.0 до 1.0."""
        return self._settings.volume

    @volume.setter
    def volume(self, value: float) -> None:
        self.set_volume(value)

    def set_volume(self, value: float) -> None:
        """Установка громкости от 0.0 до 1.0 с обновлением всех предзагруженных семплов."""
        clamped = max(0.0, min(1.0, float(value)))
        self._settings.volume = clamped
        for effect in self._effects.values():
            try:
                effect.setVolume(clamped)
            except Exception as e:
                logger.debug("Ошибка установки громкости эффекта: %s", e)

    def play_sound(self, sound_key_or_path: str) -> None:
        """Воспроизведение звука по системному ключу или пути к файлу."""
        if not self.enabled or self.volume <= 0.0:
            return

        effect = self._effects.get(sound_key_or_path)
        if effect is None:
            # Попытка динамической загрузки и кэширования по пути
            effect = self._load_effect(sound_key_or_path, sound_key_or_path)

        if effect:
            try:
                # Если эффект уже проигрывается, останавливаем и перезапускаем для 0 мс задержки
                if effect.isPlaying():
                    effect.stop()
                effect.play()
            except Exception as e:
                logger.debug("Ошибка воспроизведения звука '%s': %s", sound_key_or_path, e)

    def play_tap(self, sound_override: Optional[str] = None) -> None:
        """Воспроизведение клика плитки (с поддержкой индивидуального sound_override кнопки)."""
        if sound_override == "muted":
            return
        if sound_override and sound_override != "default":
            self.play_sound(sound_override)
        else:
            self.play_sound(self.SOUND_TAP)

    def play_soundboard(
        self,
        file_path: str,
        volume: float = 1.0,
        stop_others: bool = False,
    ) -> bool:
        """
        Воспроизведение звуковой дорожки саундборда в неблокирующем режиме.
        Поддерживает пул до 8 параллельных эффектов с авто-очисткой завершенных.
        """
        if not self.enabled or self.volume <= 0.0 or not file_path:
            return False

        abs_path = self.resolve_sound_path(file_path)
        if not abs_path:
            logger.warning("Soundboard file not found: '%s'", file_path)
            return False

        if stop_others:
            self.stop_soundboard()

        # Очистка эффектов, завершивших воспроизведение
        self._soundboard_pool = [eff for eff in self._soundboard_pool if eff.isPlaying()]

        # Ограничение размера пула (не более 8 одновременных звуков)
        while len(self._soundboard_pool) >= 8:
            old_eff = self._soundboard_pool.pop(0)
            try:
                old_eff.stop()
            except Exception:
                pass

        try:
            effect = QSoundEffect(self)
            effect.setSource(QUrl.fromLocalFile(abs_path))
            clamped_vol = max(0.0, min(1.0, float(volume))) * self.volume
            effect.setVolume(clamped_vol)
            effect.play()
            self._soundboard_pool.append(effect)
            return True
        except Exception as exc:
            logger.warning("Failed to play soundboard effect '%s': %s", abs_path, exc)
            return False

    def stop_soundboard(self) -> None:
        """Мгновенно глушит все играющие эффекты саундборда и превью."""
        for eff in self._soundboard_pool:
            try:
                if eff.isPlaying():
                    eff.stop()
            except Exception:
                pass
        self._soundboard_pool.clear()
        self.stop_preview()

    def preview_sound(self, file_path: str, volume: float = 1.0) -> bool:
        """
        Воспроизведение предпрослушки в конфигураторе DuckDeck Editor.
        """
        self.stop_preview()
        if not file_path:
            return False

        abs_path = self.resolve_sound_path(file_path)
        if not abs_path:
            logger.warning("Preview sound file not found: '%s'", file_path)
            return False

        try:
            effect = QSoundEffect(self)
            effect.setSource(QUrl.fromLocalFile(abs_path))
            clamped_vol = max(0.0, min(1.0, float(volume))) * self.volume
            effect.setVolume(clamped_vol)
            effect.play()
            self._preview_effect = effect
            return True
        except Exception as exc:
            logger.warning("Failed to preview sound '%s': %s", abs_path, exc)
            return False

    def stop_preview(self) -> None:
        """Останавливает текущее воспроизведение предпрослушки."""
        if self._preview_effect is not None:
            try:
                if self._preview_effect.isPlaying():
                    self._preview_effect.stop()
            except Exception:
                pass
            self._preview_effect = None

    def is_preview_playing(self) -> bool:
        """Возвращает True, если превью активно играет."""
        if self._preview_effect is not None:
            try:
                return self._preview_effect.isPlaying()
            except Exception:
                pass
        return False

    def play_page_switch(self) -> None:
        """Воспроизведение звука смены страницы или свайпа."""
        self.play_sound(self.SOUND_PAGE_SWITCH)

    def play_error(self) -> None:
        """Воспроизведение звука ошибки или заблокированного действия."""
        self.play_sound(self.SOUND_ERROR)

    def play_success(self) -> None:
        """Воспроизведение звука успешного выполнения."""
        self.play_sound(self.SOUND_SUCCESS)

    def get_loaded_sounds(self) -> Dict[str, str]:
        """Возвращает словарь предзагруженных звуков {key: abs_path}."""
        return dict(self._sound_paths)

    def get_effect(self, sound_key: str) -> Optional[QSoundEffect]:
        """Получение объекта QSoundEffect по ключу для интроспекции и тестов."""
        return self._effects.get(sound_key)

    def cleanup(self) -> None:
        """Остановка и очистка всех звуковых эффектов."""
        self.stop_soundboard()
        for effect in self._effects.values():
            try:
                if effect.isPlaying():
                    effect.stop()
            except Exception:
                pass
        self._effects.clear()
        self._sound_paths.clear()


__all__ = ["DeckSoundEngine"]
