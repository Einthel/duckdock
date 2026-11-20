"""
Верхняя панель управления DuckDeck (HeaderBar).
"""
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from modules.deck.models import DeckPageConfig
from core.i18n import t


class HeaderBar(QFrame):
    """
    Верхняя панель управления DuckDeck (высота 48 px).
    Включает:
      - Полосу кнопок-пилюль страниц/профилей (слева).
      - Текстовый индикатор статуса фоновых процессов (по центру).
      - Кнопку быстрой перезагрузки JSON конфигурации (справа).
    """
    page_selected = Signal(str)    # page_id
    reload_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("DeckHeaderBar")
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedHeight(48)
        self.setFixedWidth(944)

        self._pill_buttons: Dict[str, QPushButton] = {}
        self._active_page_id: str = ""

        # Таймер угасания строки статуса
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._clear_status)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # Контейнер кнопок-пилюль
        self.pills_container = QWidget(self)
        self.pills_container.setFocusPolicy(Qt.NoFocus)
        self.pills_layout = QHBoxLayout(self.pills_container)
        self.pills_layout.setContentsMargins(0, 0, 0, 0)
        self.pills_layout.setSpacing(6)
        layout.addWidget(self.pills_container, 0, Qt.AlignLeft)

        # Центральный индикатор статуса
        self.lbl_status = QLabel("", self)
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setFocusPolicy(Qt.NoFocus)
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.lbl_status, 1, Qt.AlignCenter)

        # Кнопка перезагрузки JSON конфигурации
        self.btn_reload = QPushButton("🔄", self)
        self.btn_reload.setFocusPolicy(Qt.NoFocus)
        self.btn_reload.setFixedSize(36, 36)
        self.btn_reload.setProperty("class", "deck-reload-btn")
        self.btn_reload.setToolTip(t("deck.header.reload_tooltip"))
        self.btn_reload.clicked.connect(self.reload_requested.emit)
        layout.addWidget(self.btn_reload, 0, Qt.AlignRight)

    def retranslate_ui(self) -> None:
        """Обновление тултипов панели."""
        if hasattr(self, "btn_reload"):
            self.btn_reload.setToolTip(t("deck.header.reload_tooltip"))

    def set_pages(self, pages: List[DeckPageConfig], active_page_id: str) -> None:
        """Формирует кнопки страниц-профилей."""
        # Очистка предыдущих кнопок
        for btn in self._pill_buttons.values():
            btn.setParent(None)
            btn.deleteLater()
        self._pill_buttons.clear()

        while self.pills_layout.count():
            item = self.pills_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._active_page_id = active_page_id

        for page in pages:
            btn = QPushButton(page.name, self.pills_container)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setProperty("class", "deck-pill-btn")
            btn.setProperty("active", "true" if page.id == active_page_id else "false")
            btn.clicked.connect(lambda checked=False, pid=page.id: self.page_selected.emit(pid))
            self.pills_layout.addWidget(btn)
            self._pill_buttons[page.id] = btn

    def set_active_page(self, page_id: str) -> None:
        """Переключает активную вкладку страницы."""
        self._active_page_id = page_id
        for pid, btn in self._pill_buttons.items():
            is_act = (pid == page_id)
            btn.setProperty("active", "true" if is_act else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def set_status(self, text: str, timeout_ms: int = 4000) -> None:
        """Отображает угасающее статусное сообщение."""
        self.lbl_status.setText(text)
        self._status_timer.stop()
        if text and timeout_ms > 0:
            self._status_timer.start(timeout_ms)

    def _clear_status(self) -> None:
        self.lbl_status.setText("")

    def cleanup(self) -> None:
        """Очистка таймеров шапки."""
        if self._status_timer.isActive():
            self._status_timer.stop()


__all__ = ["HeaderBar"]
