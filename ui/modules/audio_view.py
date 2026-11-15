"""
Сенсорный аудиомикшер DuckDock (Windows Core Audio Mixer).
Оптимизирован для тач-управления на 7" экране (800x600 / 1024x600).
Все элементы управления имеют Qt.NoFocus для сохранения фокуса на основном мониторе.
"""
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QSlider, QScrollArea, QScroller, QFileIconProvider, QStyle
)
from PySide6.QtCore import Qt, QTimer, QFileInfo, QSize
from PySide6.QtGui import QIcon

from core.audio_manager import AudioManager, AudioSessionInfo
from core.event_bus import bus

AUDIO_QSS = """
QFrame.audio-master-card {
    background-color: #161b26;
    border: 1px solid #232b3e;
    border-radius: 12px;
    padding: 12px 16px;
}

QFrame.audio-session-card {
    background-color: #161b26;
    border: 1px solid #1e2638;
    border-radius: 12px;
    padding: 8px 14px;
}

QLabel.section-header {
    color: #94a3b8;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 1px;
    text-transform: uppercase;
}

QLabel.card-title {
    color: #f8fafc;
    font-size: 14px;
    font-weight: bold;
}

QLabel.card-subtitle {
    color: #64748b;
    font-size: 11px;
}

QLabel.vol-badge {
    color: #38bdf8;
    font-size: 15px;
    font-weight: bold;
    min-width: 44px;
    text-align: right;
}

QPushButton.mute-btn {
    background-color: #1e2430;
    color: #94a3b8;
    border: 1px solid #2d3748;
    border-radius: 10px;
    font-size: 18px;
    min-width: 52px;
    max-width: 52px;
    min-height: 44px;
    max-height: 44px;
}

QPushButton.mute-btn:pressed {
    background-color: #2b3547;
    border-color: #3b82f6;
    color: #ffffff;
}

QPushButton.mute-btn[muted="true"] {
    background-color: #dc2626;
    color: #ffffff;
    border-color: #ef4444;
}

QPushButton.master-mute-btn {
    background-color: #1e2430;
    color: #38bdf8;
    border: 1px solid #2d3748;
    border-radius: 10px;
    font-size: 15px;
    font-weight: bold;
    min-width: 90px;
    min-height: 44px;
    padding: 0 10px;
}

QPushButton.master-mute-btn:pressed {
    background-color: #2b3547;
    border-color: #38bdf8;
}

QPushButton.master-mute-btn[muted="true"] {
    background-color: #dc2626;
    color: #ffffff;
    border-color: #ef4444;
}

QPushButton.refresh-btn {
    background-color: #1e2430;
    color: #94a3b8;
    border: 1px solid #2d3748;
    border-radius: 8px;
    font-size: 14px;
    padding: 4px 10px;
}

QPushButton.refresh-btn:pressed {
    background-color: #334155;
    color: #f8fafc;
}

/* Стилизация сенсорных слайдеров (TouchSlider) */
QSlider::groove:horizontal {
    background: #1e293b;
    height: 10px;
    border-radius: 5px;
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #38bdf8);
    height: 10px;
    border-radius: 5px;
}

QSlider::sub-page:horizontal:disabled {
    background: #475569;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 3px solid #38bdf8;
    width: 26px;
    margin-top: -8px;
    margin-bottom: -8px;
    border-radius: 13px;
}

QSlider::handle:horizontal:hover {
    background: #e2e8f0;
    border-color: #60a5fa;
    width: 28px;
    margin-top: -9px;
    margin-bottom: -9px;
    border-radius: 14px;
}

/* Скроллбар для списка сессий */
QScrollArea {
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    background: #0b0d13;
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #283347;
    min-height: 24px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #3b82f6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


class TouchSlider(QSlider):
    """
    Слайдер с мгновенной реакцией на касание в любой точке трека
    и политикой Qt.NoFocus для сохранения фокуса на основном экране.
    """

    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setFocusPolicy(Qt.NoFocus)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            val = QStyle.sliderValueFromPosition(
                self.minimum(),
                self.maximum(),
                int(event.position().x()),
                self.width()
            )
            self.setValue(val)
            event.accept()
        super().mousePressEvent(event)


class SessionCardWidget(QFrame):
    """Карточка отдельной аудиосессии приложения."""

    def __init__(self, session: AudioSessionInfo, icon_provider: QFileIconProvider, parent=None):
        super().__init__(parent)
        self.session = session
        self.icon_provider = icon_provider
        self.pid = session.pid

        self.setProperty("class", "audio-session-card")
        self.setFixedHeight(68)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # 1. Иконка приложения
        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(36, 36)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self._update_icon()
        layout.addWidget(self.lbl_icon)

        # 2. Имя и описание приложения (фиксированная колонка)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignVCenter)

        self.lbl_name = QLabel(self.session.name)
        self.lbl_name.setProperty("class", "card-title")
        info_layout.addWidget(self.lbl_name)

        sub_info = self.session.process_name if self.session.pid != 0 else "Windows System"
        self.lbl_sub = QLabel(sub_info)
        self.lbl_sub.setProperty("class", "card-subtitle")
        info_layout.addWidget(self.lbl_sub)

        # Фиксированная ширина колонки имени для ровной сетки
        info_container = QWidget()
        info_container.setLayout(info_layout)
        info_container.setFixedWidth(170)
        layout.addWidget(info_container)

        # 3. Сенсорный слайдер громкости
        self.slider = TouchSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(int(round(self.session.volume * 100)))
        layout.addWidget(self.slider, stretch=1)

        # 4. Процент громкости
        self.lbl_vol = QLabel(f"{int(round(self.session.volume * 100))}%")
        self.lbl_vol.setProperty("class", "vol-badge")
        self.lbl_vol.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.lbl_vol)

        # 5. Кнопка Mute (Touch Hitbox 52x44px)
        self.btn_mute = QPushButton("🔇" if self.session.is_muted else "🔊")
        self.btn_mute.setProperty("class", "mute-btn")
        self.btn_mute.setProperty("muted", "true" if self.session.is_muted else "false")
        self.btn_mute.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.btn_mute)

    def _update_icon(self):
        icon_set = False
        if self.session.exe_path:
            try:
                info = QFileInfo(self.session.exe_path)
                if info.exists():
                    icon = self.icon_provider.icon(info)
                    if not icon.isNull():
                        pixmap = icon.pixmap(32, 32)
                        self.lbl_icon.setPixmap(pixmap)
                        icon_set = True
            except Exception:
                pass

        if not icon_set:
            emoji = "🔊" if self.session.pid == 0 else "🎵"
            self.lbl_icon.setText(emoji)
            self.lbl_icon.setStyleSheet("font-size: 20px;")

    def update_state(self, session: AudioSessionInfo):
        """Обновление состояния без пересоздания виджета."""
        self.session = session
        if not self.slider.isSliderDown():
            vol_val = int(round(session.volume * 100))
            self.slider.setValue(vol_val)
            self.lbl_vol.setText(f"{vol_val}%")

        self.btn_mute.setText("🔇" if session.is_muted else "🔊")
        self.btn_mute.setProperty("muted", "true" if session.is_muted else "false")
        self.btn_mute.style().unpolish(self.btn_mute)
        self.btn_mute.style().polish(self.btn_mute)


class AudioMixerView(QWidget):
    """
    Полнофункциональный сенсорный экран управления аудиосистемой Windows.
    Включает Master Volume и список активных сессий приложений.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio_manager = AudioManager()
        self.icon_provider = QFileIconProvider()
        self._session_cards: Dict[Optional[int], SessionCardWidget] = {}

        self.setStyleSheet(AUDIO_QSS)
        self._init_ui()
        self._refresh_master()
        self._refresh_sessions(force_rebuild=True)

        # Подписка на изменение системного устройства воспроизведения
        self._eventbus_connected = False
        self._subscribe_eventbus()

        # Фоновый таймер периодического опроса аудиосессий (раз в 1.5 сек)
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(1500)
        self.poll_timer.timeout.connect(self._on_poll_tick)
        self.poll_timer.start()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 14, 16, 14)
        root_layout.setSpacing(12)

        # --- 1. Шапка экрана ---
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        lbl_title = QLabel("WINDOWS CORE AUDIO MIXER")
        lbl_title.setStyleSheet("color: #f1f5f9; font-size: 16px; font-weight: bold;")
        title_box.addWidget(lbl_title)

        self.lbl_device = QLabel(self.audio_manager.get_master_device_name())
        self.lbl_device.setStyleSheet("color: #64748b; font-size: 12px;")
        title_box.addWidget(self.lbl_device)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        current_dev = self.audio_manager.get_master_device_name()
        self.btn_switch_device = QPushButton(self._format_device_button_text(current_dev))
        self.btn_switch_device.setProperty("class", "refresh-btn")
        self.btn_switch_device.setFixedHeight(40)
        self.btn_switch_device.setMinimumWidth(140)
        self.btn_switch_device.setFocusPolicy(Qt.NoFocus)
        self.btn_switch_device.clicked.connect(self._on_switch_device_clicked)
        header_layout.addWidget(self.btn_switch_device)

        self.btn_refresh = QPushButton("🔄 Обновить")
        self.btn_refresh.setProperty("class", "refresh-btn")
        self.btn_refresh.setFocusPolicy(Qt.NoFocus)
        self.btn_refresh.clicked.connect(lambda: self._refresh_sessions(force_rebuild=True))
        header_layout.addWidget(self.btn_refresh)

        root_layout.addLayout(header_layout)

        # --- 2. Карточка Master Volume ---
        master_card = QFrame()
        master_card.setProperty("class", "audio-master-card")
        m_layout = QVBoxLayout(master_card)
        m_layout.setSpacing(8)

        m_header = QHBoxLayout()
        lbl_m_title = QLabel("🔊 ОБЩАЯ ГРОМКОСТЬ (MASTER VOLUME)")
        lbl_m_title.setProperty("class", "section-header")
        m_header.addWidget(lbl_m_title)
        m_header.addStretch()

        self.lbl_master_vol = QLabel("100%")
        self.lbl_master_vol.setStyleSheet("color: #38bdf8; font-size: 20px; font-weight: bold;")
        m_header.addWidget(self.lbl_master_vol)
        m_layout.addLayout(m_header)

        m_controls = QHBoxLayout()
        m_controls.setSpacing(14)

        self.master_slider = TouchSlider(Qt.Horizontal)
        self.master_slider.setRange(0, 100)
        self.master_slider.setFixedHeight(40)
        self.master_slider.valueChanged.connect(self._on_master_slider_changed)
        m_controls.addWidget(self.master_slider, stretch=1)

        self.btn_master_mute = QPushButton("🔊 ЗВУК")
        self.btn_master_mute.setProperty("class", "master-mute-btn")
        self.btn_master_mute.setFocusPolicy(Qt.NoFocus)
        self.btn_master_mute.clicked.connect(self._on_master_mute_clicked)
        m_controls.addWidget(self.btn_master_mute)

        m_layout.addLayout(m_controls)
        root_layout.addWidget(master_card)

        # --- 3. Секция активных приложений ---
        app_header = QHBoxLayout()
        self.lbl_sessions_count = QLabel("АКТИВНЫЕ ПРИЛОЖЕНИЯ И ПОТОКИ (0)")
        self.lbl_sessions_count.setProperty("class", "section-header")
        app_header.addWidget(self.lbl_sessions_count)
        app_header.addStretch()
        root_layout.addLayout(app_header)

        # QScrollArea со скроллером жестов
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFocusPolicy(Qt.NoFocus)
        QScroller.grabGesture(self.scroll_area.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)

        self.sessions_container = QWidget()
        self.sessions_layout = QVBoxLayout(self.sessions_container)
        self.sessions_layout.setContentsMargins(0, 0, 4, 0)
        self.sessions_layout.setSpacing(8)
        self.sessions_layout.addStretch()

        self.scroll_area.setWidget(self.sessions_container)
        root_layout.addWidget(self.scroll_area, stretch=1)

    def _refresh_master(self):
        """Синхронизация данных Master Volume из ядра системы."""
        vol = self.audio_manager.get_master_volume()
        muted = self.audio_manager.is_master_muted()
        int_val = int(round(vol * 100))

        if not self.master_slider.isSliderDown():
            self.master_slider.setValue(int_val)
            self.lbl_master_vol.setText(f"{int_val}%")

        self.btn_master_mute.setText("🔇 MUTE" if muted else "🔊 ЗВУК")
        self.btn_master_mute.setProperty("muted", "true" if muted else "false")
        self.btn_master_mute.style().unpolish(self.btn_master_mute)
        self.btn_master_mute.style().polish(self.btn_master_mute)

    def _on_master_slider_changed(self, value: int):
        level = value / 100.0
        self.lbl_master_vol.setText(f"{value}%")
        self.audio_manager.set_master_volume(level)
        bus.master_volume_changed.emit(level, self.audio_manager.is_master_muted())

    def _on_master_mute_clicked(self):
        new_mute = self.audio_manager.toggle_master_mute()
        self.btn_master_mute.setText("🔇 MUTE" if new_mute else "🔊 ЗВУК")
        self.btn_master_mute.setProperty("muted", "true" if new_mute else "false")
        self.btn_master_mute.style().unpolish(self.btn_master_mute)
        self.btn_master_mute.style().polish(self.btn_master_mute)
        bus.master_volume_changed.emit(self.audio_manager.get_master_volume(), new_mute)

    def _on_poll_tick(self):
        """Периодическое обновление состояния мастер-звука и сессий."""
        self._refresh_master()
        self._refresh_sessions(force_rebuild=False)

    def _refresh_sessions(self, force_rebuild: bool = False):
        """Синхронизация карточек приложений."""
        sessions = self.audio_manager.get_sessions()
        self.lbl_sessions_count.setText(f"АКТИВНЫЕ ПРИЛОЖЕНИЯ И ПОТОКИ ({len(sessions)})")

        current_pids = {s.pid for s in sessions}
        cached_pids = set(self._session_cards.keys())

        # Если состав сессий изменился или запрошен force_rebuild - перестраиваем
        if force_rebuild or current_pids != cached_pids:
            self._rebuild_sessions_ui(sessions)
        else:
            # Бесшовное обновление данных без перерисовки виджетов
            for s in sessions:
                card = self._session_cards.get(s.pid)
                if card:
                    card.update_state(s)

    def _rebuild_sessions_ui(self, sessions):
        """Полная пересборка виджетов при изменении запущенных приложений."""
        # Очищаем текущий лэйаут
        for card in self._session_cards.values():
            card.setParent(None)
            card.deleteLater()
        self._session_cards.clear()

        # Удаляем существующие элементы из layout
        while self.sessions_layout.count():
            item = self.sessions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for s in sessions:
            card = SessionCardWidget(s, self.icon_provider, self.sessions_container)
            card.slider.valueChanged.connect(
                lambda val, pid=s.pid, c=card: self._on_session_slider_changed(pid, val, c)
            )
            card.btn_mute.clicked.connect(
                lambda pid=s.pid, c=card: self._on_session_mute_clicked(pid, c)
            )
            self.sessions_layout.addWidget(card)
            self._session_cards[s.pid] = card

        self.sessions_layout.addStretch()

    def _on_session_slider_changed(self, pid: Optional[int], value: int, card: SessionCardWidget):
        level = value / 100.0
        card.lbl_vol.setText(f"{value}%")
        self.audio_manager.set_session_volume(pid, level)
        bus.session_volume_changed.emit(pid or 0, level, card.session.is_muted)

    def _on_session_mute_clicked(self, pid: Optional[int], card: SessionCardWidget):
        new_mute = self.audio_manager.toggle_session_mute(pid)
        card.session.is_muted = new_mute
        card.btn_mute.setText("🔇" if new_mute else "🔊")
        card.btn_mute.setProperty("muted", "true" if new_mute else "false")
        card.btn_mute.style().unpolish(card.btn_mute)
        card.btn_mute.style().polish(card.btn_mute)
        bus.session_volume_changed.emit(pid or 0, card.slider.value() / 100.0, new_mute)

    def _format_device_button_text(self, device_name: str) -> str:
        """Формирование подписи кнопки с адаптивной иконкой наушников/динамиков."""
        is_headphones = any(k in (device_name or "").lower() for k in ["наушники", "headphone", "headset"])
        icon = "🎧" if is_headphones else "🔊"
        clean_name = device_name or "Аудиовыход"
        return f"{icon} {clean_name}"

    def _on_switch_device_clicked(self) -> None:
        """Переключение устройства воспроизведения между целевыми устройствами."""
        self.audio_manager.toggle_playback_device(["Наушники", "Динамики"])

    def _on_playback_device_changed(self, device_name: str, device_id: str) -> None:
        """Слот реакции на смену устройства вывода по шине событий."""
        self.lbl_device.setText(device_name)
        if hasattr(self, "btn_switch_device"):
            self.btn_switch_device.setText(self._format_device_button_text(device_name))
        self._refresh_master()
        self._refresh_sessions(force_rebuild=True)

    def _subscribe_eventbus(self) -> None:
        """Безопасная подписка на сигналы EventBus."""
        if getattr(self, "_eventbus_connected", False):
            return
        try:
            bus.playback_device_changed.connect(self._on_playback_device_changed)
            self._eventbus_connected = True
        except Exception:
            pass

    def cleanup(self) -> None:
        """Освобождение таймеров и безопасная отписка от EventBus."""
        if hasattr(self, "poll_timer") and self.poll_timer.isActive():
            self.poll_timer.stop()
        if getattr(self, "_eventbus_connected", False):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                try:
                    bus.playback_device_changed.disconnect(self._on_playback_device_changed)
                except Exception:
                    pass
            self._eventbus_connected = False

    def closeEvent(self, event) -> None:
        self.cleanup()
        super().closeEvent(event)
