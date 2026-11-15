"""
Модуль типизированной конфигурации DuckDock.
Перенесен из core.config в modules.settings.config в рамках Feature-First архитектуры.
"""
import sys
from pathlib import Path
from typing import List, Tuple
from pydantic import BaseModel, Field


class DisplayConfig(BaseModel):
    screen_index: int = Field(default=1, description="Индекс целевого экрана")
    width: int = Field(default=1024, description="Ширина экрана 1024px")
    height: int = Field(default=600, description="Высота экрана 600px")
    target_fps: int = Field(default=60, description="Целевая кадровая частота")
    fallback_geometry: Tuple[int, int, int, int] = Field(
        default=(2560, 833, 1024, 600),
        description="Резервные координаты при отсутствии физического 2-го экрана"
    )


class LayoutConfig(BaseModel):
    sidebar_width: int = Field(default=80, description="Ширина сайдбара")
    workspace_width: int = Field(default=944, description="Ширина рабочей области")
    button_size: int = Field(default=64, description="Размер кнопок сайдбара")
    button_margin: int = Field(default=8, description="Отступы кнопок")
    corner_radius: int = Field(default=12, description="Радиус скругления элементов")


class StealthConfig(BaseModel):
    enable_stealth_focus: bool = Field(default=True, description="Флаг WS_EX_NOACTIVATE")
    anti_cursor_warp: bool = Field(default=True, description="Автовозврат курсора на основной экран")
    focus_restore_delay_ms: int = Field(default=80, description="Задержка возврата фокуса (мс)")
    cursor_restore_delay_ms: int = Field(default=25, description="Задержка возврата курсора (мс)")
    lock_input_mode: bool = Field(default=False, description="Режим набора текста (отключает stealth)")


class DimmerConfig(BaseModel):
    default_opacity: float = Field(default=0.0, description="Начальная непрозрачность слоя")
    night_mode_opacity: float = Field(default=0.50, description="Непрозрачность ночного режима")
    step: float = Field(default=0.05, description="Шаг регулировки яркости")


class TrackedAppConfig(BaseModel):
    name: str
    process_name: str
    tab_index: int
    auto_tile: bool = True


class AppConfig(BaseModel):
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    layout: LayoutConfig = Field(default_factory=LayoutConfig)
    stealth: StealthConfig = Field(default_factory=StealthConfig)
    dimmer: DimmerConfig = Field(default_factory=DimmerConfig)
    tracked_apps: List[TrackedAppConfig] = Field(default_factory=list)


def load_config(config_path: Path | str | None = None) -> AppConfig:
    """Загрузить конфигурацию из файла config.json или вернуть дефолтную."""
    if config_path is None:
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            if (exe_dir / "config.json").exists():
                config_path = exe_dir / "config.json"
            elif hasattr(sys, "_MEIPASS") and (Path(sys._MEIPASS) / "config.json").exists():
                config_path = Path(sys._MEIPASS) / "config.json"
            else:
                config_path = Path(__file__).resolve().parents[2] / "config.json"
        else:
            config_path = Path(__file__).resolve().parents[2] / "config.json"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        return AppConfig()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
            return AppConfig.model_validate_json(content)
    except Exception as e:
        print(f"[!] Ошибка загрузки {config_path}: {e}. Используются значения по умолчанию.")
        return AppConfig()


__all__ = [
    "DisplayConfig",
    "LayoutConfig",
    "StealthConfig",
    "DimmerConfig",
    "TrackedAppConfig",
    "AppConfig",
    "load_config",
]
