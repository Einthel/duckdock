"""
Тесты каталога иконок и кэша пиксмапов (IconCatalog & IconCache).
"""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from modules.deck.editor.icon_catalog import (
    IconCache,
    IconCatalog,
    IconCategoryDTO,
    IconEntryDTO,
)


@pytest.fixture(scope="session")
def qapp():
    """Единый экземпляр QApplication для тестов с GUI-объектами."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_icon_catalog_singleton(qapp):
    """Проверка синглтон-паттерна IconCatalog."""
    cat1 = IconCatalog()
    cat2 = IconCatalog()
    assert cat1 is cat2


def test_icon_catalog_builtin_categories(qapp):
    """Проверка наличия базовых категорий и подсчета иконок."""
    catalog = IconCatalog()
    categories = catalog.get_categories()
    cat_ids = [c.id for c in categories]

    expected = ["all", "system", "apps", "media", "glyphs", "custom"]
    for exp in expected:
        assert exp in cat_ids

    all_cat = next(c for c in categories if c.id == "all")
    assert all_cat.icon_count > 0
    assert all_cat.icon_count == len(catalog.get_all_icons())


def test_icon_catalog_bilingual_search(qapp):
    """
    Проверка поиска по ключевым словам на русском и английском:
    запросы 'звук' и 'volume' должны находить иконки громкости.
    """
    catalog = IconCatalog()

    # Поиск по-русски
    results_ru = catalog.get_icons(search_query="звук")
    assert len(results_ru) > 0
    ru_ids = [i.id for i in results_ru]
    assert "sys:vol_up" in ru_ids or "sys:mute" in ru_ids

    # Поиск по-английски
    results_en = catalog.get_icons(search_query="volume")
    assert len(results_en) > 0
    en_ids = [i.id for i in results_en]
    assert "sys:vol_up" in en_ids

    # Ищем дискорд
    results_discord_ru = catalog.get_icons(search_query="дискорд")
    assert any(i.id == "app:discord" for i in results_discord_ru)

    results_discord_en = catalog.get_icons(search_query="discord")
    assert any(i.id == "app:discord" for i in results_discord_en)


def test_icon_catalog_category_filtering(qapp):
    """Проверка фильтрации по категории."""
    catalog = IconCatalog()

    system_icons = catalog.get_icons(category="system")
    assert len(system_icons) > 0
    assert all(i.category == "system" for i in system_icons)

    apps_icons = catalog.get_icons(category="apps")
    assert len(apps_icons) > 0
    assert all(i.category == "apps" for i in apps_icons)

    media_icons = catalog.get_icons(category="media")
    assert len(media_icons) > 0
    assert all(i.category == "media" for i in media_icons)


def test_icon_cache_pixmap_caching(qapp):
    """Проверка кэширования в IconCache (повторный запрос возвращает тот же объект)."""
    cache = IconCache()
    pix1 = cache.get_pixmap("🔊", 48)
    assert not pix1.isNull()
    assert pix1.width() == 48

    pix2 = cache.get_pixmap("🔊", 48)
    # Тот же самый закэшированный QPixmap
    assert pix1 is pix2

    # Разный размер кэшируется отдельно
    pix3 = cache.get_pixmap("🔊", 36)
    assert pix3.width() == 36
    assert pix1 is not pix3


def test_icon_catalog_custom_icons_scan_and_save(qapp, tmp_path):
    """Проверка сохранения и сканирования пользовательских файлов."""
    catalog = IconCatalog()

    custom_dir = tmp_path / "custom_icons"
    with patch("modules.deck.editor.icon_catalog.CUSTOM_ICONS_DIR", custom_dir):
        # Создаем фиктивный PNG файл
        test_img = tmp_path / "test_icon.png"
        pix = QPixmap(32, 32)
        pix.fill()
        pix.save(str(test_img), "PNG")

        # Сохраняем в каталог
        saved_path = catalog.save_custom_icon(str(test_img))
        assert Path(saved_path).exists()
        assert str(custom_dir.name) in saved_path

        # Сканируем
        custom_entries = catalog.scan_custom_icons()
        assert any(e.name == "Test Icon" or "test_icon" in e.id for e in custom_entries)
