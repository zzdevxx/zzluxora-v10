"""
main_window.py | Master Lighting Console Window for ZZLUXORA v10
Features a 3-level header hierarchy (TitleBar, MenuBar, ProgramBar), 6 central workspaces,
and floating tool windows (Fixture List, Fixture Editor, Stage Visualizer, Settings, Help, About).
"""

from __future__ import annotations
import json
import math
import os
import sys
from pathlib import Path

from ui.qt_compat import (
    HAS_QT, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QMenuBar, QMenu,
    QFileDialog, QMessageBox, QButtonGroup, Qt, QTimer, QSize,
    QAction, QKeySequence, QIcon, QPixmap
)

from core.paths import ensure as ensure_dir, showfiles_dir as project_showfiles_dir
from ui.styles import Theme, CONSOLE_QSS
from ui.panels.address_tab import AddressTab
from ui.panels.analyze_tab import AnalyzeTab
from ui.panels.result_tab import ResultTab
from ui.panels.perform_tab import PerformTab
from ui.panels.page_tab import PageTab
from ui.panels.mixer_tab import MixerTab
from ui.panels.fixture_list import FixtureListWindow
from ui.panels.fixture_editor import FixtureEditorWindow
from ui.panels.preview_tab import StageVisualizerWindow
from ui.panels.settings_panel import SettingsDialog
from ui.panels.help_panel import HelpDialog
from ui.panels.about_panel import AboutDialog

from core.artnet_sender import ArtNetSender
from core.models import ProjectState
from core.project_io import ProjectIO
from core.song_library import SongLibrary


class MainWindow(QMainWindow if HAS_QT else object):
    """
    Main Production Lighting Console Window.
    Implements 3-level desktop header, 6 integrated workspaces, and floating utility windows.
    """
    def __init__(self):
        if not HAS_QT: return
        super().__init__()
        self.setWindowTitle("ZZLUXORA")
        self.resize(1200, 680)
        self.setMinimumSize(960, 560)
        self.setStyleSheet(CONSOLE_QSS)

        # Set Window and Taskbar Icon
        logo_path = Path(__file__).resolve().parent / "assets" / "logo_zz.png"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

        # DMX Buffer & State
        self.dmx_buffer = bytearray(512)
        self.project_state = ProjectState(project_name="Untitled.zlx", universe=0, master_dimmer=255)
        self.current_project_path = "Untitled.zlx"
        self.target_ip = "127.0.0.1"
        self.target_universe = 0
        self.target_port = 6454
        self.is_transmitting = False

        # Core ArtNet Sender
        self.artnet_sender = ArtNetSender(target_ip=self.target_ip, universe=self.target_universe, port=self.target_port)

        # Streaming Timer (43 FPS, ~23.22 ms)
        self.stream_timer = QTimer(self)
        self.stream_timer.setInterval(23)
        self.stream_timer.timeout.connect(self._stream_artnet_packet)

        # Floating Sub-Windows (Windowed Independent Tools)
        self.win_fixture_list: FixtureListWindow | None = None
        self.win_fixture_editor: FixtureEditorWindow | None = None
        self.win_visualizer: StageVisualizerWindow | None = None
        self.win_settings: SettingsDialog | None = None
        self.win_help: HelpDialog | None = None
        self.win_about: AboutDialog | None = None

        # Smooth Crossfade Engine State (~43.07 FPS DMX refresh)
        self._crossfade_timer = QTimer(self)
        self._crossfade_timer.setInterval(23)
        self._crossfade_timer.timeout.connect(self._on_crossfade_tick)
        self._fade_start = bytearray(512)
        self._fade_target = bytearray(512)
        self._fade_duration = 0.0
        self._fade_elapsed = 0.0
        # Look captured when a momentary flash is pressed, restored on release.
        self._flash_restore_buffer = bytearray()

        self._init_ui()
        self._init_menu_bar()
        self._init_shortcuts()
        self._update_title_bar()

    def _init_menu_bar(self) -> None:
        """Level 2: Main Menu Bar with proper dropdown QMenu hierarchy."""
        mb = self.menuBar()

        # 1. File Menu
        menu_file = mb.addMenu("File")

        act_open = QAction("Open Project", self)
        act_open.setShortcut(QKeySequence("Ctrl+O"))
        act_open.triggered.connect(self._on_open_project)
        menu_file.addAction(act_open)

        act_save = QAction("Save Project", self)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        act_save.triggered.connect(self._on_save_project)
        menu_file.addAction(act_save)

        act_save_as = QAction("Save As Project", self)
        act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_as.triggered.connect(self._on_save_as_project)
        menu_file.addAction(act_save_as)

        menu_file.addSeparator()

        act_exit = QAction("Exit", self)
        act_exit.setShortcut(QKeySequence("Alt+F4"))
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        # 2. Fixture Menu
        menu_fix = mb.addMenu("Fixture")
        act_fix_list = QAction("Fixture Library", self)
        act_fix_list.setShortcut(QKeySequence("Ctrl+F"))
        act_fix_list.triggered.connect(self._on_open_fixture_list)
        menu_fix.addAction(act_fix_list)

        act_fix_edit = QAction("Fixture Editor", self)
        act_fix_edit.setShortcut(QKeySequence("Ctrl+E"))
        act_fix_edit.triggered.connect(self._on_open_fixture_editor)
        menu_fix.addAction(act_fix_edit)

        # 3. Preview Action (Direct Pop-up, No Dropdown)
        act_preview = mb.addAction("Preview")
        act_preview.setShortcut(QKeySequence("Ctrl+P"))
        act_preview.triggered.connect(self._on_open_visualizer)

        # 4. Setting Action (Direct Pop-up, No Dropdown)
        act_setting = mb.addAction("Setting")
        act_setting.setShortcut(QKeySequence("Ctrl+Shift+P"))
        act_setting.triggered.connect(self._on_open_settings)

        # 5. Help Action (Direct Pop-up, No Dropdown)
        act_help = mb.addAction("Help")
        act_help.setShortcut(QKeySequence("F1"))
        act_help.triggered.connect(self._on_open_help)

        # 6. About Action (Direct Pop-up, No Dropdown)
        act_about = mb.addAction("About")
        act_about.triggered.connect(self._on_open_about)

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # LEVEL 2: PROGRAM VIEW BAR (Horizontal Workspace Tabs & Status)
        program_bar_frame = QFrame()
        program_bar_frame.setObjectName("ProgramBarFrame")
        pbar_layout = QHBoxLayout(program_bar_frame)
        pbar_layout.setContentsMargins(12, 4, 12, 4)
        pbar_layout.setSpacing(8)

        # Workspace Tab Buttons Group (Left)
        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)

        tab_names = ["Address", "Analyze", "Result", "Perform", "Page", "Mixer"]
        self.tab_buttons: list[QPushButton] = []
        for idx, name in enumerate(tab_names):
            btn = QPushButton(name)
            btn.setProperty("class", "ProgramTabBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, i=idx: self._switch_workspace(i))
            self.tab_group.addButton(btn, idx)
            pbar_layout.addWidget(btn)
            self.tab_buttons.append(btn)

        self.tab_buttons[0].setChecked(True)
        pbar_layout.addStretch()

        # Telemetry & Main Stage Action Buttons (Right)
        self.btn_artnet_badge = QPushButton("OUTPUT: IDLE")
        self.btn_artnet_badge.setObjectName("ArtNetBadgeBtn")
        self.btn_artnet_badge.setProperty("connected", "false")
        self.btn_artnet_badge.clicked.connect(self._on_open_settings)
        pbar_layout.addWidget(self.btn_artnet_badge)

        self.btn_blackout = QPushButton("BLACKOUT")
        self.btn_blackout.setObjectName("BlackoutBtn")
        self.btn_blackout.clicked.connect(self._on_blackout_clicked)
        pbar_layout.addWidget(self.btn_blackout)

        self.btn_play_stop = QPushButton("PLAY")
        self.btn_play_stop.setObjectName("PlayStopToggleBtn")
        self.btn_play_stop.setProperty("state", "play")
        self.btn_play_stop.clicked.connect(self._on_play_stop_toggled)
        pbar_layout.addWidget(self.btn_play_stop)

        root_layout.addWidget(program_bar_frame)

        # WORKSPACE AREA (QStackedWidget)
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {Theme.BG_ROOT};")

        # 1. Address Tab
        self.tab_address = AddressTab(self.project_state, self)
        self.tab_address.patch_changed.connect(self._on_patch_changed)
        self.tab_address.open_library_requested.connect(self._on_open_fixture_list)
        self.stack.addWidget(self.tab_address)

        # One song list shared by Analyze, Result and Perform. Each tab reads the
        # same order and hears the same notifications, so adding, removing,
        # selecting and reordering a song happens once and shows up everywhere.
        self.song_library = SongLibrary()

        # 2. Analyze Tab
        self.tab_analyze = AnalyzeTab(self.project_state, self, song_library=self.song_library)
        self.tab_analyze.analysis_ready.connect(self._on_analysis_ready)
        self.stack.addWidget(self.tab_analyze)

        # 3. Result Tab
        self.tab_result = ResultTab(self.project_state, self, song_library=self.song_library)
        self.tab_result.export_to_perform.connect(self._on_export_to_perform)
        self.tab_result.reanalyze_requested.connect(lambda: self._switch_workspace(1))
        self.stack.addWidget(self.tab_result)

        # 4. Perform Tab
        self.tab_perform = PerformTab(self.project_state, self, song_library=self.song_library)
        self.tab_perform.export_to_page.connect(self._on_export_to_page)
        self.tab_perform.cue_activated.connect(self._on_cue_activated)
        self.stack.addWidget(self.tab_perform)

        # 5. Page Tab
        self.tab_page = PageTab(self)
        self.tab_page.cue_activated.connect(self._on_cue_activated)
        self.stack.addWidget(self.tab_page)

        # 6. Mixer Tab
        self.tab_mixer = MixerTab(self.project_state, self)
        self.tab_mixer.fader_changed.connect(self._on_fader_moved)
        self.stack.addWidget(self.tab_mixer)

        root_layout.addWidget(self.stack, 1)

    def _init_shortcuts(self) -> None:
        """Global Keyboard Shortcuts.

        Every shortcut is bound with ApplicationShortcut context on purpose.
        The default WindowShortcut context only fires while the main window is
        the active window, so opening Help, About, Settings, the Fixture windows
        or the Stage Visualizer (all non-modal) silently disabled Play, Blackout
        and workspace switching until the popup was closed. A console must keep
        responding while an operator has a tool window open.
        """
        def bind(sequence: str, handler) -> None:
            action = QAction(self)
            action.setShortcut(QKeySequence(sequence))
            action.setShortcutContext(Qt.ApplicationShortcut)
            action.triggered.connect(handler)
            self.addAction(action)

        # Ctrl+F1 to Ctrl+F6: Direct workspace tab switching
        for i in range(6):
            bind(f"Ctrl+F{i + 1}", lambda _, idx=i: self._switch_workspace(idx))

        # Space: Toggle Play / Stop
        bind("Space", self._on_play_stop_toggled)

        # Escape and B: Blackout. Both are documented in the Help panel.
        bind("Escape", self._on_blackout_clicked)
        bind("B", self._on_blackout_clicked)

        # Global Undo: Ctrl+Z
        bind("Ctrl+Z", self.tab_address.undo_patch)

        # Global Redo: Ctrl+Shift+Z or Ctrl+Y (both are documented)
        bind("Ctrl+Shift+Z", self.tab_address.redo_patch)
        bind("Ctrl+Y", self.tab_address.redo_patch)

    def _switch_workspace(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        if 0 <= index < len(self.tab_buttons):
            self.tab_buttons[index].setChecked(True)

    def _update_title_bar(self) -> None:
        if not self.current_project_path or self.current_project_path == "Untitled.zlx":
            self.setWindowTitle("ZZLUXORA [Untitled.zlx]")
        else:
            self.setWindowTitle(f"ZZLUXORA [{self.current_project_path}]")

    # MENU POP-UP ACTIONS (WINDOWED INDEPENDENT TOOLS)
    def _on_open_fixture_list(self) -> None:
        if self.win_fixture_list is None:
            self.win_fixture_list = FixtureListWindow(parent=self)
        self.win_fixture_list.showNormal()
        self.win_fixture_list.show()
        self.win_fixture_list.raise_()
        self.win_fixture_list.activateWindow()

    def _on_open_fixture_editor(self) -> None:
        if self.win_fixture_editor is None:
            self.win_fixture_editor = FixtureEditorWindow(parent=self)
        self.win_fixture_editor.showNormal()
        self.win_fixture_editor.show()
        self.win_fixture_editor.raise_()
        self.win_fixture_editor.activateWindow()

    def _on_open_visualizer(self) -> None:
        if self.win_visualizer is None:
            self.win_visualizer = StageVisualizerWindow(parent=self)
        if hasattr(self, 'tab_address'):
            fixtures = self.tab_address.get_patched_fixtures()
            self.win_visualizer.sync_fixtures(fixtures)
        self.win_visualizer.update_dmx(self.dmx_buffer)
        self.win_visualizer.showNormal()
        self.win_visualizer.show()
        self.win_visualizer.raise_()
        self.win_visualizer.activateWindow()

    def _on_open_settings(self) -> None:
        if self.win_settings is None:
            self.win_settings = SettingsDialog(self.target_ip, self.target_universe, self)
            self.win_settings.setWindowFlags(Qt.Window)
            self.win_settings.settings_saved.connect(self._on_settings_saved)
        self.win_settings.showNormal()
        self.win_settings.show()
        self.win_settings.raise_()
        self.win_settings.activateWindow()

    def _on_settings_saved(self, ip: str, port: int, universe: int, fps: int = 43) -> None:
        self.target_ip = ip
        self.target_port = port
        self.target_universe = universe
        self.artnet_sender.close()
        self.artnet_sender = ArtNetSender(target_ip=ip, universe=universe, port=port)
        self._apply_stream_rate(fps)

    def _apply_stream_rate(self, fps: int) -> None:
        """Set the output timer interval from a target frames-per-second value."""
        clamped = max(1, min(120, int(fps)))
        interval_ms = max(1, int(round(1000.0 / clamped)))
        self.stream_timer.setInterval(interval_ms)
        self._crossfade_timer.setInterval(interval_ms)

    def _on_open_help(self) -> None:
        if self.win_help is None:
            self.win_help = HelpDialog(self)
            self.win_help.setWindowFlags(Qt.Window)
        self.win_help.showNormal()
        self.win_help.show()
        self.win_help.raise_()
        self.win_help.activateWindow()

    def _on_open_about(self) -> None:
        if self.win_about is None:
            self.win_about = AboutDialog(self)
            self.win_about.setWindowFlags(Qt.Window)
        self.win_about.showNormal()
        self.win_about.show()
        self.win_about.raise_()
        self.win_about.activateWindow()

    # STAGE CONTROLS: BLACKOUT & PLAY/STOP
    def _on_blackout_clicked(self) -> None:
        # A live crossfade keeps writing the dmx_buffer on every tick, so a
        # blackout that only zeroes the buffer was undone ~23 ms later by the
        # next tick and the stage lit back up. Cancel the fade first.
        if self._crossfade_timer.isActive():
            self._crossfade_timer.stop()
        if hasattr(self, 'tab_perform'):
            self.tab_perform.reset_crossfade_progress()
        self.tab_mixer.apply_blackout()
        for i in range(512):
            self.dmx_buffer[i] = 0
        if self.is_transmitting:
            # Push the zeroed buffer into the sender BEFORE asking it to black
            # out. ArtNetSender keeps its own copy of the 512 channels, and its
            # blackout() transmits that copy; without this push the stale
            # previous frame (including any channels the UI never rewrites, such
            # as 257-512) is sent to the rig first, briefly re-lighting it.
            self.artnet_sender.send_raw(self.dmx_buffer)
            self.artnet_sender.blackout()
        if self.win_visualizer and self.win_visualizer.isVisible():
            self.win_visualizer.update_dmx([0] * 512)

    def _on_play_stop_toggled(self) -> None:
        self.is_transmitting = not self.is_transmitting

        if self.is_transmitting:
            # Change button to STOP (Red)
            self.btn_play_stop.setText("STOP")
            self.btn_play_stop.setProperty("state", "stop")
            self.btn_play_stop.style().polish(self.btn_play_stop)

            # Badge reports that frames are being streamed. UDP gives no
            # delivery confirmation, so it must not claim the node received them.
            self.btn_artnet_badge.setText("OUTPUT: STREAMING")
            self.btn_artnet_badge.setProperty("connected", "true")
            self.btn_artnet_badge.style().polish(self.btn_artnet_badge)

            # Transmit immediately on play and start continuous streaming.
            # Derive the frame from the faders first: RESET DMX zeroes the
            # faders silently, so the dmx_buffer still held the previous look
            # and pressing PLAY re-lit the stage with it.
            self._rebuild_dmx_from_faders()
            self.artnet_sender.send_raw(self.dmx_buffer)
            self.stream_timer.start()
        else:
            # Change button to PLAY (Green)
            self.btn_play_stop.setText("PLAY")
            self.btn_play_stop.setProperty("state", "play")
            self.btn_play_stop.style().polish(self.btn_play_stop)

            # Streaming stopped; no frames are leaving this machine.
            self.btn_artnet_badge.setText("OUTPUT: IDLE")
            self.btn_artnet_badge.setProperty("connected", "false")
            self.btn_artnet_badge.style().polish(self.btn_artnet_badge)

            self.stream_timer.stop()

    def _rebuild_dmx_from_faders(self) -> None:
        """Recompute the whole DMX frame from the current fader positions.

        The mixer uses silent setters for bulk changes (RESET DMX, blackout,
        loading a project) so it does not emit one Art-Net packet per channel.
        The price is that dmx_buffer does not follow those faders by itself;
        anything that transmits the buffer after a bulk change must rebuild it
        first, or the rig gets the pre-change look.
        """
        master_scale = self.tab_mixer.master_fader.value / 255.0
        for ch in range(1, 513):
            raw_value = self.tab_mixer.faders[ch].value
            self.dmx_buffer[ch - 1] = int(round(raw_value * master_scale))

    def _stream_artnet_packet(self) -> None:
        if self.is_transmitting:
            self.artnet_sender.send_raw(self.dmx_buffer)
            if self.win_visualizer and self.win_visualizer.isVisible():
                self.win_visualizer.update_dmx(self.dmx_buffer)

    def _on_fader_moved(self, ch_id: int, val: int) -> None:
        master_val = val if ch_id == 0 else self.tab_mixer.master_fader.value
        master_dim = master_val / 255.0

        if ch_id == 0:
            # Grand Master moved: scale all 512 channels
            for ch in range(1, 513):
                raw = self.tab_mixer.faders[ch].value
                self.dmx_buffer[ch - 1] = int(round(raw * master_dim))
        elif 1 <= ch_id <= 512:
            self.dmx_buffer[ch_id - 1] = int(round(val * master_dim))

        # Hanya mengirim paket jika tombol Play aktif (is_transmitting == True)
        if self.is_transmitting:
            self.artnet_sender.send_raw(self.dmx_buffer)

        if self.win_visualizer and self.win_visualizer.isVisible():
            self.win_visualizer.update_dmx(self.dmx_buffer)

    @staticmethod
    def _fixture_channel_offset(channel_number: int, footprint: int = 8) -> int:
        """Return zero-based offset within a fixed 8-channel PAR fixture footprint.

        Deprecated for address recovery. It assumes every fixture occupies
        exactly 8 channels, so deriving a start address from it corrupts any
        fixture with a different channel count or a non-8-aligned address.
        Addresses now come from AddressTab.get_patched_fixtures(), which follows
        the real contiguous run. Kept only for the fixed-footprint preview and
        visualizer geometry.
        """
        return (channel_number - 1) % footprint

    def _on_patch_changed(self) -> None:
        fixtures = self.tab_address.get_patched_fixtures() if hasattr(self, 'tab_address') else []
        if hasattr(self, 'tab_mixer'):
            self.tab_mixer.sync_patch(fixtures)
        if self.win_visualizer is not None:
            self.win_visualizer.sync_fixtures(fixtures)
            self.win_visualizer.update_dmx(self.dmx_buffer)

    # WORKFLOW INTEGRATION ACROSS TABS
    def _on_analysis_ready(self, res: dict) -> None:
        self.tab_result.load_analysis_result(res)
        self.tab_perform.add_analyzed_song(res)
        self._switch_workspace(2)  # Switch to Result tab

    def _on_export_to_perform(self, song_res: dict) -> None:
        self.tab_perform.add_analyzed_song(song_res)
        self._switch_workspace(3)  # Switch to Perform tab

    def _on_export_to_page(self, cues: list) -> None:
        self.tab_page.load_cues(cues)
        self._switch_workspace(4)  # Switch to Page tab

    def _get_target_dmx_for_cue(self, cue_info: dict) -> bytearray:
        """Calculate the 512-channel DMX target buffer for a given cue based on patched fixtures.

        The palette arriving here is already physically decomposed: ColorEngine
        pulled W = min(R, G, B) out of the colour into its own component, so R/G/B
        no longer carry it. A fixture without a white emitter therefore has
        nowhere to put W, and dropping it silently costs most of the available
        light - measured at 22 to 78 percent of the intended RGB intensity across
        the benchmark tracks, and total blackout for a pure white cue
        (255,255,255) -> (0,0,0). When no patched channel can accept W, fold it
        back into R/G/B so the requested colour is reproduced at full brightness
        instead of going dark.
        """
        target = bytearray(512)
        palette = cue_info.get("color", {})
        intensity = max(0, min(255, int(cue_info.get("dimmer", 255)))) if cue_info.get("active", True) else 0
        r_val = max(0, min(255, int(palette.get("R", 255))))
        g_val = max(0, min(255, int(palette.get("G", 255))))
        b_val = max(0, min(255, int(palette.get("B", 255))))
        w_val = max(0, min(255, int(palette.get("W", 0))))
        is_flash = (cue_info.get("type") == "flash")

        patched_boxes = [box for box in self.tab_address.grid_area.boxes.values() if box.is_patched]
        if patched_boxes:
            # Additive white is a display-space property: only relevant when a
            # white channel exists. Otherwise recombine before writing channels.
            has_white_channel = any("white" in box.channel_type.lower() for box in patched_boxes)
            if not has_white_channel and w_val:
                r_val = min(255, r_val + w_val)
                g_val = min(255, g_val + w_val)
                b_val = min(255, b_val + w_val)
                w_val = 0

            for box in patched_boxes:
                ch = box.channel_num
                ctype = box.channel_type.lower()
                val = 0
                if "dim" in ctype:
                    val = intensity
                elif "red" in ctype:
                    val = r_val
                elif "green" in ctype:
                    val = g_val
                elif "blue" in ctype:
                    val = b_val
                elif "white" in ctype:
                    val = w_val
                elif "strobe" in ctype:
                    val = 255 if is_flash else 0
                elif ctype in ["program", "speed", "empty"]:
                    val = 0
                target[ch - 1] = max(0, min(255, val))
        else:
            # Fallback when no patch is active: default 4 PARs at channels 1..32
            for fix_idx in range(4):
                base = fix_idx * 8
                target[base] = intensity
                target[base + 1] = r_val
                target[base + 2] = g_val
                target[base + 3] = b_val
                target[base + 4] = w_val

        return target

    def _apply_dmx_buffer(self, buf: bytearray | list[int]) -> None:
        """Applies buffer to dmx_buffer, updates mixer faders, transmits Art-Net, and updates visualizer."""
        self.dmx_buffer[:] = bytes(buf)
        for ch in range(1, 513):
            val = self.dmx_buffer[ch - 1]
            self.tab_mixer.set_channel_value(ch, val, silent=True)

        if self.is_transmitting:
            self.artnet_sender.send_raw(self.dmx_buffer)

        if self.win_visualizer and self.win_visualizer.isVisible():
            self.win_visualizer.update_dmx(self.dmx_buffer)

    def _on_cue_activated(self, cue_info: dict) -> None:
        """Smoothly or instantly crossfades stage lighting to the triggered cue."""
        is_flash = (cue_info.get("type") == "flash")

        # A flash is momentary: pressing it jumps to the flash look, and
        # releasing it must return to whatever was running before. Without this
        # memory the release was routed through the normal cue path with
        # active=False, which zeroes the dimmer and leaves the colour channels
        # latched at the flash values, so every flash ended in a blackout plus
        # stuck white.
        if is_flash:
            if cue_info.get("active", True):
                if not self._flash_restore_buffer:
                    self._flash_restore_buffer = bytearray(self.dmx_buffer)
            else:
                restore = self._flash_restore_buffer
                self._flash_restore_buffer = bytearray()
                if restore:
                    if self._crossfade_timer.isActive():
                        self._crossfade_timer.stop()
                    self.tab_perform.reset_crossfade_progress()
                    self._apply_dmx_buffer(bytearray(restore))
                    return

        target = self._get_target_dmx_for_cue(cue_info)
        fade_time = float(cue_info.get("fade_time", cue_info.get("fade_in", 0.0)))

        if fade_time <= 0.05 or is_flash or not HAS_QT:
            if self._crossfade_timer.isActive():
                self._crossfade_timer.stop()
            self.tab_perform.reset_crossfade_progress()
            self._apply_dmx_buffer(target)
        else:
            self._fade_start = bytearray(self.dmx_buffer)
            self._fade_target = bytearray(target)
            self._fade_duration = max(0.1, fade_time)
            self._fade_elapsed = 0.0
            self.tab_perform.reset_crossfade_progress()
            self._crossfade_timer.start()

    def _on_crossfade_tick(self) -> None:
        self._fade_elapsed += 0.023
        progress = min(1.0, self._fade_elapsed / self._fade_duration)
        # Cosine S-curve interpolation
        factor = 0.5 * (1.0 - math.cos(math.pi * progress))

        buf = bytearray(512)
        for i in range(512):
            s = self._fade_start[i]
            t = self._fade_target[i]
            buf[i] = int(round(s + (t - s) * factor))

        self._apply_dmx_buffer(buf)

        if hasattr(self, 'tab_perform'):
            self.tab_perform.set_crossfade_progress(progress, self._fade_elapsed, self._fade_duration)

        if progress >= 1.0:
            self._crossfade_timer.stop()
            if hasattr(self, 'tab_perform'):
                self.tab_perform.set_crossfade_progress(1.0, self._fade_duration, self._fade_duration)

    # FILE MANAGEMENT (.zlx)
    def load_project_file(self, path: str, notify: bool = True) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Gate the payload before any state is touched. ProjectIO owns the
            # schema rules; without this check the console adopted any JSON at
            # all (a QLC+ file, a hand-edited one whose target_ip was the string
            # "not-an-ip") and then sent Art-Net to an invalid destination,
            # having already replaced the operator's current patch.
            problem = ProjectIO.validate_payload(data)
            if problem is not None:
                if notify:
                    QMessageBox.critical(
                        self,
                        "Open Error",
                        f"'{Path(path).name}' was not loaded because {problem}.\n\n"
                        "The current project was left unchanged.",
                    )
                return

            self.current_project_path = path
            self._update_title_bar()

            # Target IP, UDP port, and universe
            self.target_ip = data.get("target_ip", "127.0.0.1")
            self.target_port = data.get("port", 6454)
            self.target_universe = data.get("universe", 0)
            self.artnet_sender.close()
            self.artnet_sender = ArtNetSender(target_ip=self.target_ip, universe=self.target_universe, port=self.target_port)

            # Load patch entries in either showfile fixture-block form or legacy per-channel form
            patches = data.get("patches", data.get("patches_raw", []))
            self.tab_address.record_undo()
            for box in self.tab_address.grid_area.boxes.values():
                box.set_unpatched()
            for p in patches:
                if "channels" in p:
                    start_ch = int(p.get("start_channel", 1))
                    fixture_name = p.get("model", p.get("name", "Fixture"))
                    for offset, ch in enumerate(p.get("channels", [])):
                        ch_num = start_ch + offset
                        if ch_num in self.tab_address.grid_area.boxes:
                            self.tab_address.grid_area.boxes[ch_num].set_patched(
                                ch.get("type", "empty"), ch.get("label", ""), fixture_name
                            )
                else:
                    ch_num = int(p.get("channel", 0))
                    if ch_num in self.tab_address.grid_area.boxes:
                        self.tab_address.grid_area.boxes[ch_num].set_patched(
                            p.get("type", "empty"), p.get("label", ""),
                            p.get("fixture", p.get("fixture_name", "Fixture"))
                        )
            self.tab_address.patch_changed.emit()

            # Load songs to PerformTab
            songs = data.get("songs", [])
            self.tab_perform.playlist.clear()
            self.tab_perform.playlist_widget.clear()
            for s in songs:
                self.tab_perform.add_analyzed_song(s)

            # Load cues to PageTab
            cues = data.get("cues", [])
            self.tab_page._clear_executors()
            if cues:
                self.tab_page.load_cues(cues)

            # Load saved channel values, then derive DMX output with Grand Master.
            faders_dict = data.get("faders", {})
            if "0" not in faders_dict and "master_dimmer" in data:
                faders_dict["0"] = data["master_dimmer"]
            for channel_text, value in faders_dict.items():
                self.tab_mixer.set_channel_value(int(channel_text), value, silent=True)
            master_scale = getattr(self.tab_mixer.master_fader, "value", 255) / 255.0
            for channel in range(1, 513):
                fader = self.tab_mixer.faders.get(channel) if hasattr(self.tab_mixer.faders, "get") else None
                raw_value = getattr(fader, "value", 0) if fader is not None else 0
                self.dmx_buffer[channel - 1] = round(raw_value * master_scale)

            if notify:
                QMessageBox.information(self, "Project Loaded", f"Project successfully loaded from:\n{Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Open Error", f"Failed to load project file:\n{e}")

    def _on_open_project(self) -> None:
        showfiles_dir = ensure_dir(project_showfiles_dir())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open ZZLUXORA Project",
            str(showfiles_dir),
            "ZZLUXORA Project (*.zlx)",
        )
        if path:
            self.load_project_file(path)

    def _on_save_project(self) -> None:
        if self.current_project_path == "Untitled.zlx":
            self._on_save_as_project()
        else:
            self._save_to_path(self.current_project_path)

    def _on_save_as_project(self) -> None:
        showfiles_dir = ensure_dir(project_showfiles_dir())
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save ZZLUXORA Project",
            str(showfiles_dir / "Untitled.zlx"),
            "ZZLUXORA Project (*.zlx)",
        )
        if path:
            self._save_to_path(path)

    def _save_to_path(self, path: str) -> None:
        try:
            # Group by the fixture's real contiguous run, taken from the address
            # grid. Deriving the start address from a modulo-8 formula wrote the
            # wrong address for any fixture not dropped on an 8-channel boundary
            # (a fixture at DMX 18 was saved as 17), and that wrong address then
            # drove the wrong physical fixtures after reload.
            patches = []
            for fixture in self.tab_address.get_patched_fixtures():
                entry = {
                    "start_channel": int(fixture["start_channel"]),
                    "model": fixture.get("name", ""),
                    "channels": [
                        {"index": index + 1,
                         "type": channel.get("type", ""),
                         "label": channel.get("label", "")}
                        for index, channel in enumerate(fixture.get("channels", []))
                    ],
                }
                patches.append(entry)

            faders = {}
            for ch in range(513):
                fader = self.tab_mixer.faders.get(ch) if hasattr(self.tab_mixer.faders, "get") else None
                if fader is not None:
                    val = getattr(fader, "value", 0)
                    if val > 0 or ch == 0:
                        faders[str(ch)] = val

            data = {
                "app": "ZZLUXORA",
                "version": "10.0.0",
                "project_name": Path(path).stem,
                "target_ip": self.target_ip,
                "port": self.target_port,
                "universe": self.target_universe,
                "master_dimmer": self.tab_mixer.master_fader.value,
                "patches": patches,
                "songs": self.tab_perform.playlist,
                "cues": [button.cue_data for button in self.tab_page.executor_buttons],
                "faders": faders,
            }
            # Atomic write, matching ProjectIO.save_project. The previous inline
            # open(path, "w") truncated the showfile before writing, so a failure
            # mid-serialization turned the operator's saved show into a corrupt
            # fragment (measured: a 1973-byte project became 51 unusable bytes).
            temporary = f"{path}.{os.getpid()}.tmp"
            try:
                with open(temporary, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporary, path)
            except OSError:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
                raise

            self.current_project_path = path
            self._update_title_bar()
            QMessageBox.information(self, "Project Saved", f"Project successfully saved to:\n{Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save project file:\n{e}")

    def closeEvent(self, event) -> None:
        # Close all child windows. The Fixture Editor refuses to close while it
        # holds unsaved changes the operator chose to keep, and aborting the whole
        # shutdown is safer than destroying a document on the way out.
        children = [
            self.win_fixture_list,
            self.win_fixture_editor,
            self.win_visualizer,
            self.win_settings,
            self.win_help,
            self.win_about,
        ]
        for window in children:
            if window is not None and not window.close():
                event.ignore()
                return
        self.stream_timer.stop()
        # Fold the blackout state into this window, not only the wire. Sending
        # blackout() darkens the rig, but the window's dmx_buffer and the mixer
        # faders kept the last look. Shutdown can be aborted (a child window that
        # refuses to close makes this event ignored), and then PLAY would resend
        # the stale buffer and the faders would contradict the dark stage. Mirror
        # the BLACKOUT path so the surface, the buffer, and the wire agree.
        self.tab_mixer.apply_blackout()
        for i in range(512):
            self.dmx_buffer[i] = 0
        if self.is_transmitting:
            self.artnet_sender.send_raw(self.dmx_buffer)
        self.artnet_sender.blackout()
        self.artnet_sender.close()
        event.accept()
