"""
mixer_tab.py | grandMA3 513-Fader Industrial Console Mixer Desk
Features 1 Grand Master + 512 DMX channels utilizing tactile fader widgets
with illuminated groove rails, analog calibration scale marks, and smooth horizontal scrolling.
"""

from __future__ import annotations

from ui.qt_compat import (
    HAS_QT, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSplitter, Qt, Signal
)
from ui.styles import Theme
from ui.widgets.tactile_fader import TactileFader


class MixerTab(QWidget if HAS_QT else object):
    """
    Mixer Tab: 513 physical-style console faders (1 Grand Master + 512 DMX Output Channels).
    Emulates the hardware touch and lighting of grandMA3 lighting consoles.
    """
    fader_changed = Signal(int, int)  # (channel_id, value)

    def __init__(self, project_state=None, parent: QWidget | None = None):
        if not HAS_QT: return
        super().__init__(parent)
        self.project_state = project_state
        self.faders: dict[int, TactileFader] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(12)

        # Top Control Bar (Clean & Focused on Stage Safety)
        top_bar = QHBoxLayout()

        top_bar.addStretch()

        self.btn_reset_all = QPushButton("RESET DMX")
        self.btn_reset_all.clicked.connect(self._reset_dmx_channels)
        top_bar.addWidget(self.btn_reset_all)

        # Retained as internal attributes for backwards compatibility
        self.btn_full_master = QPushButton("FULL MASTER")
        self.btn_full_master.clicked.connect(lambda: self.set_channel_value(0, 255))
        self.btn_refresh = QPushButton("REFRESH")
        self.btn_refresh.clicked.connect(self.refresh_display)

        main_layout.addLayout(top_bar)

        # Faders Container Area (Master on left, Channels scrollable on right)
        desk_container = QHBoxLayout()
        desk_container.setSpacing(10)

        # 1. Master Fader Column (Fixed, Anchored on Far Left)
        master_frame = QFrame()
        # Neutral frame. The column used to carry a 2px amber outline plus amber
        # heading text, which broke the project's own rule that a coloured
        # element is a solid block, never an outline, and spent the accent on
        # chrome instead of meaning. The amber now appears only where it says
        # something: on the master's own value readout, below, marking the one
        # fader that scales every other.
        master_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.BG_SURFACE};
                border: 1px solid {Theme.BORDER_SUBTLE};
                border-radius: 6px;
                padding: 4px;
            }}
        """)
        master_layout = QVBoxLayout(master_frame)
        master_layout.setContentsMargins(6, 6, 6, 6)

        lbl_m = QLabel("GRAND MASTER")
        lbl_m.setAlignment(Qt.AlignCenter)
        lbl_m.setStyleSheet(
            f"font-size: 10px; font-weight: 800; color: {Theme.TEXT_SECONDARY};")
        master_layout.addWidget(lbl_m)

        self.master_fader = TactileFader(channel_id=0, label="MASTER", initial_value=255, is_master=True, parent=master_frame)
        self.master_fader.valueChanged.connect(self._on_fader_value_changed)
        self.faders[0] = self.master_fader
        master_layout.addWidget(self.master_fader, 1, alignment=Qt.AlignCenter)

        desk_container.addWidget(master_frame)

        # 2. 512 DMX Channels Deck (Bank Bar + Horizontally Scrollable Faders)
        channels_pane = QVBoxLayout()
        channels_pane.setSpacing(6)

        # Fader Bank Quick-Jump Bar (grandMA3 style - 8 banks of 64 channels = 512 channels)
        bank_bar = QHBoxLayout()
        bank_bar.setSpacing(6)

        lbl_bank = QLabel("FADER BANK:")
        lbl_bank.setStyleSheet(f"font-size: 10px; font-weight: 800; color: {Theme.TEXT_MUTED};")
        bank_bar.addWidget(lbl_bank)

        self.bank_buttons: list[tuple[QPushButton, int, int]] = []
        self.active_bank_index = 0
        banks = [
            ("BANK 1 (1-64)", 1, 64),
            ("BANK 2 (65-128)", 65, 128),
            ("BANK 3 (129-192)", 129, 192),
            ("BANK 4 (193-256)", 193, 256),
            ("BANK 5 (257-320)", 257, 320),
            ("BANK 6 (321-384)", 321, 384),
            ("BANK 7 (385-448)", 385, 448),
            ("BANK 8 (449-512)", 449, 512),
        ]
        for b_name, start_ch, end_ch in banks:
            btn_b = QPushButton(b_name)
            btn_b.setToolTip(f"Jump to DMX channels {start_ch} to {end_ch}")
            btn_b.setMinimumWidth(74)
            btn_b.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Theme.BG_SURFACE};
                    border: 1px solid {Theme.BORDER_SUBTLE};
                    border-radius: 4px;
                    color: {Theme.TEXT_SECONDARY};
                    font-size: 10px;
                    font-weight: 700;
                    padding: 4px 8px;
                }}
                QPushButton:hover {{
                    border-color: {Theme.ACCENT_CYAN};
                    color: {Theme.TEXT_PRIMARY};
                    background-color: {Theme.BG_ELEVATED};
                }}
            """)
            btn_b.clicked.connect(lambda _, ch=start_ch: self.scroll_to_channel(ch))
            bank_bar.addWidget(btn_b)
            self.bank_buttons.append((btn_b, start_ch, end_ch))

        bank_bar.addStretch()
        channels_pane.addLayout(bank_bar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Theme.BG_ROOT};
                border: 1px solid {Theme.BORDER_SUBTLE};
                border-radius: 6px;
            }}
        """)
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self._on_scroll_changed)

        channels_container = QWidget()
        channels_layout = QHBoxLayout(channels_container)
        channels_layout.setContentsMargins(10, 8, 10, 8)
        channels_layout.setSpacing(6)

        # Populate full 512 DMX channels
        for ch in range(1, 513):
            fader = TactileFader(channel_id=ch, label=f"Ch {ch}", initial_value=0, is_master=False, parent=channels_container)
            fader.valueChanged.connect(self._on_fader_value_changed)
            self.faders[ch] = fader
            channels_layout.addWidget(fader)

        channels_layout.addStretch()
        self.scroll_area.setWidget(channels_container)
        channels_pane.addWidget(self.scroll_area, 1)

        desk_container.addLayout(channels_pane, 1)

        main_layout.addLayout(desk_container, 1)

    def _on_scroll_changed(self, scroll_x: int) -> None:
        """Highlights the bank containing the first substantially visible channel."""
        fader_step = 58
        viewport_width = max(1, self.scroll_area.viewport().width())
        first_visible = max(1, 1 + (scroll_x // fader_step))
        last_visible = min(512, first_visible + max(0, viewport_width // fader_step))
        best_index = 0
        best_overlap = -1
        for bank_index, (_, start_ch, end_ch) in enumerate(self.bank_buttons):
            overlap = max(0, min(last_visible, end_ch) - max(first_visible, start_ch) + 1)
            if overlap > best_overlap:
                best_overlap = overlap
                best_index = bank_index
        self.active_bank_index = best_index
        for bank_index, (btn, start_ch, end_ch) in enumerate(self.bank_buttons):
            if bank_index == self.active_bank_index:
                btn.setProperty("active_bank", True)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {Theme.BG_ELEVATED};
                        border: 1px solid {Theme.ACCENT_CYAN};
                        border-radius: 4px;
                        color: {Theme.TEXT_PRIMARY};
                        font-size: 10px;
                        font-weight: 800;
                        padding: 4px 8px;
                    }}
                """)
            else:
                btn.setProperty("active_bank", False)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {Theme.BG_SURFACE};
                        border: 1px solid {Theme.BORDER_SUBTLE};
                        border-radius: 4px;
                        color: {Theme.TEXT_SECONDARY};
                        font-size: 10px;
                        font-weight: 700;
                        padding: 4px 8px;
                    }}
                    QPushButton:hover {{
                        border-color: {Theme.ACCENT_CYAN};
                        color: {Theme.TEXT_PRIMARY};
                        background-color: {Theme.BG_ELEVATED};
                    }}
                """)

    def sync_patch(self, patched_fixtures: list[dict]) -> None:
        """Updates fader header tags to show patched fixture and channel roles."""
        # 1. Reset all channels to blank tag
        for ch in range(1, 513):
            if ch in self.faders:
                self.faders[ch].set_fixture_tag("")

        # 2. Assign tags for each patched fixture
        for fix in patched_fixtures:
            channels = fix.get("channels", [])
            fixture_name = str(fix.get("name", fix.get("model", "Fixture")))
            fixture_name = fixture_name.replace(" (8CH RGBW)", "").replace(" (8CH RGB)", "")
            fixture_prefix = fixture_name.split("#", 1)[0].strip()
            fixture_index = fixture_name.split("#", 1)[1].split()[0] if "#" in fixture_name else ""
            short_fixture = (fixture_prefix.replace("Alien-", "").replace("Alien ", "")
                             .replace("Kumastb-", "").replace("Kumastb ", ""))
            if fixture_index:
                short_fixture = f"{short_fixture}-{fixture_index}"
            for ch_info in channels:
                ch_num = ch_info.get("channel", 1)
                ctype = str(ch_info.get("type", "dim")).lower()
                short_type = {
                    "dimmer": "DIM", "red": "RED", "green": "GRN", "blue": "BLU",
                    "white": "WHT", "strobe": "STR", "shutter": "SHT", "program": "PRG",
                    "speed": "SPD", "pan": "PAN", "tilt": "TLT", "empty": "EMP",
                    "amber": "AMB", "uv": "UV", "cyan": "CYN", "magenta": "MAG",
                    "yellow": "YEL", "gobo": "GOB", "prism": "PRS", "effect": "FX",
                    "maintenance": "MNT", "color macro": "MAC", "macro": "MAC",
                }.get(ctype, ctype[:3].upper())
                if ch_num in self.faders:
                    self.faders[ch_num].set_fixture_tag(f"{short_fixture}:{short_type}" if short_fixture else short_type)

    def scroll_to_channel(self, channel_num: int) -> None:
        """Instantly scrolls horizontal fader deck to the requested channel."""
        fader_step = 58  # 52px width + 6px spacing
        target_x = max(0, (channel_num - 1) * fader_step)
        self.scroll_area.horizontalScrollBar().setValue(target_x)

    def _on_fader_value_changed(self, ch_num: int, val: int) -> None:
        self.fader_changed.emit(ch_num, val)

    def set_channel_value(self, ch_num: int, val: int, silent: bool = False) -> None:
        """Sets a fader value programmatically."""
        fader = self.faders.get(ch_num)
        if fader:
            if silent:
                fader.set_value_silent(val)
            else:
                fader.value = val

    def apply_blackout(self) -> None:
        """Instant blackout: zero the Grand Master and every channel fader.

        Both must move together. Zeroing the Grand Master alone left the 256
        channel faders visually lit while the console transmitted zeros, so the
        mixer contradicted the DMX output on screen (and the operator had no
        indication the rig was dark). This mirrors what the BLACKOUT button
        writes to the wire, so the surface and the output always agree.

        Every fader is moved with the silent setter on purpose. Emitting
        valueChanged here would make the shell transmit once per fader, so a
        single blackout would push hundreds of frames and, worse, the first of
        them would carry the pre-blackout levels.
        """
        self.master_fader.set_value_silent(0)
        self._reset_dmx_channels()

    def _reset_dmx_channels(self) -> None:
        """Sets channels 1-512 to 0 while preserving Grand Master.

        Uses the silent setter: emitting valueChanged for 512 faders would make
        the shell transmit one Art-Net packet per channel, so a single blackout
        would burst hundreds of frames onto the wire.
        """
        for ch in range(1, 513):
            self.faders[ch].set_value_silent(0)

    def refresh_display(self) -> None:
        for f in self.faders.values():
            f.update()
