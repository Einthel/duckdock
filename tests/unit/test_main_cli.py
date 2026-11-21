"""
Модульные тесты парсера аргументов командной строки и интеграции лончера main.py.
Проверяют:
  - Парсинг флагов --editor и --deck-editor.
  - Поведение по умолчанию (запуск основного шелла).
  - Инициализацию и запуск DeckEditorWindow при наличии флага --editor.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import main


def test_parse_args_defaults():
    """По умолчанию флаг editor выключен."""
    args = main.parse_args([])
    assert args.editor is False


def test_parse_args_editor_flag():
    """Флаг --editor активирует режим редактора."""
    args = main.parse_args(["--editor"])
    assert args.editor is True


def test_parse_args_deck_editor_flag():
    """Алиас --deck-editor также активирует режим редактора."""
    args = main.parse_args(["--deck-editor"])
    assert args.editor is True


def test_main_editor_launch_flow(monkeypatch, qapp):
    """Проверка вызова DeckEditorWindow и load_demo_profile_into_window при флаге --editor."""
    mock_window = MagicMock()
    mock_editor_class = MagicMock(return_value=mock_window)
    mock_load_demo = MagicMock()

    monkeypatch.setattr("modules.deck.editor.window.DeckEditorWindow", mock_editor_class)
    monkeypatch.setattr("modules.deck.editor.demo_data.load_demo_profile_into_window", mock_load_demo)
    monkeypatch.setattr(qapp, "exec", MagicMock(return_value=0))

    exit_code = main.main(["--editor"])

    assert exit_code == 0
    mock_editor_class.assert_called_once()
    mock_load_demo.assert_called_once_with(mock_window)
    mock_window._center_on_primary_screen.assert_called_once()
    mock_window.show.assert_called_once()
