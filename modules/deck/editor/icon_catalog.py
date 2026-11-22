"""
Декларативный каталог иконок и кэш изображений редактора DuckDeck (IconCatalog & IconCache).
Поддерживает системные, прикладные, медиа и глифовые иконки, пользовательскую папку
resources/deck/custom_icons/ и двуязычный семантический поиск (RU/EN).
"""
from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap

logger = logging.getLogger("duckdock.deck.editor.icon_catalog")

CUSTOM_ICONS_DIR = Path("resources/deck/custom_icons")
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".svg", ".ico", ".jpg", ".jpeg", ".webp"}


@dataclass
class IconEntryDTO:
    """DTO описания иконки в каталоге."""
    id: str
    name: str
    category: str
    path_or_glyph: str
    is_glyph: bool = False
    keywords_ru: list[str] = field(default_factory=list)
    keywords_en: list[str] = field(default_factory=list)


@dataclass
class IconCategoryDTO:
    """DTO категории иконок."""
    id: str
    title_key: str
    icon_count: int = 0


class IconCache:
    """
    Потокобезопасный in-memory кэш предмасштабированных QPixmap.
    Устраняет задержки при отрисовке сетки каталога иконок.
    """

    def __init__(self) -> None:
        self._pixmap_cache: dict[tuple[str, int], QPixmap] = {}

    def get_pixmap(self, path_or_glyph: str, size: int) -> QPixmap:
        """
        Возвращает масштабированный QPixmap для файла изображения или глифа.
        Результат кэшируется по ключу (path_or_glyph, size).
        """
        cache_key = (path_or_glyph, size)
        if cache_key in self._pixmap_cache:
            return self._pixmap_cache[cache_key]

        # 1. Проверка на существование файла изображения
        resolved_path = None
        if os.path.isfile(path_or_glyph):
            resolved_path = path_or_glyph
        else:
            rel_path = Path(path_or_glyph)
            if rel_path.is_file():
                resolved_path = str(rel_path)

        if resolved_path is not None:
            source_pixmap = QPixmap(resolved_path)
            if not source_pixmap.isNull():
                scaled = source_pixmap.scaled(
                    size,
                    size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self._pixmap_cache[cache_key] = scaled
                return scaled

        # 2. Отрисовка глифа / эмодзи / символа
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.TextAntialiasing, True)
            font = QFont()
            font.setPixelSize(max(10, int(size * 0.65)))
            painter.setFont(font)
            painter.setPen(QColor("#f8fafc"))
            rect = QRect(0, 0, size, size)
            painter.drawText(rect, Qt.AlignCenter, path_or_glyph)
        finally:
            painter.end()

        self._pixmap_cache[cache_key] = pixmap
        return pixmap

    def clear(self) -> None:
        """Очищает кэш пиксмапов."""
        self._pixmap_cache.clear()


class IconCatalog:
    """
    Синглтон каталога иконок DuckDeck.
    Управляет встроенными коллекциями (System, Apps, Media, Glyphs),
    пользовательскими файлами и поиском по ключевым словам.
    """

    _instance: Optional[IconCatalog] = None

    def __new__(cls) -> IconCatalog:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.cache = IconCache()
        self._builtin_icons: list[IconEntryDTO] = []
        self._load_builtins()

    def _load_builtins(self) -> None:
        """Инициализация встроенного набора иконок по категориям."""
        # 1. Системные иконки (System)
        system_icons = [
            IconEntryDTO("sys:vol_up", "Volume Up", "system", "🔊", True, ["звук", "громкость", "плюс"], ["volume", "sound", "up"]),
            IconEntryDTO("sys:vol_down", "Volume Down", "system", "🔉", True, ["звук", "тише", "минус"], ["volume", "sound", "down"]),
            IconEntryDTO("sys:mute", "Mute Audio", "system", "🔇", True, ["мьют", "без звука", "заглушить"], ["mute", "silence", "audio"]),
            IconEntryDTO("sys:mic_mute", "Mute Mic", "system", "🎙️", True, ["микрофон", "голос", "запись"], ["microphone", "mic", "voice"]),
            IconEntryDTO("sys:cpu", "CPU Monitor", "system", "💻", True, ["процессор", "цпу", "нагрузка"], ["cpu", "processor", "load"]),
            IconEntryDTO("sys:gpu", "GPU Monitor", "system", "🎮", True, ["видеокарта", "гпу", "графика"], ["gpu", "graphics", "card"]),
            IconEntryDTO("sys:ram", "RAM Memory", "system", "💾", True, ["память", "озу", "рам"], ["ram", "memory"]),
            IconEntryDTO("sys:temp", "Temperature", "system", "🌡️", True, ["температура", "нагрев", "градус"], ["temperature", "temp", "heat"]),
            IconEntryDTO("sys:dimmer", "Dimmer", "system", "🌙", True, ["диммер", "яркость", "ночной режим", "экран"], ["dimmer", "brightness", "night", "screen"]),
            IconEntryDTO("sys:lock", "Screen Lock", "system", "🔒", True, ["блокировка", "замок", "экран"], ["lock", "screen", "security"]),
            IconEntryDTO("sys:screenshot", "Screenshot", "system", "📸", True, ["скриншот", "снимок", "экран"], ["screenshot", "capture", "screen"]),
            IconEntryDTO("sys:settings", "Settings", "system", "⚙️", True, ["настройки", "параметры", "конфиг"], ["settings", "config", "preferences"]),
        ]

        # 2. Приложения (Apps)
        app_icons = [
            IconEntryDTO("app:chrome", "Google Chrome", "apps", "🌐", True, ["хром", "браузер", "интернет"], ["chrome", "browser", "web"]),
            IconEntryDTO("app:firefox", "Mozilla Firefox", "apps", "🦊", True, ["фаерфокс", "лиса", "браузер"], ["firefox", "browser", "web"]),
            IconEntryDTO("app:edge", "Microsoft Edge", "apps", "🧭", True, ["эдж", "браузер", "майкрософт"], ["edge", "browser", "microsoft"]),
            IconEntryDTO("app:discord", "Discord", "apps", "💬", True, ["дискорд", "чат", "голос", "сообщения"], ["discord", "chat", "voice", "messages"]),
            IconEntryDTO("app:telegram", "Telegram", "apps", "✈️", True, ["телеграм", "телега", "чат"], ["telegram", "messenger", "chat"]),
            IconEntryDTO("app:steam", "Steam", "apps", "🎮", True, ["стим", "игры", "гейминг"], ["steam", "games", "gaming"]),
            IconEntryDTO("app:epic", "Epic Games", "apps", "⚡", True, ["эпик", "игры", "лаунчер"], ["epic", "games", "launcher"]),
            IconEntryDTO("app:obs", "OBS Studio", "apps", "🔴", True, ["обс", "стрим", "запись"], ["obs", "stream", "record", "broadcast"]),
            IconEntryDTO("app:terminal", "Terminal", "apps", "⌨️", True, ["терминал", "консоль", "командная строка"], ["terminal", "console", "cmd", "shell"]),
            IconEntryDTO("app:calc", "Calculator", "apps", "🔢", True, ["калькулятор", "счет"], ["calculator", "calc", "math"]),
        ]

        # 3. Медиа & Стриминг (Media)
        media_icons = [
            IconEntryDTO("media:play", "Play", "media", "▶️", True, ["плей", "воспроизведение", "пуск"], ["play", "start"]),
            IconEntryDTO("media:pause", "Pause", "media", "⏸️", True, ["пауза", "стоп"], ["pause", "hold"]),
            IconEntryDTO("media:stop", "Stop", "media", "⏹️", True, ["стоп", "остановить"], ["stop"]),
            IconEntryDTO("media:next", "Next Track", "media", "⏭️", True, ["следующий", "трек", "вперед"], ["next", "track", "forward"]),
            IconEntryDTO("media:prev", "Previous Track", "media", "⏮️", True, ["предыдущий", "трек", "назад"], ["prev", "previous", "track", "back"]),
            IconEntryDTO("media:shuffle", "Shuffle", "media", "🔀", True, ["случайно", "перемешать"], ["shuffle", "random"]),
            IconEntryDTO("media:repeat", "Repeat", "media", "🔁", True, ["повтор", "зациклить"], ["repeat", "loop"]),
            IconEntryDTO("media:ffwd", "Fast Forward", "media", "⏩", True, ["перемотка", "вперед"], ["fast forward", "forward"]),
            IconEntryDTO("media:rwd", "Rewind", "media", "⏪", True, ["перемотка", "назад"], ["rewind", "backward"]),
        ]

        # 4. Символы & Эмодзи (Glyphs)
        glyph_icons = [
            IconEntryDTO("glyph:gamepad", "Gamepad", "glyphs", "🎮", True, ["геймпад", "джойстик", "игра"], ["gamepad", "joystick", "game"]),
            IconEntryDTO("glyph:bell", "Bell", "glyphs", "🔔", True, ["звонок", "уведомление", "колокол"], ["bell", "notification", "alert"]),
            IconEntryDTO("glyph:rocket", "Rocket", "glyphs", "🚀", True, ["ракета", "запуск", "старт", "быстро"], ["rocket", "launch", "fast"]),
            IconEntryDTO("glyph:lightbulb", "Lightbulb", "glyphs", "💡", True, ["лампочка", "идея", "свет"], ["lightbulb", "idea", "light"]),
            IconEntryDTO("glyph:shield", "Shield", "glyphs", "🛡️", True, ["щит", "защита", "безопасность"], ["shield", "defense", "security"]),
            IconEntryDTO("glyph:star", "Star", "glyphs", "⭐", True, ["звезда", "избранное"], ["star", "favorite"]),
            IconEntryDTO("glyph:heart", "Heart", "glyphs", "❤️", True, ["сердце", "лайк", "любовь"], ["heart", "like", "love"]),
            IconEntryDTO("glyph:fire", "Fire", "glyphs", "🔥", True, ["огонь", "жара", "топ"], ["fire", "hot", "flame"]),
            IconEntryDTO("glyph:folder", "Folder", "glyphs", "📁", True, ["папка", "директория", "файлы"], ["folder", "directory", "files"]),
            IconEntryDTO("glyph:globe", "Globe", "glyphs", "🌍", True, ["планета", "мир", "глобус"], ["globe", "earth", "world"]),
            IconEntryDTO("glyph:music", "Music", "glyphs", "🎵", True, ["музыка", "нота", "песня"], ["music", "note", "song"]),
            IconEntryDTO("glyph:headphones", "Headphones", "glyphs", "🎧", True, ["наушники", "звук", "аудио"], ["headphones", "headset", "audio"]),
        ]

        self._builtin_icons = system_icons + app_icons + media_icons + glyph_icons

    def scan_custom_icons(self) -> list[IconEntryDTO]:
        """
        Сканирует директорию resources/deck/custom_icons/ и возвращает
        список зарегистрированных пользовательских файлов.
        """
        custom_icons: list[IconEntryDTO] = []
        try:
            CUSTOM_ICONS_DIR.mkdir(parents=True, exist_ok=True)
            for entry in CUSTOM_ICONS_DIR.iterdir():
                if entry.is_file() and entry.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
                    stem_name = entry.stem.replace("_", " ").title()
                    lower_name = entry.stem.lower()
                    rel_path = str(entry).replace("\\", "/")
                    custom_icons.append(
                        IconEntryDTO(
                            id=f"custom:{entry.name}",
                            name=stem_name,
                            category="custom",
                            path_or_glyph=rel_path,
                            is_glyph=False,
                            keywords_ru=[lower_name],
                            keywords_en=[lower_name],
                        )
                    )
        except Exception as exc:
            logger.warning("Error scanning custom icons in '%s': %s", CUSTOM_ICONS_DIR, exc)

        return custom_icons

    def save_custom_icon(self, source_path: str) -> str:
        """
        Копирует указанный файл изображения в папку resources/deck/custom_icons/
        и возвращает нормализованный относительный путь.
        """
        CUSTOM_ICONS_DIR.mkdir(parents=True, exist_ok=True)
        src = Path(source_path)
        if not src.is_file():
            raise FileNotFoundError(f"Source icon file not found: {source_path}")

        dest = CUSTOM_ICONS_DIR / src.name
        # Защита от коллизий имен
        if dest.exists() and dest.resolve() != src.resolve():
            base_stem = src.stem
            ext = src.suffix
            counter = 1
            while dest.exists() and dest.resolve() != src.resolve():
                dest = CUSTOM_ICONS_DIR / f"{base_stem}_{counter}{ext}"
                counter += 1

        if dest.resolve() != src.resolve():
            shutil.copy2(src, dest)

        return str(dest).replace("\\", "/")

    def get_all_icons(self) -> list[IconEntryDTO]:
        """Возвращает объединение встроенных и пользовательских иконок."""
        return self._builtin_icons + self.scan_custom_icons()

    def get_categories(self) -> list[IconCategoryDTO]:
        """
        Возвращает список категорий с актуальным подсчетом количества иконок.
        """
        all_icons = self.get_all_icons()
        counts: dict[str, int] = {
            "all": len(all_icons),
            "system": 0,
            "apps": 0,
            "media": 0,
            "glyphs": 0,
            "custom": 0,
        }
        for icon in all_icons:
            if icon.category in counts:
                counts[icon.category] += 1

        return [
            IconCategoryDTO("all", "deck.editor.dialog.icon_library.categories.all", counts["all"]),
            IconCategoryDTO("system", "deck.editor.dialog.icon_library.categories.system", counts["system"]),
            IconCategoryDTO("apps", "deck.editor.dialog.icon_library.categories.apps", counts["apps"]),
            IconCategoryDTO("media", "deck.editor.dialog.icon_library.categories.media", counts["media"]),
            IconCategoryDTO("glyphs", "deck.editor.dialog.icon_library.categories.glyphs", counts["glyphs"]),
            IconCategoryDTO("custom", "deck.editor.dialog.icon_library.categories.custom", counts["custom"]),
        ]

    def get_icons(self, category: Optional[str] = None, search_query: str = "") -> list[IconEntryDTO]:
        """
        Фильтрует иконки по выбранной категории и строке поиска (без учета регистра, RU/EN).
        """
        icons = self.get_all_icons()
        query = search_query.strip().lower()

        filtered: list[IconEntryDTO] = []
        for icon in icons:
            # 1. Фильтрация по категории
            if category and category != "all" and icon.category != category:
                continue

            # 2. Фильтрация по поисковому запросу
            if query:
                name_match = query in icon.name.lower()
                id_match = query in icon.id.lower()
                ru_match = any(query in kw.lower() for kw in icon.keywords_ru)
                en_match = any(query in kw.lower() for kw in icon.keywords_en)
                if not (name_match or id_match or ru_match or en_match):
                    continue

            filtered.append(icon)

        return filtered
