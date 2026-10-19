"""
tactile_fader.py | grandMA3 Tactile Stage Lighting Console Fader Widget
Custom QWidget implementation with illuminated groove rails, analog calibration tick marks,
tactile ribbed cap, and precision DMX readout (0-255).
"""

from __future__ import annotations

from ui.qt_compat import (
    HAS_QT, QWidget, QVBoxLayout, QLabel, QLineEdit, QInputDialog,
    Qt, Signal, QRectF, QPointF, QPainter, QColor, QPen, QBrush, QLinearGradient, QFont
)
from ui.styles import Theme


class TactileFader(QWidget if HAS_QT else object):
    """
    High-precision stage lighting fader emulating grandMA3 console hardware.
    Features illuminated LED track groove, tactile cap with center notch,
    analog calibration scale, and direct DMX value input.
    """
    valueChanged = Signal(int, int)  # (channel_id, new_value)

    def __init__(
        self,
        channel_id: int,
        label: str = "",
        initial_value: int = 0,
        is_master: bool = False,
        parent: QWidget | None = None,
    ):
        if not HAS_QT: return
        super().__init__(parent)
        self.channel_id = channel_id
        self.label_text = label if label else ("MASTER" if is_master else f"Ch {channel_id}")
        self.fixture_tag = ""
        self._value = max(0, min(255, initial_value))
        self.is_master = is_master
        self.is_dragging = False

        if is_master:
            self.setFixedWidth(68)
            self.setMinimumHeight(275)
            # The master is the dominant control and keeps its fixed height, so
            # it stays taller than the channel strip at every resolution.
            self.setMaximumHeight(275)
            self.cap_width = 44
            self.cap_height = 24
            self.track_width = 6
            self.top_margin = 22
            self.bottom_margin = 52
        else:
            self.setFixedWidth(52)
            # Scaled up for precise tactile response and grandMA3 pro console feel.
            # The ceiling stays below the master's 275px so the master remains
            # the dominant control at every resolution.
            self.setMinimumHeight(230)
            self.setMaximumHeight(255)
            self.cap_width = 32
            self.cap_height = 20
            self.track_width = 4
            self.top_margin = 18
            self.bottom_margin = 48

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, val: int) -> None:
        clamped = max(0, min(255, int(val)))
        if clamped != self._value:
            self._value = clamped
            self.update()
            self.valueChanged.emit(self.channel_id, self._value)

    def set_value_silent(self, val: int) -> None:
        """Sets fader value without emitting valueChanged signal (prevents loopback)."""
        clamped = max(0, min(255, int(val)))
        if clamped != self._value:
            self._value = clamped
            self.update()

    def set_fixture_tag(self, tag: str) -> None:
        """Sets descriptive patch tag (e.g. 'AL36-1:DIM') above fader."""
        if self.fixture_tag != tag:
            self.fixture_tag = tag
            self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            pos = event.position()
            # 1. Click on [X] quick-zero clear button
            if hasattr(self, "_btn_zero_rect") and self._btn_zero_rect.contains(pos):
                self.value = 0
                return

            # 2. Click on bottom value readout box -> open direct input dialog
            if hasattr(self, "_val_box_rect") and self._val_box_rect.contains(pos):
                self._open_direct_input()
                return

            self.is_dragging = True
            self._update_from_mouse_y(pos.y())

    def mouseMoveEvent(self, event) -> None:
        if self.is_dragging:
            self._update_from_mouse_y(event.position().y())

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.is_dragging = False

    def wheelEvent(self, event) -> None:
        """Adjust the value only with a modifier held; otherwise let it scroll.

        The faders sit inside a horizontally scrollable deck. Taking every wheel
        event here meant an ordinary scroll across the mixer silently rewrote
        DMX levels, so a stray trackpad gesture during a service changed the
        rig. Requiring Ctrl (or Shift) keeps wheel-to-scroll working and makes a
        value change deliberate.
        """
        modifiers = event.modifiers()
        if not (modifiers & (Qt.ControlModifier | Qt.ShiftModifier)):
            event.ignore()
            return

        delta = 5 if event.angleDelta().y() > 0 else -5
        self.value = self._value + delta
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        self._open_direct_input()

    def _open_direct_input(self) -> None:
        val, ok = QInputDialog.getInt(
            self,
            f"Set Nilai DMX: {self.label_text}",
            "Nilai DMX (0 - 255):",
            self._value,
            0,
            255,
            1,
        )
        if ok:
            self.value = val

    def _track_y_bounds(self) -> tuple[float, float]:
        """Returns (y_top, y_bottom) for the center of the cap."""
        y_top = float(self.top_margin + self.cap_height / 2)
        y_bottom = float(self.height() - self.bottom_margin - self.cap_height / 2)
        return y_top, y_bottom

    def _update_from_mouse_y(self, mouse_y: float) -> None:
        """Map a vertical position to a DMX value, ignoring presses outside the track.

        Only positions inside the track band change the value. A press in the
        strip below the track (where the value readout and the [X] button live)
        previously clamped to the track bottom and therefore wrote DMX 0, so
        aiming for a low level such as 1, 5 or 10 blacked the channel out
        instead. On the master fader that strip was 47 percent of the track, so
        the master could not be dragged below roughly DMX 63 at all.
        """
        y_top, y_bottom = self._track_y_bounds()
        track_len = y_bottom - y_top
        if track_len <= 0:
            return

        if mouse_y < y_top:
            self.value = 255
        elif mouse_y > y_bottom:
            # Outside the track: leave the value untouched rather than forcing 0.
            return
        else:
            norm = 1.0 - ((mouse_y - y_top) / track_len)
            self.value = int(round(norm * 255.0))

    def _cap_center_y(self) -> float:
        y_top, y_bottom = self._track_y_bounds()
        track_len = y_bottom - y_top
        norm = self._value / 255.0
        return y_bottom - (norm * track_len)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        y_top, y_bottom = self._track_y_bounds()

        # 1. Background fill
        painter.fillRect(0, 0, w, h, QColor(Theme.BG_ROOT))

        # 2. Header Label (Top)
        # The header states which fader this is: a channel number, a fixture tag,
        # or MASTER. That is a label, not a status, so it stays neutral. The
        # master is told apart by its taller column and its own value readout
        # below, which is where the amber carries meaning; painting the word
        # "MASTER" amber as well duplicated the signal with decoration.
        painter.setPen(QColor(Theme.TEXT_SECONDARY))
        if self.is_master:
            painter.setFont(QFont("Inter", 8, QFont.Bold))
            header_str = "MASTER"
        elif self.fixture_tag:
            painter.setFont(QFont("JetBrains Mono", 7, QFont.Bold))
            header_str = self.fixture_tag
        else:
            painter.setFont(QFont("Inter", 8, QFont.Bold))
            header_str = f"{self.channel_id}"

        painter.drawText(
            QRectF(1, 3, w - 2, 16),
            Qt.AlignCenter,
            header_str,
        )

        # Analog Calibration Scale Lines (Tick Marks) with Engraved Labels
        track_len = y_bottom - y_top
        scale_labels = {1.0: "FL", 0.5: "50", 0.0: "0"}
        painter.setFont(QFont("JetBrains Mono", 7, QFont.Bold))

        for step in [0.0, 0.25, 0.5, 0.75, 1.0]:
            ty = y_bottom - (step * track_len)
            is_major = step in (0.0, 0.5, 1.0)
            tick_w = 6 if is_major else 3
            if is_major:
                painter.setPen(QPen(QColor(Theme.TICK_MAJOR), 1.5))
            else:
                painter.setPen(QPen(QColor(Theme.TICK_MINOR), 1.0))

            # Left and Right ticks
            painter.drawLine(QPointF(cx - 14 - tick_w, ty), QPointF(cx - 14, ty))
            painter.drawLine(QPointF(cx + 14, ty), QPointF(cx + 14 + tick_w, ty))

            # Engraved analog scale label next to major ticks
            if is_major and step in scale_labels:
                lbl_str = scale_labels[step]
                painter.setPen(QColor(Theme.TEXT_MUTED))
                label_rect = QRectF(0, ty - 6, max(12.0, cx - 14), 12)
                painter.drawText(label_rect, Qt.AlignRight | Qt.AlignVCenter, lbl_str)

        # 4. Fader Groove / Recessed Track
        track_rect = QRectF(cx - self.track_width / 2.0, y_top - 2, self.track_width, track_len + 4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(Theme.SURFACE_TROUGH))
        painter.drawRoundedRect(track_rect, 2, 2)

        # 5. Illuminated LED Groove (Dual-Pass Backlit Light-Pipe Diffusion)
        cap_y = self._cap_center_y()
        led_height = y_bottom - cap_y
        if led_height > 0:
            accent_base = QColor(Theme.ACCENT_AMBER if self.is_master else Theme.ACCENT_CYAN)

            # Pass 1: Soft Outer Light-Pipe Glow Diffusion
            diffuse_color = QColor(accent_base)
            diffuse_color.setAlpha(65)
            diffuse_rect = QRectF(cx - (self.track_width / 2.0) - 1.5, cap_y, self.track_width + 3.0, led_height)
            painter.setBrush(QBrush(diffuse_color))
            painter.drawRoundedRect(diffuse_rect, 2.5, 2.5)

            # Pass 2: High-Luminance Core
            led_rect = QRectF(cx - (self.track_width / 2.0), cap_y, self.track_width, led_height)
            painter.setBrush(QBrush(accent_base))
            painter.drawRoundedRect(led_rect, 1.5, 1.5)

        # 6. Tactile Ribbed Fader Cap
        cap_left = cx - self.cap_width / 2.0
        cap_top = cap_y - self.cap_height / 2.0
        cap_rect = QRectF(cap_left, cap_top, self.cap_width, self.cap_height)

        # Gradient body
        grad = QLinearGradient(cap_left, cap_top, cap_left, cap_top + self.cap_height)
        grad.setColorAt(0.0, QColor(Theme.FADER_CAP_TOP))
        grad.setColorAt(0.5, QColor(Theme.SURFACE_CAP))
        grad.setColorAt(1.0, QColor(Theme.FADER_CAP_BOT))

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(Theme.BORDER_STRONG), 1))
        painter.drawRoundedRect(cap_rect, 3, 3)

        # Embossed Dual-Line Ridges (raised tactile physical grip texture)
        for offset_y in [-5, -2, 2, 5]:
            # Highlight upper ridge
            painter.setPen(QPen(QColor(Theme.FADER_RIB_HIGHLIGHT), 1))
            painter.drawLine(QPointF(cap_left + 3, cap_y + offset_y - 0.5), QPointF(cap_left + 8, cap_y + offset_y - 0.5))
            painter.drawLine(QPointF(cap_left + self.cap_width - 8, cap_y + offset_y - 0.5), QPointF(cap_left + self.cap_width - 3, cap_y + offset_y - 0.5))
            # Shadow lower ridge
            painter.setPen(QPen(QColor(Theme.FADER_RIB_SHADOW), 1))
            painter.drawLine(QPointF(cap_left + 3, cap_y + offset_y + 0.5), QPointF(cap_left + 8, cap_y + offset_y + 0.5))
            painter.drawLine(QPointF(cap_left + self.cap_width - 8, cap_y + offset_y + 0.5), QPointF(cap_left + self.cap_width - 3, cap_y + offset_y + 0.5))

        # Center White Indicator Notch Line
        painter.setPen(QPen(QColor(Theme.TEXT_PRIMARY), 2))
        painter.drawLine(
            QPointF(cap_left + 7, cap_y),
            QPointF(cap_left + self.cap_width - 7, cap_y),
        )

        # 7. Bottom Value Box (0-255 Readout)
        self._val_box_rect = QRectF(4, h - self.bottom_margin + 4, w - 8, 20)
        painter.setPen(QPen(QColor(Theme.BORDER_SUBTLE), 1))
        painter.setBrush(QColor(Theme.SURFACE_INPUT))
        painter.drawRoundedRect(self._val_box_rect, 3, 3)

        painter.setFont(QFont("JetBrains Mono", 9 if not self.is_master else 11, QFont.Bold))
        painter.setPen(QColor(Theme.ACCENT_AMBER if self.is_master else Theme.TEXT_PRIMARY))
        painter.drawText(self._val_box_rect, Qt.AlignCenter, f"{self._value}")

        # 8. [CLR] Quick-Zero Clear Button at bottom
        btn_w = 26 if self.is_master else 22
        self._btn_zero_rect = QRectF(cx - btn_w / 2.0, h - 20, btn_w, 15)
        if self._value > 0:
            painter.setBrush(QColor(Theme.FADER_CLEAR_BG))
            painter.setPen(QPen(QColor(Theme.COLOR_DANGER), 1))
            painter.drawRoundedRect(self._btn_zero_rect, 3, 3)
            painter.setFont(QFont("Inter", 8, QFont.Bold))
            painter.setPen(QColor(Theme.COLOR_DANGER))
            painter.drawText(self._btn_zero_rect, Qt.AlignCenter, "X")
        else:
            painter.setBrush(QColor(Theme.SURFACE_INPUT))
            painter.setPen(QPen(QColor(Theme.BORDER_SUBTLE), 1))
            painter.drawRoundedRect(self._btn_zero_rect, 3, 3)
            painter.setFont(QFont("Inter", 8, QFont.Bold))
            painter.setPen(QColor(Theme.TEXT_MUTED))
            painter.drawText(self._btn_zero_rect, Qt.AlignCenter, "X")

        painter.end()
