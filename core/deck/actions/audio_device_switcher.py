"""
Модуль переключения устройств воспроизведения Windows через COM-интерфейс IPolicyConfig.
Обеспечивает переключение дефолтного аудиоустройства (Наушники <-> Динамики)
без использования сторонних утилит с изоляцией COM-контекста.
"""
import logging
from ctypes import POINTER, c_int, c_int64, c_void_p
from ctypes.wintypes import DWORD, LPCWSTR
from typing import List, Optional

from core.deck.models import AudioDeviceInfo

logger = logging.getLogger("duckdock.deck.audio_device")

try:
    import comtypes
    from comtypes import COMMETHOD, GUID, HRESULT, IUnknown
    from pycaw.pycaw import AudioUtilities
    PYCAW_AVAILABLE = True
except (ImportError, OSError, Exception):
    PYCAW_AVAILABLE = False
    AudioUtilities = None
    IUnknown = object
    GUID = None

# CLSID и IID недокументированного COM-интерфейса Windows IPolicyConfig
if PYCAW_AVAILABLE and GUID is not None:
    CLSID_PolicyConfigClient = GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}")
    IID_IPolicyConfig = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
else:
    CLSID_PolicyConfigClient = None
    IID_IPolicyConfig = None

# Windows Property Key для FriendlyName: {a45c254e-df1c-4efd-8020-67d146a850e0}, 14
PKEY_DEVICE_FRIENDLY_NAME = "{A45C254E-DF1C-4EFD-8020-67D146A850E0} 14"

# Роли аудиоустройств WASAPI (ERole)
ROLE_CONSOLE = 0
ROLE_MULTIMEDIA = 1
ROLE_COMMUNICATIONS = 2
ALL_ROLES = (ROLE_CONSOLE, ROLE_MULTIMEDIA, ROLE_COMMUNICATIONS)

# Флаг состояния устройства
DEVICE_STATE_ACTIVE = 1

# Префикс ID устройств вывода (eRender) в Windows
RENDER_DEVICE_PREFIX = "{0.0.0.00000000}."


if PYCAW_AVAILABLE:
    class IPolicyConfig(IUnknown):
        """COM vtable интерфейса IPolicyConfig для Windows 10/11."""
        _iid_ = IID_IPolicyConfig
        _methods_ = [
            COMMETHOD([], HRESULT, "GetMixFormat",
                      (["in"], LPCWSTR, "pszDeviceName"),
                      (["out"], POINTER(c_void_p), "ppFormat")),
            COMMETHOD([], HRESULT, "GetDeviceFormat",
                      (["in"], LPCWSTR, "pszDeviceName"),
                      (["in"], c_int, "bDefault"),
                      (["out"], POINTER(c_void_p), "ppFormat")),
            COMMETHOD([], HRESULT, "ResetDeviceFormat",
                      (["in"], LPCWSTR, "pszDeviceName")),
            COMMETHOD([], HRESULT, "SetDeviceFormat",
                      (["in"], LPCWSTR, "pszDeviceName"),
                      (["in"], c_void_p, "pEndpointFormat"),
                      (["in"], c_void_p, "pMixFormat")),
            COMMETHOD([], HRESULT, "GetProcessingPeriod",
                      (["in"], LPCWSTR, "pszDeviceName"),
                      (["in"], c_int, "bDefault"),
                      (["out"], POINTER(c_int64), "pmftDefaultPeriod"),
                      (["out"], POINTER(c_int64), "pmftMinimumPeriod")),
            COMMETHOD([], HRESULT, "SetProcessingPeriod",
                      (["in"], LPCWSTR, "pszDeviceName"),
                      (["in"], POINTER(c_int64), "pmftPeriod")),
            COMMETHOD([], HRESULT, "GetShareMode",
                      (["in"], LPCWSTR, "pszDeviceName"),
                      (["out"], POINTER(c_int), "pMode")),
            COMMETHOD([], HRESULT, "SetShareMode",
                      (["in"], LPCWSTR, "pszDeviceName"),
                      (["in"], c_int, "mode")),
            COMMETHOD([], HRESULT, "GetPropertyValue",
                      (["in"], LPCWSTR, "pszDeviceName"),
                      (["in"], c_void_p, "pKey"),
                      (["out"], c_void_p, "pv")),
            COMMETHOD([], HRESULT, "SetPropertyValue",
                      (["in"], LPCWSTR, "pszDeviceName"),
                      (["in"], c_void_p, "pKey"),
                      (["in"], c_void_p, "pv")),
            COMMETHOD([], HRESULT, "SetDefaultEndpoint",
                      (["in"], LPCWSTR, "wszDeviceId"),
                      (["in"], DWORD, "eRole")),
            COMMETHOD([], HRESULT, "SetEndpointVisibility",
                      (["in"], LPCWSTR, "wszDeviceId"),
                      (["in"], c_int, "bVisible")),
        ]
else:
    IPolicyConfig = None


def _ensure_com_init() -> None:
    """Гарантирует инициализацию COM для текущего потока."""
    if PYCAW_AVAILABLE:
        try:
            comtypes.CoInitialize()
        except Exception:
            pass


def get_default_playback_device_id() -> Optional[str]:
    """Возвращает системный ID активного по умолчанию устройства вывода."""
    if not PYCAW_AVAILABLE or AudioUtilities is None:
        return None
    _ensure_com_init()
    try:
        spk = AudioUtilities.GetSpeakers()
        if spk is not None:
            if hasattr(spk, "GetId"):
                return spk.GetId()
            if hasattr(spk, "id"):
                return spk.id
    except Exception as e:
        logger.debug(f"Не удалось получить ID дефолтных динамиков: {e}")
    return None


def get_playback_devices() -> List[AudioDeviceInfo]:
    """
    Возвращает список всех активных устройств воспроизведения (eRender).
    """
    if not PYCAW_AVAILABLE or AudioUtilities is None:
        return []

    _ensure_com_init()
    devices_list: List[AudioDeviceInfo] = []
    try:
        default_id = get_default_playback_device_id()
        raw_devices = AudioUtilities.GetAllDevices()

        for d in raw_devices:
            try:
                state_val = getattr(d.state, "value", d.state)
                # Фильтруем только активные устройства вывода
                if state_val != DEVICE_STATE_ACTIVE:
                    continue

                dev_id = getattr(d, "id", None)
                if not dev_id and hasattr(d, "GetId"):
                    dev_id = d.GetId()

                if not dev_id:
                    continue

                # Проверяем, что это render (вывод), а не capture (ввод)
                if not dev_id.startswith(RENDER_DEVICE_PREFIX):
                    continue

                name = getattr(d, "FriendlyName", None)
                if not name and hasattr(d, "properties"):
                    name = d.properties.get(PKEY_DEVICE_FRIENDLY_NAME)
                if not name:
                    name = "Аудиоустройство"

                is_def = (dev_id == default_id)

                devices_list.append(
                    AudioDeviceInfo(
                        id=dev_id,
                        name=name,
                        is_default=is_def,
                        state=int(state_val),
                    )
                )
            except Exception as item_err:
                logger.debug(f"Ошибка при разборе аудиоустройства: {item_err}")
                continue

    except Exception as e:
        logger.error(f"Ошибка получения списка аудиоустройств: {e}")

    return devices_list


def switch_default_device(device_id: str) -> bool:
    """
    Устанавливает указанное аудиоустройство как дефолтное для всех ролей
    (eConsole, eMultimedia, eCommunications) через COM IPolicyConfig.
    """
    if not PYCAW_AVAILABLE or IPolicyConfig is None:
        logger.error("COM / pycaw недоступен для смены аудиоустройства")
        return False

    try:
        comtypes.CoInitialize()
    except Exception:
        pass

    try:
        policy = comtypes.CoCreateInstance(
            CLSID_PolicyConfigClient,
            IPolicyConfig,
            comtypes.CLSCTX_ALL,
        )

        for role in ALL_ROLES:
            hr = policy.SetDefaultEndpoint(device_id, role)
            if hr != 0:
                logger.warning(f"SetDefaultEndpoint role={role} returned hr={hr}")

        logger.info(f"Успешно переключено аудиоустройство по умолчанию на: {device_id}")
        return True
    except Exception as e:
        logger.error(f"Исключение при вызове IPolicyConfig.SetDefaultEndpoint: {e}")
        return False
    finally:
        try:
            comtypes.CoUninitialize()
        except Exception:
            pass


def toggle_audio_device(targets: Optional[List[str]] = None) -> Optional[AudioDeviceInfo]:
    """
    Циклически переключает аудиоустройство между списком целевых фильтров targets
    (например ['Наушники', 'Динамики'] или ['Headset', 'Creative']).
    Если targets не передан, циклически переключает между всеми доступными устройствами.
    Возвращает информацию о вновь активированном устройстве.
    """
    devices = get_playback_devices()
    if not devices:
        logger.warning("Нет доступных активных устройств воспроизведения")
        return None

    if len(devices) == 1:
        return devices[0]

    # Определяем текущее дефолтное устройство
    current_default = next((d for d in devices if d.is_default), None)
    current_id = current_default.id if current_default else devices[0].id

    # Фильтруем устройства, если задан список целей
    candidate_devices: List[AudioDeviceInfo] = []
    if targets:
        for t in targets:
            t_lower = t.lower()
            matched = [d for d in devices if t_lower in d.name.lower()]
            for m in matched:
                if m not in candidate_devices:
                    candidate_devices.append(m)

    if not candidate_devices:
        candidate_devices = devices

    # Находим индекс текущего устройства среди кандидатов
    curr_idx = -1
    for idx, d in enumerate(candidate_devices):
        if d.id == current_id:
            curr_idx = idx
            break

    # Следующее устройство в циклическом порядке
    next_idx = (curr_idx + 1) % len(candidate_devices)
    target_dev = candidate_devices[next_idx]

    success = switch_default_device(target_dev.id)
    if success:
        target_dev.is_default = True
        return target_dev
    return None
