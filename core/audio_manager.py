"""
Глубокий модуль управления аудиосессиями Windows Core Audio (PyCaw Facade).
Обеспечивает чтение и регулировку общей громкости (Master Volume)
и громкости отдельных приложений для сенсорного микшера DuckDock.
"""
import logging
from typing import Dict, List, Optional
import psutil
from pydantic import BaseModel, Field

try:
    import comtypes
    from pycaw.pycaw import AudioUtilities
    PYCAW_AVAILABLE = True
except (ImportError, OSError, Exception):
    PYCAW_AVAILABLE = False
    AudioUtilities = None

logger = logging.getLogger("duckdock.audio")

# Словарь дружелюбных имен для известных приложений
APP_FRIENDLY_NAMES: Dict[str, str] = {
    "chrome.exe": "Google Chrome",
    "browser.exe": "Yandex Browser",
    "msedge.exe": "Microsoft Edge",
    "firefox.exe": "Mozilla Firefox",
    "opera.exe": "Opera",
    "discord.exe": "Discord",
    "telegram.exe": "Telegram",
    "spotify.exe": "Spotify",
    "steam.exe": "Steam",
    "vlc.exe": "VLC Media Player",
    "mpv.exe": "MPV Player",
    "foobar2000.exe": "Foobar2000",
    "obs64.exe": "OBS Studio",
    "xboxpcapp.exe": "Xbox App",
    "devenv.exe": "Visual Studio",
    "code.exe": "VS Code",
    "pycharm64.exe": "PyCharm",
    "happ.exe": "happ Proxy",
    "wmplayer.exe": "Windows Media Player",
}


class AudioSessionInfo(BaseModel):
    """Модель данных аудиосессии приложения."""
    pid: Optional[int] = Field(default=None, description="ID процесса (0 или None для системных звуков)")
    name: str = Field(default="Unknown", description="Понятное отображаемое имя")
    process_name: str = Field(default="", description="Имя процесса (например browser.exe)")
    exe_path: Optional[str] = Field(default=None, description="Полный путь к исполняемому файлу")
    volume: float = Field(default=1.0, ge=0.0, le=1.0, description="Уровень громкости от 0.0 до 1.0")
    is_muted: bool = Field(default=False, description="Флаг отключения звука")
    is_active: bool = Field(default=True, description="Флаг активности воспроизведения")


class AudioManager:
    """
    Фасад взаимодействия с Windows Core Audio API через pycaw.
    Изолирует всю COM-специфику и предоставляет безопасный потокобезопасный API.
    """

    def __init__(self):
        self._exe_cache: Dict[int, Optional[str]] = {}
        self._ensure_com_init()

    def _ensure_com_init(self):
        """Гарантирует инициализацию COM для текущего потока."""
        if PYCAW_AVAILABLE:
            try:
                comtypes.CoInitialize()
            except Exception:
                pass

    def _get_speakers_device(self):
        """Получить активное устройство вывода (Default Speakers/Headphones)."""
        if not PYCAW_AVAILABLE or AudioUtilities is None:
            return None
        self._ensure_com_init()
        try:
            return AudioUtilities.GetSpeakers()
        except Exception as e:
            logger.debug(f"Не удалось получить аудиоустройство: {e}")
            return None

    def _get_endpoint_volume(self):
        """Получить интерфейс EndpointVolume для мастер-громкости."""
        dev = self._get_speakers_device()
        if dev is not None:
            try:
                return dev.EndpointVolume
            except Exception as e:
                logger.debug(f"Не удалось получить EndpointVolume: {e}")
        return None

    def get_master_device_name(self) -> str:
        """Получить человекопонятное имя текущего активного аудиоустройства."""
        dev = self._get_speakers_device()
        if dev is not None:
            try:
                # В pycaw dev.FriendlyName может быть доступно
                return getattr(dev, "FriendlyName", str(dev))
            except Exception:
                return "Динамики / Аудиовыход"
        return "Устройство вывода не обнаружено"

    def get_master_volume(self) -> float:
        """Получить общую системную громкость (0.0 - 1.0)."""
        ep = self._get_endpoint_volume()
        if ep is not None:
            try:
                val = ep.GetMasterVolumeLevelScalar()
                return max(0.0, min(1.0, float(val)))
            except Exception as e:
                logger.error(f"Ошибка чтения master volume: {e}")
        return 1.0

    def set_master_volume(self, level: float) -> None:
        """Установить общую системную громкость (0.0 - 1.0)."""
        ep = self._get_endpoint_volume()
        if ep is not None:
            try:
                clamped = max(0.0, min(1.0, float(level)))
                ep.SetMasterVolumeLevelScalar(clamped, None)
            except Exception as e:
                logger.error(f"Ошибка установки master volume: {e}")

    def is_master_muted(self) -> bool:
        """Проверить, отключен ли общий звук."""
        ep = self._get_endpoint_volume()
        if ep is not None:
            try:
                return bool(ep.GetMute())
            except Exception as e:
                logger.error(f"Ошибка чтения master mute: {e}")
        return False

    def set_master_mute(self, muted: bool) -> None:
        """Включить или выключить общее отключение звука."""
        ep = self._get_endpoint_volume()
        if ep is not None:
            try:
                ep.SetMute(1 if muted else 0, None)
            except Exception as e:
                logger.error(f"Ошибка установки master mute: {e}")

    def toggle_master_mute(self) -> bool:
        """Переключить общее состояние отключения звука и вернуть новое состояние."""
        current = self.is_master_muted()
        new_state = not current
        self.set_master_mute(new_state)
        return new_state

    def _resolve_process_exe(self, pid: int) -> Optional[str]:
        """Кэшированное получение полного пути к .exe для извлечения иконки."""
        if pid in self._exe_cache:
            return self._exe_cache[pid]
        try:
            p = psutil.Process(pid)
            exe = p.exe()
            self._exe_cache[pid] = exe
            return exe
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            self._exe_cache[pid] = None
            return None

    def _format_app_name(self, process_name: str, pid: Optional[int]) -> str:
        """Форматирование понятного имени приложения."""
        if not process_name or pid in (0, None):
            return "Системные звуки"
        lower = process_name.lower()
        if lower in APP_FRIENDLY_NAMES:
            return APP_FRIENDLY_NAMES[lower]
        # Отсекаем расширение .exe и форматируем
        base = process_name[:-4] if lower.endswith(".exe") else process_name
        return base

    def get_sessions(self) -> List[AudioSessionInfo]:
        """
        Получить список активных сессий приложений, сгруппированных по PID.
        Исключает устаревшие (Expired) сессии.
        """
        if not PYCAW_AVAILABLE or AudioUtilities is None:
            return []

        self._ensure_com_init()
        try:
            raw_sessions = AudioUtilities.GetAllSessions()
        except Exception as e:
            logger.error(f"Ошибка получения списка сессий: {e}")
            return []

        # Группируем сырые сессии по PID процесса
        grouped: Dict[Optional[int], List] = {}
        for s in raw_sessions:
            try:
                # Состояние 2 = AudioSessionStateExpired
                if getattr(s, "State", 0) == 2:
                    continue
                proc = getattr(s, "Process", None)
                pid = proc.pid if proc else 0
                grouped.setdefault(pid, []).append(s)
            except Exception:
                continue

        results: List[AudioSessionInfo] = []
        for pid, group in grouped.items():
            try:
                first_session = group[0]
                proc = getattr(first_session, "Process", None)
                proc_name = proc.name() if proc else "System"

                exe_path = self._resolve_process_exe(pid) if pid and pid > 0 else None
                display_name = self._format_app_name(proc_name, pid)

                # Вычисляем максимальную громкость среди потоков процесса
                volumes = []
                mutes = []
                for s in group:
                    vol_ctrl = getattr(s, "SimpleAudioVolume", None)
                    if vol_ctrl:
                        try:
                            volumes.append(vol_ctrl.GetMasterVolume())
                            mutes.append(bool(vol_ctrl.GetMute()))
                        except Exception:
                            pass

                vol = max(volumes) if volumes else 1.0
                is_muted = any(mutes) if mutes else False
                is_active = any(getattr(s, "State", 0) == 1 for s in group)

                results.append(
                    AudioSessionInfo(
                        pid=pid,
                        name=display_name,
                        process_name=proc_name,
                        exe_path=exe_path,
                        volume=round(max(0.0, min(1.0, float(vol))), 3),
                        is_muted=is_muted,
                        is_active=is_active,
                    )
                )
            except Exception as e:
                logger.debug(f"Ошибка обработки сессии PID {pid}: {e}")
                continue

        # Сортировка: сначала активные потоки, затем системные звуки, затем по имени
        results.sort(key=lambda s: (not s.is_active, s.pid == 0, s.name.lower()))
        return results

    def set_session_volume(self, pid: Optional[int], level: float) -> None:
        """
        Установить уровень громкости для всех сессий указанного PID (0.0 - 1.0).
        """
        if not PYCAW_AVAILABLE or AudioUtilities is None:
            return

        self._ensure_com_init()
        target_pid = pid if pid is not None else 0
        clamped = max(0.0, min(1.0, float(level)))

        try:
            sessions = AudioUtilities.GetAllSessions()
            for s in sessions:
                proc = getattr(s, "Process", None)
                cur_pid = proc.pid if proc else 0
                if cur_pid == target_pid:
                    vol_ctrl = getattr(s, "SimpleAudioVolume", None)
                    if vol_ctrl:
                        vol_ctrl.SetMasterVolume(clamped, None)
        except Exception as e:
            logger.error(f"Ошибка установки громкости для PID {pid}: {e}")

    def set_session_mute(self, pid: Optional[int], muted: bool) -> None:
        """
        Включить или отключить звук для всех сессий указанного PID.
        """
        if not PYCAW_AVAILABLE or AudioUtilities is None:
            return

        self._ensure_com_init()
        target_pid = pid if pid is not None else 0
        mute_val = 1 if muted else 0

        try:
            sessions = AudioUtilities.GetAllSessions()
            for s in sessions:
                proc = getattr(s, "Process", None)
                cur_pid = proc.pid if proc else 0
                if cur_pid == target_pid:
                    vol_ctrl = getattr(s, "SimpleAudioVolume", None)
                    if vol_ctrl:
                        vol_ctrl.SetMute(mute_val, None)
        except Exception as e:
            logger.error(f"Ошибка установки mute для PID {pid}: {e}")

    def toggle_session_mute(self, pid: Optional[int]) -> bool:
        """
        Переключить состояние mute для сессий указанного PID и вернуть новое состояние.
        """
        if not PYCAW_AVAILABLE or AudioUtilities is None:
            return False

        self._ensure_com_init()
        target_pid = pid if pid is not None else 0

        # Определяем текущее состояние
        current_mute = False
        try:
            sessions = AudioUtilities.GetAllSessions()
            for s in sessions:
                proc = getattr(s, "Process", None)
                cur_pid = proc.pid if proc else 0
                if cur_pid == target_pid:
                    vol_ctrl = getattr(s, "SimpleAudioVolume", None)
                    if vol_ctrl:
                        current_mute = bool(vol_ctrl.GetMute())
                        break

            new_mute = not current_mute
            self.set_session_mute(target_pid, new_mute)
            return new_mute
        except Exception as e:
            logger.error(f"Ошибка переключения mute для PID {pid}: {e}")
            return False
