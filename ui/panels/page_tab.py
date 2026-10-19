"""
page_tab.py | Virtual Executor Page Tab (grandMA3 & QLC+ Style)
Provides tactile executor buttons for live stage lighting playback, flash buttons,
and auto-generated cue buttons received from PerformTab.
"""

from __future__ import annotations

from ui.qt_compat import (
    HAS_QT, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGroupBox, Qt, Signal, QColor, QFont
)
from ui.styles import Theme


class ExecutorButton(QPushButton if HAS_QT else object):
    """grandMA3-style rectangular playback executor button."""
    cue_triggered = Signal(dict)

    def __init__(self, cue_data: dict, parent: QWidget | None = None):
        if not HAS_QT: return
        super().__init__(parent)
        self.cue_data = cue_data
        self.is_active = False
        self.is_flash = cue_data.get("type") == "flash"

        self.setFixedSize(140, 90)
        label = cue_data.get("label", "Cue")
        self.setText(f"{label}\n[GO+]")
        self.setFont(QFont("Inter", 10, QFont.Bold))
        self.update_appearance()

        if self.is_flash:
            self.pressed.connect(self._on_flash_pressed)
            self.released.connect(self._on_flash_released)
        else:
            self.clicked.connect(self._toggle)

    def _toggle(self) -> None:
        self.is_active = not self.is_active
        self.update_appearance()
        self.cue_triggered.emit({**self.cue_data, "active": self.is_active})

    def _on_flash_pressed(self) -> None:
        self.is_active = True
        self.update_appearance()
        self.cue_triggered.emit({**self.cue_data, "active": True})

    def _on_flash_released(self) -> None:
        self.is_active = False
        self.update_appearance()
        self.cue_triggered.emit({**self.cue_data, "active": False})

    def update_appearance(self) -> None:
        if self.is_flash:
            border = Theme.COLOR_WARNING
            bg = Theme.COLOR_WARNING if self.is_active else Theme.STATUS_WARNING_BG
            text_color = Theme.BG_ROOT if self.is_active else Theme.COLOR_WARNING
        else:
            border = Theme.ACCENT_AMBER if self.is_active else Theme.BORDER_STRONG
            bg = Theme.STATUS_EXECUTOR_ACTIVE if self.is_active else Theme.BG_SURFACE
            text_color = Theme.TEXT_PRIMARY

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: 2px solid {border};
                border-radius: 6px;
                color: {text_color};
                font-weight: bold;
                padding: 6px;
            }}
            QPushButton:hover {{
                border-color: {Theme.ACCENT_CYAN};
            }}
        """)


class PageTab(QWidget if HAS_QT else object):
    """Virtual Executor Grid Page."""
    cue_activated = Signal(dict)

    def __init__(self, parent: QWidget | None = None):
        if not HAS_QT: return
        super().__init__(parent)
        self.executor_buttons: list[ExecutorButton] = []
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(12)

        # Top Bar (Retained as internal attributes for automated tests)
        self.btn_clear_page = QPushButton("CLEAR PAGE")
        self.btn_clear_page.setVisible(False)
        self.btn_clear_page.clicked.connect(self._clear_executors)

        # Scrollable Executor Grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Theme.BG_ROOT};
                border: 1px solid {Theme.BORDER_SUBTLE};
                border-radius: 6px;
            }}
        """)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(14, 14, 14, 14)
        self.grid_layout.setSpacing(14)
        scroll.setWidget(self.grid_container)

        main_layout.addWidget(scroll, 1)

    def load_cues(self, cues: list[dict]) -> None:
        """Replace the executor page with the given cues.

        The page is cleared first so an export replaces what is shown. Without
        this, every GENERATE EXECUTORS run appended another copy, so pressing it
        three times left three identical sets of executor buttons stacked on the
        grid.

        Non-object entries are skipped rather than passed to ExecutorButton,
        which dereferences .get() and would raise on an int or a string. The
        project loader now rejects such files, but this method is also reachable
        directly, so it stays defensive on its own.
        """
        self._clear_executors()
        for cue in cues:
            if not isinstance(cue, dict):
                continue
            btn = ExecutorButton(cue, self.grid_container)
            btn.cue_triggered.connect(self._on_cue_triggered)
            self.executor_buttons.append(btn)

            idx = len(self.executor_buttons) - 1
            row = idx // 6
            col = idx % 6
            self.grid_layout.addWidget(btn, row, col)

    def _clear_executors(self) -> None:
        # Release any flash that is still held before destroying its button.
        # A flash is momentary: pressed sends active=True and the release sends
        # active=False, which restores the look that was running. When the page
        # is replaced (CLEAR PAGE, or a new GENERATE EXECUTORS) while the flash is
        # still down, the release never arrives, so the stage stayed lit with no
        # executor left to turn it off. Emit the release here so the console
        # restores the pre-flash look, matching what lifting the button does.
        for btn in self.executor_buttons:
            if getattr(btn, "is_flash", False) and getattr(btn, "is_active", False):
                btn.is_active = False
                self.cue_activated.emit({**btn.cue_data, "active": False})
                break
        for btn in self.executor_buttons:
            self.grid_layout.removeWidget(btn)
            btn.deleteLater()
        self.executor_buttons.clear()

    def _on_cue_triggered(self, cue_info: dict) -> None:
        self.cue_activated.emit(cue_info)
