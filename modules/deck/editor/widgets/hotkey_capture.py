"""
Интерактивная кнопка захвата сочетаний клавиш (HotkeyCaptureButton).
Поддерживает режим модального перехвата клавиатуры (grabKeyboard), распознавание модификаторов,
отмену по Escape, очистку по Delete/Backspace и локализацию по стандарту Dark Obsidian.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFocusEvent, QKeyEvent, QKeySequence
from PySide6.QtWidgets import QPushButton, QWidget

from core.i18n import t
from modules.deck.editor.styles import INPUT_HEIGHT


class HotkeyCaptureButton(QPushButton):
    """
    Кнопка захвата шорткатов клавиатуры с визуальным статусом ожидания и акцентной подсветкой.
    """

    hotkey_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("hotkeyCaptureButton")
        self.setProperty("class", "HotkeyCaptureButton")
        self.setProperty("capturing", "false")
        self.setFixedHeight(INPUT_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)

        self._capturing: bool = False
        self._current_hotkey: str = ""

        self._update_display_text()
        self.clicked.connect(self._on_clicked)

    def _update_display_text(self) -> None:
        """
        Обновляет текст кнопки в зависимости от текущего состояния (захват / заданный хоткей / плейсхолдер).
        """
        if self._capturing:
            self.setText(t("deck.editor.inspector.hotkey.press_shortcut"))
        elif self._current_hotkey:
            self.setText(f"{self._current_hotkey}  ▾")
        else:
            self.setText(f"{t('deck.editor.inspector.hotkey.click_to_assign')}  ▾")

    def retranslate_ui(self) -> None:
        """
        Обновляет локализованный текст кнопки, строго сохраняя назначенный хоткей.
        """
        self._update_display_text()

    def set_hotkey(self, hotkey: str) -> None:
        """
        Устанавливает строковое значение хоткея (например, 'Ctrl+Shift+D').
        """
        self._current_hotkey = hotkey.strip()
        if self._capturing:
            self.cancel_capture()
        else:
            self._update_display_text()

    def get_hotkey(self) -> str:
        """
        Возвращает текущую строку назначенного хоткея.
        """
        return self._current_hotkey

    def is_capturing(self) -> bool:
        """
        Возвращает True, если кнопка находится в активном режиме перехвата клавиш.
        """
        return self._capturing

    def _on_clicked(self) -> None:
        if self._capturing:
            self.cancel_capture()
        else:
            self.start_capture()

    def start_capture(self) -> None:
        """
        Переводит кнопку в режим ожидания нажатия комбинации клавиш.
        """
        self._capturing = True
        self.setProperty("capturing", "true")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

        self._update_display_text()
        try:
            self.grabKeyboard()
        except Exception:
            pass

    def cancel_capture(self) -> None:
        """
        Отменяет режим захвата без сохранения изменений.
        """
        if not self._capturing:
            return
        self._capturing = False
        self.setProperty("capturing", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

        try:
            self.releaseKeyboard()
        except Exception:
            pass

        self._update_display_text()

    def finish_capture(self, new_hotkey: str) -> None:
        """
        Завершает режим захвата с сохранением новой комбинации и эмиссией сигнала.
        """
        self._capturing = False
        self.setProperty("capturing", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

        try:
            self.releaseKeyboard()
        except Exception:
            pass

        self._current_hotkey = new_hotkey
        self._update_display_text()
        self.hotkey_changed.emit(self._current_hotkey)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Перехват нажатий клавиш клавиатуры при активном захвате.
        """
        if not self._capturing:
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()

        # Игнорируем нажатия отдельных клавиш-модификаторов в ожидании основной клавиши
        if key in (
            Qt.Key_Control,
            Qt.Key_Shift,
            Qt.Key_Alt,
            Qt.Key_Meta,
        ):
            event.accept()
            return

        # Нажатие Escape отменяет захват без изменений
        if key == Qt.Key_Escape:
            self.cancel_capture()
            event.accept()
            return

        # Backspace или Delete очищают назначенный хоткей
        if key in (Qt.Key_Backspace, Qt.Key_Delete):
            self.finish_capture("")
            event.accept()
            return

        # Формирование канонической комбинации клавиш
        parts: list[str] = []
        if modifiers & Qt.ControlModifier:
            parts.append("Ctrl")
        if modifiers & Qt.AltModifier:
            parts.append("Alt")
        if modifiers & Qt.ShiftModifier:
            parts.append("Shift")
        if modifiers & Qt.MetaModifier:
            parts.append("Win")

        # Определение строкового представления клавиши
        key_str = ""
        if Qt.Key_A <= key <= Qt.Key_Z:
            key_str = chr(key)
        elif Qt.Key_0 <= key <= Qt.Key_9:
            key_str = chr(key)
        elif Qt.Key_F1 <= key <= Qt.Key_F24:
            key_str = f"F{key - Qt.Key_F1 + 1}"
        else:
            seq_str = QKeySequence(key).toString()
            if seq_str:
                key_str = seq_str
            else:
                key_str = event.text().upper()

        if not key_str:
            event.accept()
            return

        # Если клавиша уже входит в модификаторы (дубликат), убираем ее
        if key_str in parts:
            combo = "+".join(parts)
        else:
            combo = "+".join(parts + [key_str]) if parts else key_str

        self.finish_capture(combo)
        event.accept()

    def focusOutEvent(self, event: QFocusEvent) -> None:
        """
        При потере фокуса во время захвата безопасно отменяем перехват.
        """
        if self._capturing:
            self.cancel_capture()
        super().focusOutEvent(event)
