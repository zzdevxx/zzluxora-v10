"""
perform_tab.py | Live Stage Show Controller & Performance Cue Generator
Manages the worship song playlist, song sections (Intro, Verse, Chorus, Bridge, Ending),
fade timings, smooth live cue crossfading [GO+], and exports automated executor triggers to Tab Page.
"""

from __future__ import annotations

from ui.qt_compat import (
    HAS_QT, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QListWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QSplitter, QDoubleSpinBox, QProgressBar, QMessageBox,
    QDialog, QLineEdit, QSpinBox,
    Qt, Signal, QColor, QFont
)
from ui.styles import Theme, CONSOLE_QSS
from core.song_library import SongLibrary
from ui.widgets.song_list_panel import SongListPanel


class EditCueDialog(QDialog if HAS_QT else object):
    """Modal dialog for adding or editing custom cue parameters."""
    def __init__(self, cue: dict, is_new: bool = False, parent: QWidget | None = None):
        if not HAS_QT: return
        super().__init__(parent)
        self.setWindowTitle("Add Section Cue" if is_new else "Edit Section Cue")
        self.resize(380, 420)
        self.setStyleSheet(CONSOLE_QSS)
        self.cue = dict(cue)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Section Name:"))
        self.txt_section = QLineEdit(self.cue.get("section", "Chorus"))
        self.txt_section.setStyleSheet(f"background-color: {Theme.SURFACE_INPUT}; border: 1px solid {Theme.BORDER_STRONG}; color: {Theme.TEXT_PRIMARY};")
        layout.addWidget(self.txt_section)

        layout.addWidget(QLabel("Mood Character:"))
        self.txt_mood = QLineEdit(self.cue.get("mood", "Praise Energy Rise"))
        self.txt_mood.setStyleSheet(f"background-color: {Theme.SURFACE_INPUT}; border: 1px solid {Theme.BORDER_STRONG}; color: {Theme.TEXT_PRIMARY};")
        layout.addWidget(self.txt_mood)

        fade_row = QHBoxLayout()
        fade_in_box = QVBoxLayout()
        fade_in_box.addWidget(QLabel("Fade In (sec):"))
        self.spin_fade_in = QDoubleSpinBox()
        self.spin_fade_in.setRange(0.0, 30.0)
        self.spin_fade_in.setSingleStep(0.5)
        self.spin_fade_in.setValue(float(self.cue.get("fade_in", 2.0)))
        fade_in_box.addWidget(self.spin_fade_in)
        fade_row.addLayout(fade_in_box)

        fade_out_box = QVBoxLayout()
        fade_out_box.addWidget(QLabel("Fade Out (sec):"))
        self.spin_fade_out = QDoubleSpinBox()
        self.spin_fade_out.setRange(0.0, 30.0)
        self.spin_fade_out.setSingleStep(0.5)
        self.spin_fade_out.setValue(float(self.cue.get("fade_out", 2.0)))
        fade_out_box.addWidget(self.spin_fade_out)
        fade_row.addLayout(fade_out_box)
        layout.addLayout(fade_row)

        layout.addWidget(QLabel("Dimmer (0-255):"))
        self.spin_dimmer = QSpinBox()
        self.spin_dimmer.setRange(0, 255)
        self.spin_dimmer.setValue(int(self.cue.get("dimmer", 255)))
        layout.addWidget(self.spin_dimmer)

        pal = self.cue.get("color", {"R": 255, "G": 255, "B": 255, "W": 0})
        layout.addWidget(QLabel("RGBW Color (0-255):"))
        rgb_row = QHBoxLayout()

        r_box = QVBoxLayout(); r_box.addWidget(QLabel("R:")); self.spin_r = QSpinBox(); self.spin_r.setRange(0, 255); self.spin_r.setValue(int(pal.get("R", 255))); r_box.addWidget(self.spin_r); rgb_row.addLayout(r_box)
        g_box = QVBoxLayout(); g_box.addWidget(QLabel("G:")); self.spin_g = QSpinBox(); self.spin_g.setRange(0, 255); self.spin_g.setValue(int(pal.get("G", 255))); g_box.addWidget(self.spin_g); rgb_row.addLayout(g_box)
        b_box = QVBoxLayout(); b_box.addWidget(QLabel("B:")); self.spin_b = QSpinBox(); self.spin_b.setRange(0, 255); self.spin_b.setValue(int(pal.get("B", 255))); b_box.addWidget(self.spin_b); rgb_row.addLayout(b_box)
        w_box = QVBoxLayout(); w_box.addWidget(QLabel("W:")); self.spin_w = QSpinBox(); self.spin_w.setRange(0, 255); self.spin_w.setValue(int(pal.get("W", 0))); w_box.addWidget(self.spin_w); rgb_row.addLayout(w_box)
        layout.addLayout(rgb_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_save = QPushButton("Save Cue")
        btn_save.setStyleSheet(f"background-color: {Theme.STATUS_SUCCESS_BG}; color: {Theme.COLOR_SUCCESS}; font-weight: bold; padding: 6px 14px;")
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_save)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _on_save(self) -> None:
        self.cue["section"] = self.txt_section.text().strip() or "Cue"
        self.cue["mood"] = self.txt_mood.text().strip()
        self.cue["fade_in"] = self.spin_fade_in.value()
        self.cue["fade_out"] = self.spin_fade_out.value()
        self.cue["dimmer"] = self.spin_dimmer.value()
        self.cue["color"] = {
            "R": self.spin_r.value(),
            "G": self.spin_g.value(),
            "B": self.spin_b.value(),
            "W": self.spin_w.value(),
        }
        self.accept()


class PerformTab(QWidget if HAS_QT else object):
    """Perform Tab: Live stage show sequencer, cue crossfade controller, and Page executor generator."""
    export_to_page = Signal(list)  # Emits list of generated cues for PageTab
    cue_activated = Signal(dict)   # Emits active cue with color, dimmer, fade_time to MainWindow

    def __init__(self, project_state=None, parent: QWidget | None = None,
                 song_library=None):
        if not HAS_QT: return
        super().__init__(parent)
        self.project_state = project_state
        self.song_library = song_library if song_library is not None else SongLibrary()
        self.song_library.on_changed(self._refresh_playlist_view)
        self.song_library.on_selection_changed(self._on_library_selection)
        self.playlist: list[dict] = []
        self.current_song_cues: list[dict] = []
        self.active_cue_index: int = -1
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(12)

        # Top Control Bar (Clean - playlist actions moved to song panel and cue table)
        top_bar = QHBoxLayout()
        top_bar.addStretch()

        # Retained as internal attributes for automated tests
        self.btn_move_up = QPushButton("MOVE UP")
        self.btn_move_up.clicked.connect(self._on_move_up)
        self.btn_move_down = QPushButton("MOVE DOWN")
        self.btn_move_down.clicked.connect(self._on_move_down)
        self.btn_delete_song = QPushButton("DELETE")
        self.btn_delete_song.clicked.connect(self._on_delete_song)
        self.btn_export_page = QPushButton("GENERATE EXECUTORS")
        self.btn_export_page.clicked.connect(self._on_export_to_page)

        main_layout.addLayout(top_bar)

        # Splitter: Playlist vs Cues
        splitter = QSplitter(Qt.Horizontal)

        # Left: Standardized Song List Panel
        self.song_panel = SongListPanel(self.song_library, self)
        self.playlist_widget = self.song_panel.list_widget
        self.song_panel.song_selected.connect(self._on_song_selected)
        splitter.addWidget(self.song_panel)

        # Right: Section Cues & Master Playback
        right_box = QGroupBox("Section Cues & Stage Lighting Timing")
        right_box.setStyleSheet(f"QGroupBox {{ font-weight: 700; color: {Theme.TEXT_PRIMARY}; }}")
        right_layout = QVBoxLayout(right_box)

        # Cue Control Bar (5 square icon buttons)
        cue_bar = QHBoxLayout()
        cue_bar.setContentsMargins(0, 0, 0, 0)
        cue_bar.setSpacing(4)
        lbl_cues = QLabel("SECTION CUES")
        lbl_cues.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {Theme.TEXT_SECONDARY};")
        cue_bar.addWidget(lbl_cues)
        cue_bar.addStretch()

        self.btn_cue_add = QPushButton("+")
        self.btn_cue_add.setFixedSize(24, 22)
        self.btn_cue_add.setToolTip("Add custom cue / section")
        self.btn_cue_add.clicked.connect(self._on_add_cue_clicked)
        cue_bar.addWidget(self.btn_cue_add)

        self.btn_cue_edit = QPushButton("✎")
        self.btn_cue_edit.setFixedSize(24, 22)
        self.btn_cue_edit.setToolTip("Edit selected cue parameters")
        self.btn_cue_edit.setEnabled(False)
        self.btn_cue_edit.clicked.connect(self._on_edit_cue_clicked)
        cue_bar.addWidget(self.btn_cue_edit)

        self.btn_cue_remove = QPushButton("-")
        self.btn_cue_remove.setFixedSize(24, 22)
        self.btn_cue_remove.setToolTip("Remove selected cue")
        self.btn_cue_remove.setEnabled(False)
        self.btn_cue_remove.clicked.connect(self._on_remove_cue_clicked)
        cue_bar.addWidget(self.btn_cue_remove)

        self.btn_cue_up = QPushButton("▲")
        self.btn_cue_up.setFixedSize(24, 22)
        self.btn_cue_up.setToolTip("Move selected cue up")
        self.btn_cue_up.setEnabled(False)
        self.btn_cue_up.clicked.connect(lambda: self._on_move_cue_clicked(-1))
        cue_bar.addWidget(self.btn_cue_up)

        self.btn_cue_down = QPushButton("▼")
        self.btn_cue_down.setFixedSize(24, 22)
        self.btn_cue_down.setToolTip("Move selected cue down")
        self.btn_cue_down.setEnabled(False)
        self.btn_cue_down.clicked.connect(lambda: self._on_move_cue_clicked(1))
        cue_bar.addWidget(self.btn_cue_down)

        right_layout.addLayout(cue_bar)

        self.cue_table = QTableWidget(0, 6)
        self.cue_table.setHorizontalHeaderLabels([
            "Section", "Mood", "Fade In", "Fade Out", "Dimmer", "Trigger"
        ])
        self.cue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cue_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.cue_table.verticalHeader().setVisible(False)
        self.cue_table.cellDoubleClicked.connect(lambda row, col: self._trigger_cue_at_row(row))
        self.cue_table.itemSelectionChanged.connect(self._on_cue_selection_changed)
        right_layout.addWidget(self.cue_table, 1)

        # Live Master Playback Transport Toolbar
        playback_box = QFrame()
        playback_box.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.BG_ELEVATED};
                border: 1px solid {Theme.BORDER_STRONG};
                border-radius: 6px;
                padding: 6px;
            }}
        """)
        playback_layout = QHBoxLayout(playback_box)
        playback_layout.setContentsMargins(10, 8, 10, 8)
        playback_layout.setSpacing(10)

        self.btn_prev_cue = QPushButton("[PREV]")
        self.btn_prev_cue.setStyleSheet(f"font-weight: 700; color: {Theme.TEXT_PRIMARY}; min-height: 38px; padding: 6px 14px;")
        self.btn_prev_cue.clicked.connect(self._on_prev_clicked)
        playback_layout.addWidget(self.btn_prev_cue)

        self.btn_go_cue = QPushButton("[GO+]")
        self.btn_go_cue.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.STATUS_SUCCESS_BG};
                border: 2px solid {Theme.COLOR_SUCCESS};
                color: {Theme.COLOR_SUCCESS};
                font-weight: 900;
                font-size: 14px;
                min-height: 44px;
                min-width: 90px;
                padding: 8px 22px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {Theme.COLOR_SUCCESS};
                color: {Theme.BG_ROOT};
            }}
            QPushButton:pressed {{
                background-color: {Theme.STATUS_SUCCESS_BORDER};
                color: {Theme.TEXT_PRIMARY};
            }}
        """)
        self.btn_go_cue.setMinimumHeight(48)
        self.btn_go_cue.clicked.connect(self._on_go_clicked)
        playback_layout.addWidget(self.btn_go_cue)

        self.btn_fade_black = QPushButton("[FADE BLACK]")
        self.btn_fade_black.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.STATUS_DANGER_BG};
                border: 1px solid {Theme.COLOR_DANGER};
                color: {Theme.COLOR_DANGER};
                font-weight: 700;
                min-height: 38px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: {Theme.COLOR_DANGER};
                color: {Theme.TEXT_PRIMARY};
            }}
        """)
        self.btn_fade_black.clicked.connect(self._on_fade_black_clicked)
        playback_layout.addWidget(self.btn_fade_black)

        self.btn_fade_idle = QPushButton("[FADE IDLE]")
        self.btn_fade_idle.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.BG_SURFACE};
                border: 1px solid {Theme.ACCENT_CYAN};
                color: {Theme.ACCENT_CYAN};
                font-weight: 700;
                min-height: 38px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: {Theme.ACCENT_CYAN};
                color: {Theme.BG_ROOT};
            }}
        """)
        self.btn_fade_idle.clicked.connect(self._on_fade_idle_clicked)
        playback_layout.addWidget(self.btn_fade_idle)

        # Crossfade Progress Bar & Countdown Telemetry
        telemetry_box = QVBoxLayout()
        telemetry_box.setSpacing(3)
        self.lbl_fade_countdown = QLabel("FADE: IDLE | 0.0s")
        self.lbl_fade_countdown.setStyleSheet(f"font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 10px; font-weight: bold; color: {Theme.ACCENT_CYAN};")
        self.progress_crossfade = QProgressBar()
        self.progress_crossfade.setRange(0, 100)
        self.progress_crossfade.setValue(0)
        self.progress_crossfade.setFixedHeight(6)
        self.progress_crossfade.setTextVisible(False)
        self.progress_crossfade.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Theme.SURFACE_INPUT};
                border: 1px solid {Theme.BORDER_SUBTLE};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {Theme.COLOR_SUCCESS};
                border-radius: 2px;
            }}
        """)
        telemetry_box.addWidget(self.lbl_fade_countdown)
        telemetry_box.addWidget(self.progress_crossfade)
        playback_layout.addLayout(telemetry_box)

        playback_layout.addStretch()

        self.lbl_cue_status = QLabel("STATUS: STANDBY | SELECT CUE OR PRESS [GO+]")
        self.lbl_cue_status.setStyleSheet(f"font-weight: 800; color: {Theme.ACCENT_AMBER}; font-size: 11px;")
        playback_layout.addWidget(self.lbl_cue_status)

        right_layout.addWidget(playback_box)
        splitter.addWidget(right_box)

        splitter.setSizes([320, 680])
        main_layout.addWidget(splitter, 1)

    # PLAYLIST & SONG SECTION GENERATION
    def _refresh_playlist_view(self) -> None:
        """Repaint this tab's playlist from the shared song library.

        Rebuilt wholesale rather than appended to, because the library can add,
        remove and reorder in one action. Only songs that carry analysis are
        listed here: Perform builds cues from analysis, so an unanalysed file has
        nothing to schedule yet.
        """
        if hasattr(self, "song_panel"):
            self.song_panel.refresh_list()
        entries = [entry for entry in self.song_library.songs if entry.is_analyzed]
        self.playlist = [dict(entry.analysis or {}, file_path=entry.path) for entry in entries]

        widget = getattr(self, "playlist_widget", None)
        if widget is not None:
            self._on_song_selected(widget.currentRow())
        self.auto_sync_to_page()

    def _on_library_selection(self, index: int) -> None:
        """Follow a selection made in another tab."""
        if hasattr(self, "song_panel"):
            self.song_panel._on_library_selection_changed(index)
        self._on_song_selected(index)

    def add_analyzed_song(self, song_data: dict) -> None:
        """Receive a finished analysis from ResultTab and schedule it.

        Routed through the shared library so the song also appears in Analyze
        and Result; the refresh callback then repaints this tab's playlist.
        """
        self.song_library.add_analysis(song_data)

    def _on_song_selected(self, row: int) -> None:
        if not (0 <= row < len(self.playlist)):
            self.cue_table.setRowCount(0)
            self.current_song_cues = []
            self.active_cue_index = -1
            self.lbl_cue_status.setText("STATUS: STANDBY")
            self._on_cue_selection_changed()
            return

        song = self.playlist[row]
        self._populate_song_cues(song)
        self._on_cue_selection_changed()

    def _derive_section_cues(self, song: dict) -> list[dict]:
        """Build the worship section cues for a song.

        Shared by the cue table and the Page export so both surfaces emit the
        same colours. Previously the export used the raw song palette while the
        table applied clamps and scaling, so the same song produced two
        different looks depending on which button was pressed.
        """
        title = song.get("title", "Song")
        quadrant = str(song.get("quadrant", "")).lower()
        base_palette = song.get("palette", {"R": 255, "G": 200, "B": 100, "W": 40})
        r_base = int(base_palette.get("R", 255))
        g_base = int(base_palette.get("G", 200))
        b_base = int(base_palette.get("B", 100))
        w_base = int(base_palette.get("W", 40))

        # Route by the four quadrants in core.models.EmotionCoordinate:
        #   Q1_PRAISE_HIGH        high valence, high arousal  -> Praise
        #   Q2_INTENSE_REVERENCE  low valence,  high arousal  -> Reverence
        #   Q3_DEEP_WORSHIP       low valence,  low arousal   -> Worship
        #   Q4_PEACE_INTIMACY     high valence, low arousal   -> Worship
        # Q2 used to fall into the Praise branch because only q3/q4 matched, so a
        # solemn but driving song was lit as joyful praise ("Praise Energy Rise").
        is_reverence = "q2" in quadrant or "reverence" in quadrant
        is_worship = (not is_reverence) and (
            "worship" in quadrant or "q3" in quadrant or "q4" in quadrant
        )

        if is_reverence:
            # Q2_INTENSE_REVERENCE: low valence with HIGH arousal. Solemn weight
            # carried by a driving, high-energy dynamic: deep saturated blues and
            # ambers, strong dimmer, brisk chases. Distinct from the Praise set
            # (joyful, high valence) and from the Worship set (calm, low arousal).
            cues = [
                {
                    "section": "Intro",
                    "mood": "Reverent Awe (Low Wash)",
                    "fade_in": 2.5,
                    "fade_out": 2.0,
                    "dimmer": 165,
                    "chase_rate": 0.7,
                    "color": {"R": max(30, int(r_base * 0.5)), "G": max(40, int(g_base * 0.5)), "B": max(150, int(b_base * 1.1)), "W": 25},
                },
                {
                    "section": "Verse 1",
                    "mood": "Deep Conviction",
                    "fade_in": 1.8,
                    "fade_out": 1.8,
                    "dimmer": 205,
                    "chase_rate": 1.0,
                    "color": {"R": max(190, int(r_base * 0.95)), "G": max(90, int(g_base * 0.6)), "B": 55, "W": 80},
                },
                {
                    "section": "Chorus",
                    "mood": "Majestic Surge",
                    "fade_in": 1.2,
                    "fade_out": 1.6,
                    "dimmer": 250,
                    "chase_rate": 1.6,
                    "color": {"R": 255, "G": 120, "B": 60, "W": 110},
                },
                {
                    "section": "Verse 2",
                    "mood": "Intimate Soft Lavender",
                    "fade_in": 2.0,
                    "fade_out": 2.0,
                    "dimmer": 180,
                    "chase_rate": 0.8,
                    "color": {"R": 170, "G": 90, "B": 230, "W": 50},
                },
                {
                    "section": "Bridge",
                    "mood": "Holy Surrender (Altar Call)",
                    "fade_in": 2.5,
                    "fade_out": 2.0,
                    "dimmer": 255,
                    "chase_rate": 1.0,
                    "color": {"R": 230, "G": 230, "B": 255, "W": 255},
                },
                {
                    "section": "Ending",
                    "mood": "Quiet Peaceful Night",
                    "fade_in": 3.0,
                    "fade_out": 4.0,
                    "dimmer": 100,
                    "chase_rate": 0.5,
                    "color": {"R": 15, "G": 30, "B": 160, "W": 0},
                },
            ]
        elif is_worship:
            # Worship: Deep reverence, meditative intro, sacred altar call, high white ratio
            cues = [
                {
                    "section": "Intro",
                    "mood": "Deep Sanctuary Atmosphere",
                    "fade_in": 3.0,
                    "fade_out": 2.5,
                    "dimmer": 140,
                    "chase_rate": 0.5,
                    "color": {"R": max(20, int(r_base * 0.4)), "G": max(30, int(g_base * 0.5)), "B": max(180, int(b_base * 1.2)), "W": 20},
                },
                {
                    "section": "Verse 1",
                    "mood": "Warm Prayerful Reflection",
                    "fade_in": 2.0,
                    "fade_out": 2.0,
                    "dimmer": 180,
                    "chase_rate": 0.8,
                    "color": {"R": max(180, int(r_base * 0.9)), "G": max(130, int(g_base * 0.8)), "B": 40, "W": 90},
                },
                {
                    "section": "Chorus",
                    "mood": "Majestic Sacred Reverence",
                    "fade_in": 1.5,
                    "fade_out": 2.0,
                    "dimmer": 240,
                    "chase_rate": 1.2,
                    "color": {"R": 255, "G": 210, "B": 90, "W": 130},
                },
                {
                    "section": "Verse 2",
                    "mood": "Intimate Soft Lavender",
                    "fade_in": 2.0,
                    "fade_out": 2.0,
                    "dimmer": 180,
                    "chase_rate": 0.8,
                    "color": {"R": 170, "G": 90, "B": 230, "W": 50},
                },
                {
                    "section": "Bridge",
                    "mood": "Holy Surrender (Altar Call)",
                    "fade_in": 2.5,
                    "fade_out": 2.0,
                    "dimmer": 255,
                    "chase_rate": 1.0,
                    "color": {"R": 230, "G": 230, "B": 255, "W": 255},
                },
                {
                    "section": "Ending",
                    "mood": "Quiet Peaceful Night",
                    "fade_in": 3.0,
                    "fade_out": 4.0,
                    "dimmer": 100,
                    "chase_rate": 0.5,
                    "color": {"R": 15, "G": 30, "B": 160, "W": 0},
                },
            ]
        else:
            # Praise: High energy, bright saturated color, faster chase, triumphant hits
            cues = [
                {
                    "section": "Intro",
                    "mood": "Praise Energy Rise",
                    "fade_in": 1.5,
                    "fade_out": 1.5,
                    "dimmer": 210,
                    "chase_rate": 1.5,
                    "color": {"R": 255, "G": 160, "B": 20, "W": 30},
                },
                {
                    "section": "Verse 1",
                    "mood": "Joyful Groove (Cyan/Yellow)",
                    "fade_in": 1.0,
                    "fade_out": 1.5,
                    "dimmer": 200,
                    "chase_rate": 1.5,
                    "color": {"R": 240, "G": 220, "B": 30, "W": 20},
                },
                {
                    "section": "Chorus",
                    "mood": "Shout of Victory (Full Dynamic)",
                    "fade_in": 0.8,
                    "fade_out": 1.0,
                    "dimmer": 255,
                    "chase_rate": 2.5,
                    "color": {"R": 255, "G": 50, "B": 190, "W": 50},
                },
                {
                    "section": "Verse 2",
                    "mood": "Stepping Forward (Emerald)",
                    "fade_in": 1.0,
                    "fade_out": 1.5,
                    "dimmer": 200,
                    "chase_rate": 1.5,
                    "color": {"R": 30, "G": 240, "B": 80, "W": 30},
                },
                {
                    "section": "Bridge",
                    "mood": "Blazing Anthem Build",
                    "fade_in": 1.0,
                    "fade_out": 1.0,
                    "dimmer": 255,
                    "chase_rate": 2.0,
                    "color": {"R": 255, "G": 100, "B": 0, "W": 40},
                },
                {
                    "section": "Ending",
                    "mood": "Triumphant Flash & Hit",
                    "fade_in": 0.5,
                    "fade_out": 3.0,
                    "dimmer": 255,
                    "chase_rate": 1.0,
                    "color": {"R": 255, "G": 255, "B": 180, "W": 120},
                },
            ]

        return cues

    def _populate_song_cues(self, song: dict) -> None:
        """Render the derived or custom section cues into the cue table."""
        cues = song.get("custom_cues") or self._derive_section_cues(song)
        self.current_song_cues = list(cues)
        self.active_cue_index = -1
        self._render_cues_to_table(self.current_song_cues)
        self.lbl_cue_status.setText(f"READY: {song.get('title', 'Song')} ({len(cues)} Section Cues)")
        self._on_cue_selection_changed()

    def _render_cues_to_table(self, cues: list[dict]) -> None:
        self.cue_table.setRowCount(len(cues))
        for row, cue in enumerate(cues):
            it_sec = QTableWidgetItem(cue.get("section", "Cue"))
            it_sec.setFont(QFont("Inter", 10, QFont.Bold))
            it_sec.setForeground(QColor(Theme.TEXT_PRIMARY))
            self.cue_table.setItem(row, 0, it_sec)

            it_mood = QTableWidgetItem(cue.get("mood", "-"))
            it_mood.setForeground(QColor(Theme.ACCENT_CYAN))
            self.cue_table.setItem(row, 1, it_mood)

            it_fi = QTableWidgetItem(f"{float(cue.get('fade_in', 2.0)):.1f}s")
            it_fi.setTextAlignment(Qt.AlignCenter)
            it_fi.setForeground(QColor(Theme.COLOR_SUCCESS))
            self.cue_table.setItem(row, 2, it_fi)

            it_fo = QTableWidgetItem(f"{float(cue.get('fade_out', 2.0)):.1f}s")
            it_fo.setTextAlignment(Qt.AlignCenter)
            it_fo.setForeground(QColor(Theme.COLOR_WARNING))
            self.cue_table.setItem(row, 3, it_fo)

            dim_val = int(cue.get("dimmer", 255))
            it_dim = QTableWidgetItem(f"{int(dim_val * 100 / 255)}%")
            it_dim.setTextAlignment(Qt.AlignCenter)
            it_dim.setForeground(QColor(Theme.TEXT_PRIMARY))
            self.cue_table.setItem(row, 4, it_dim)

            # Trigger Button in Table
            btn_go = QPushButton("GO")
            btn_go.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Theme.STATUS_SUCCESS_BG};
                    border: 1px solid {Theme.COLOR_SUCCESS};
                    color: {Theme.COLOR_SUCCESS};
                    font-weight: 800;
                    font-size: 10px;
                    padding: 3px 8px;
                }}
                QPushButton:hover {{
                    background-color: {Theme.COLOR_SUCCESS};
                    color: {Theme.BG_ROOT};
                }}
            """)
            btn_go.clicked.connect(lambda _, r=row: self._trigger_cue_at_row(r))
            self.cue_table.setCellWidget(row, 5, btn_go)

    def _on_cue_selection_changed(self) -> None:
        r = self.cue_table.currentRow()
        has_sel = 0 <= r < len(self.current_song_cues)
        self.btn_cue_edit.setEnabled(has_sel)
        self.btn_cue_remove.setEnabled(has_sel)
        self.btn_cue_up.setEnabled(has_sel and r > 0)
        self.btn_cue_down.setEnabled(has_sel and 0 <= r < len(self.current_song_cues) - 1)

    def _on_add_cue_clicked(self) -> None:
        if not self.playlist:
            return
        default_cue = {
            "section": f"Section {len(self.current_song_cues) + 1}",
            "mood": "Custom Atmosphere",
            "fade_in": 2.0,
            "fade_out": 2.0,
            "dimmer": 255,
            "color": {"R": 255, "G": 200, "B": 100, "W": 50},
        }
        dlg = EditCueDialog(default_cue, is_new=True, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.current_song_cues.append(dlg.cue)
            curr_row = self.playlist_widget.currentRow()
            if 0 <= curr_row < len(self.playlist):
                self.playlist[curr_row]["custom_cues"] = list(self.current_song_cues)
            self._render_cues_to_table(self.current_song_cues)
            self.auto_sync_to_page()

    def _on_edit_cue_clicked(self) -> None:
        r = self.cue_table.currentRow()
        if not (0 <= r < len(self.current_song_cues)):
            return
        dlg = EditCueDialog(self.current_song_cues[r], is_new=False, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.current_song_cues[r] = dlg.cue
            curr_row = self.playlist_widget.currentRow()
            if 0 <= curr_row < len(self.playlist):
                self.playlist[curr_row]["custom_cues"] = list(self.current_song_cues)
            self._render_cues_to_table(self.current_song_cues)
            self.auto_sync_to_page()

    def _on_remove_cue_clicked(self) -> None:
        r = self.cue_table.currentRow()
        if not (0 <= r < len(self.current_song_cues)):
            return
        sec = self.current_song_cues[r].get("section", "Cue")
        reply = QMessageBox.question(
            self, "Remove Cue", f"Remove cue '{sec}' from sequence?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            del self.current_song_cues[r]
            curr_row = self.playlist_widget.currentRow()
            if 0 <= curr_row < len(self.playlist):
                self.playlist[curr_row]["custom_cues"] = list(self.current_song_cues)
            self._render_cues_to_table(self.current_song_cues)
            self.auto_sync_to_page()

    def _on_move_cue_clicked(self, delta: int) -> None:
        r = self.cue_table.currentRow()
        target = r + delta
        if not (0 <= r < len(self.current_song_cues) and 0 <= target < len(self.current_song_cues)):
            return
        self.current_song_cues[r], self.current_song_cues[target] = self.current_song_cues[target], self.current_song_cues[r]
        curr_row = self.playlist_widget.currentRow()
        if 0 <= curr_row < len(self.playlist):
            self.playlist[curr_row]["custom_cues"] = list(self.current_song_cues)
        self._render_cues_to_table(self.current_song_cues)
        self.cue_table.setCurrentCell(target, 0)
        self.auto_sync_to_page()

    def _on_fade_idle_clicked(self) -> None:
        self.reset_crossfade_progress()
        self.lbl_cue_status.setText("ACTIVE: [STANDBY IDLE] | Fade: 3.0s")
        for r in range(self.cue_table.rowCount()):
            for c in range(5):
                it = self.cue_table.item(r, c)
                if it: it.setBackground(QColor("transparent"))
        self.cue_activated.emit({
            "type": "scene",
            "active": True,
            "dimmer": 80,
            "color": {"R": 180, "G": 100, "B": 30, "W": 60},
            "fade_time": 3.0,
        })

    def auto_sync_to_page(self) -> None:
        """Collect all cues from all active songs in the playlist, in order, and emit to Page."""
        all_cues = []
        for song_idx, song in enumerate(self.playlist, 1):
            song_cues = song.get("custom_cues") or self._derive_section_cues(song)
            song_title = song.get("title", f"Song {song_idx}")
            for cue in song_cues:
                sec = cue.get("section", "Cue")
                all_cues.append({
                    "label": f"[{song_idx}] {sec}\n{song_title[:10]}",
                    "section": sec,
                    "song_title": song_title,
                    "song_index": song_idx,
                    "type": "scene",
                    "dimmer": cue.get("dimmer", 255),
                    "color": cue.get("color", {"R": 255, "G": 255, "B": 255, "W": 0}),
                    "fade_time": cue.get("fade_in", 2.0),
                })
        self.export_to_page.emit(all_cues)

    # CUE PLAYBACK & MASTER GO+ ENGINE
    def _trigger_cue_at_row(self, row: int) -> None:
        if not (0 <= row < len(self.current_song_cues)):
            return

        self.active_cue_index = row
        cue = self.current_song_cues[row]

        # Highlight active row in table
        for r in range(self.cue_table.rowCount()):
            for c in range(5):
                it = self.cue_table.item(r, c)
                if it:
                    if r == row:
                        it.setBackground(QColor(Theme.STATUS_ACTIVE_CUE_BG))
                    else:
                        it.setBackground(QColor("transparent"))

        self.cue_table.selectRow(row)

        sec_name = cue.get("section", "Cue")
        fade_time = float(cue.get("fade_in", 1.5))
        self.lbl_cue_status.setText(f"ACTIVE: [{sec_name.upper()} | {cue['mood']}] | Fade: {fade_time:.1f}s")

        # Emit to MainWindow for smooth crossfade
        payload = {
            "type": "scene",
            "active": True,
            "label": sec_name,
            "dimmer": cue.get("dimmer", 255),
            "color": cue.get("color", {"R": 255, "G": 255, "B": 255, "W": 0}),
            "fade_time": fade_time,
        }
        self.cue_activated.emit(payload)

    def set_crossfade_progress(self, progress: float, elapsed: float, total: float) -> None:
        """Updates live master crossfade countdown and telemetry."""
        clamped = max(0.0, min(1.0, float(progress)))
        if total <= 0.0:
            self.reset_crossfade_progress()
            return
        if hasattr(self, 'progress_crossfade'):
            self.progress_crossfade.setValue(int(clamped * 100))
        if hasattr(self, 'lbl_fade_countdown'):
            if clamped >= 1.0:
                self.lbl_fade_countdown.setText(f"FADE: {total:.1f}s | COMPLETE")
            else:
                rem = max(0.0, total - elapsed)
                self.lbl_fade_countdown.setText(f"FADE: {rem:.1f}s ({int(clamped * 100)}%)")

    def reset_crossfade_progress(self) -> None:
        """Returns transition telemetry to idle when a new cue or instant action begins."""
        if hasattr(self, "progress_crossfade"):
            self.progress_crossfade.setValue(0)
        if hasattr(self, "lbl_fade_countdown"):
            self.lbl_fade_countdown.setText("FADE: IDLE | 0.0s")

    def _on_go_clicked(self) -> None:
        """Master GO+ / Next Cue trigger."""
        if not self.current_song_cues:
            return

        next_row = self.active_cue_index + 1
        if next_row >= len(self.current_song_cues):
            # Advance to next song if available
            curr_song_row = self.playlist_widget.currentRow()
            if curr_song_row + 1 < len(self.playlist):
                self.playlist_widget.setCurrentRow(curr_song_row + 1)
                next_row = 0
            else:
                next_row = 0  # Loop back to start

        self._trigger_cue_at_row(next_row)

    def _on_prev_clicked(self) -> None:
        """Trigger previous cue."""
        if not self.current_song_cues:
            return
        prev_row = max(0, self.active_cue_index - 1)
        self._trigger_cue_at_row(prev_row)

    def _on_fade_black_clicked(self) -> None:
        """Smoothly fade to blackout over 2.5s."""
        # Forget the active cue and clear the transition telemetry so the next
        # GO+ starts from a clean state. Previously the index stayed current, so
        # a second FADE BLACK resumed as if a cue were still playing.
        self.active_cue_index = -1
        self.reset_crossfade_progress()

        self.lbl_cue_status.setText("ACTIVE: [BLACKOUT] | Fade: 2.5s")
        # Deselect rows
        for r in range(self.cue_table.rowCount()):
            for c in range(5):
                it = self.cue_table.item(r, c)
                if it: it.setBackground(QColor("transparent"))

        self.cue_activated.emit({
            "type": "scene",
            "active": False,
            "dimmer": 0,
            "color": {"R": 0, "G": 0, "B": 0, "W": 0},
            "fade_time": 2.5,
        })

    # PLAYLIST REORDERING & EXPORT TO PAGE
    def _on_move_up(self) -> None:
        """Reorder in the shared library, so every tab sees the new order."""
        row = self.playlist_widget.currentRow()
        if row > 0:
            self.song_library.move(row, -1)
            self._refresh_playlist_view()
            self.playlist_widget.setCurrentRow(row - 1)

    def _on_move_down(self) -> None:
        row = self.playlist_widget.currentRow()
        if 0 <= row < len(self.song_library) - 1:
            self.song_library.move(row, 1)
            self._refresh_playlist_view()
            self.playlist_widget.setCurrentRow(row + 1)

    def _on_delete_song(self) -> None:
        """Remove from the shared library, so the song leaves every tab."""
        row = self.playlist_widget.currentRow()
        if 0 <= row < len(self.song_library):
            self.song_library.remove([row])
            if self.playlist_widget.count():
                self.playlist_widget.setCurrentRow(
                    min(row, self.playlist_widget.count() - 1))

    def _on_export_to_page(self) -> None:
        """Generates executor cues across all songs and pushes to PageTab."""
        if not self.playlist:
            QMessageBox.warning(self, "Empty Playlist", "Add songs to the playlist before exporting to Page.")
            return

        generated_cues = []
        for song in self.playlist:
            title = song.get("title", "Song")
            short_title = title.split("(")[0].strip()[:14]
            quadrant = str(song.get("quadrant", "")).lower()
            is_worship = ("worship" in quadrant or "q3" in quadrant or "q4" in quadrant)
            # Derive the colours exactly as the cue table does, so the exported
            # executors match what the operator previewed.
            sections = self._derive_section_cues(song)
            verse_palette = dict(sections[1]["color"]) if len(sections) > 1 else {"R": 255, "G": 255, "B": 255, "W": 0}
            chorus_palette = dict(sections[2]["color"]) if len(sections) > 2 else verse_palette
            palette = verse_palette

            # 1. Verse Cue
            generated_cues.append({
                "label": f"{short_title}\n(Verse)",
                "type": "scene",
                "color": palette,
                "dimmer": 180,
                "fade_time": 2.0,
            })
            # 2. Chorus Cue
            generated_cues.append({
                "label": f"{short_title}\n(Chorus)",
                "type": "scene",
                "color": chorus_palette,
                "dimmer": 255,
                "fade_time": 1.2 if is_worship else 0.8,
            })
            # 3. Flash Hit Button
            generated_cues.append({
                "label": f"FLASH\n{short_title[:8]}",
                "type": "flash",
                "color": {"R": 255, "G": 255, "B": 255, "W": 255},
                "dimmer": 255,
                "fade_time": 0.0,
            })

        self.export_to_page.emit(generated_cues)
        QMessageBox.information(
            self,
            "Executors Generated",
            f"Successfully generated {len(generated_cues)} virtual executor buttons in Page Tab!",
        )
