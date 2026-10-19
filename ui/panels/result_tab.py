"""
result_tab.py | Analysis Results & Affective Dashboard
Displays MIR acoustic metrics, Russell 2D Plane, mood quadrant, and provides
the 'Export to Perform' workflow trigger.
"""

from __future__ import annotations

from ui.qt_compat import (
    HAS_QT, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QSplitter,
    QListWidget,
    Qt, Signal, QColor, QFont
)
from ui.styles import Theme
from core.song_library import SongLibrary
from ui.widgets.song_list_panel import SongListPanel
from ui.panels.analyze_tab import RussellPlaneWidget


class ResultTab(QWidget if HAS_QT else object):
    """Result Tab: Summarizes extracted audio analysis and exports cue sequences to Perform."""
    export_to_perform = Signal(dict)
    reanalyze_requested = Signal()

    def __init__(self, project_state=None, parent: QWidget | None = None,
                 song_library=None):
        if not HAS_QT: return
        super().__init__(parent)
        self.project_state = project_state
        self.song_library = song_library if song_library is not None else SongLibrary()
        self.song_library.on_changed(self._refresh_song_list)
        self.song_library.on_selection_changed(self._on_library_selection)
        self.current_analysis: dict | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(12)

        # Header Title
        top_bar = QHBoxLayout()

        top_bar.addStretch()

        self.btn_reanalyze = QPushButton("RE-ANALYZE")
        self.btn_reanalyze.clicked.connect(lambda: self.reanalyze_requested.emit())
        top_bar.addWidget(self.btn_reanalyze)

        # Retained as internal attribute for automated testing; export is now automatic
        self.btn_export = QPushButton("EXPORT TO PERFORM")
        self.btn_export.setEnabled(False)
        self.btn_export.setVisible(False)
        self.btn_export.clicked.connect(self._on_export_clicked)

        main_layout.addLayout(top_bar)

        # Content Splitter
        splitter = QSplitter(Qt.Horizontal)

        # Songs first, then metrics, then the plane. The list is on the left
        # because Result describes whichever song is selected, and a reading
        # surface with no visible subject makes the operator hunt for what the
        # numbers belong to. It mirrors the left panel in Analyze and Perform.
        # Standardized Song List Panel on the left
        self.song_panel = SongListPanel(self.song_library, self)
        self.song_list_widget = self.song_panel.list_widget
        self.song_panel.song_selected.connect(self._on_song_row_selected)
        splitter.addWidget(self.song_panel)
        self.song_list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {Theme.SURFACE_INPUT};
                border: 1px solid {Theme.BORDER_SUBTLE};
                border-radius: 4px;
                color: {Theme.TEXT_PRIMARY};
            }}
            QListWidget::item {{
                padding: 6px 8px;
                border-bottom: 1px solid {Theme.BORDER_SUBTLE};
            }}
            QListWidget::item:selected {{
                background-color: {Theme.SURFACE_HOVER};
                color: {Theme.TEXT_PRIMARY};
            }}
        """)

        # Left: Metric Details Table
        left_box = QGroupBox("Acoustic Metrics & Song Characteristics")
        left_box.setStyleSheet(f"QGroupBox {{ font-weight: 700; color: {Theme.TEXT_PRIMARY}; }}")
        left_layout = QVBoxLayout(left_box)

        self.table = QTableWidget(12, 2)
        self.table.setHorizontalHeaderLabels(["Scientific & DSP Parameter", "Computed Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)

        metrics = [
            ("Song Title", "No analysis yet"),
            ("Estimated Tempo", "-"),
            ("Duration & STFT Frames", "-"),
            ("RMS Energy (Parseval)", "-"),
            ("Spectral Centroid", "-"),
            ("Chroma STFT & Tonality", "-"),
            ("MFCC Acoustic Density", "-"),
            ("Spectral Flux (Onsets)", "-"),
            ("Valence (Mood)", "-"),
            ("Arousal (Energy)", "-"),
            ("Quadrant Classification", "-"),
            ("Physical RGBW Decomposition", "-"),
        ]
        for row, (param, val) in enumerate(metrics):
            i1 = QTableWidgetItem(param)
            i2 = QTableWidgetItem(val)
            i1.setFont(QFont("Inter", 9, QFont.Bold))
            i2.setFont(QFont("JetBrains Mono", 9))
            i1.setForeground(QColor(Theme.TEXT_PRIMARY))
            i2.setForeground(QColor(Theme.ACCENT_CYAN))
            self.table.setItem(row, 0, i1)
            self.table.setItem(row, 1, i2)

        left_layout.addWidget(self.table)
        splitter.addWidget(left_box)

        # Right: Russell 2D Plane Display
        right_box = QGroupBox("Russell Emotion Plane Mapping (Valence-Arousal)")
        right_box.setStyleSheet(f"QGroupBox {{ font-weight: 700; color: {Theme.TEXT_PRIMARY}; }}")
        right_layout = QVBoxLayout(right_box)

        self.russell_plane = RussellPlaneWidget()
        right_layout.addWidget(self.russell_plane, alignment=Qt.AlignCenter)

        self.lbl_palette_desc = QLabel("Stage Color Palette: Not assigned.")
        self.lbl_palette_desc.setStyleSheet(f"font-size: 12px; color: {Theme.TEXT_SECONDARY};")
        self.lbl_palette_desc.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.lbl_palette_desc)

        splitter.addWidget(right_box)
        splitter.setSizes([550, 450])
        main_layout.addWidget(splitter, 1)

    def _refresh_song_list(self) -> None:
        """Repaint the song list from the shared library."""
        if hasattr(self, "song_panel"):
            self.song_panel.refresh_list()
        widget = getattr(self, "song_list_widget", None)
        if widget is not None:
            self._on_song_row_selected(widget.currentRow())

    def _on_song_row_selected(self, row: int) -> None:
        """Display the metrics of the song the operator picked in the list.

        A song that has no analysis must clear the card, not leave the previous
        song's numbers and an enabled Export behind. Only the analysed branch was
        handled, so selecting an unanalysed track (or switching to a file that is
        still queued) left the dashboard describing a song the operator no longer
        had selected, and Export would send that stale result to Perform.
        """
        self.song_library.select(row)
        entry = self.song_library.songs[row] if 0 <= row < len(self.song_library) else None
        if entry is not None and entry.is_analyzed:
            self.load_analysis_result(dict(entry.analysis or {}))
        else:
            self._show_no_analysis()

    def _show_no_analysis(self) -> None:
        """Clear the metrics card and disable Export for a song with no result."""
        self.current_analysis = None
        self.btn_export.setEnabled(False)
        self.russell_plane.set_coordinates(0.0, 0.0, "Idle")
        self.lbl_palette_desc.setText("<b>Recommended Stage Lighting Color:</b> not assigned.")
        for row in range(self.table.rowCount()):
            value_item = self.table.item(row, 1)
            if value_item is None:
                continue
            value_item.setText("No analysis yet" if row == 0 else "-")

    def _on_library_selection(self, index: int) -> None:
        """Follow a selection made in another tab.

        Moving the highlight is not enough: the widget's currentRowChanged is
        blocked while repainting, so the metrics card was never refreshed and
        kept describing whatever song was on screen before. Selecting lagu_A
        after lagu_B used to leave lagu_B's numbers in the table, and a song
        with no analysis showed the previous song's metrics instead of the
        "No analysis yet" placeholder. Load the selected song's own result.
        """
        widget = getattr(self, "song_list_widget", None)
        if widget is not None and widget.currentRow() != index:
            widget.blockSignals(True)
            widget.setCurrentRow(index)
            widget.blockSignals(False)
        self._on_song_row_selected(index)

    def load_analysis_result(self, res: dict) -> None:
        """Loads and visualizes analysis data from AnalyzeTab."""
        self.current_analysis = res

        # Only offer Export when the result carries real, usable numbers.
        # Previously every row was rendered from a plausible numeric default
        # (centroid 1850 Hz, MFCC 0.500, BPM 120, a white RGBW palette), so a
        # partial result read as a complete measurement and Export was enabled
        # for data that did not exist.
        required = ("bpm", "valence", "arousal", "rms", "palette")
        analysed = res.get("frames_count", 0) > 1 and all(res.get(k) is not None for k in required)
        self.btn_export.setEnabled(analysed)

        def value(key, default=None):
            """Return the recorded value or None, never a stand-in number."""
            raw = res.get(key)
            return default if raw is None else raw

        def show(fmt: str, key: str, fallback: str = "- (not measured)") -> str:
            raw = res.get(key)
            if raw is None:
                return fallback
            try:
                return fmt.format(raw)
            except (TypeError, ValueError):
                return fallback

        v = float(res.get("valence", 0.0))
        a = float(res.get("arousal", 0.0))
        quad = res.get("quadrant", "Idle")

        self.russell_plane.set_coordinates(v, a, quad)

        palette = res.get("palette")
        has_palette = isinstance(palette, dict) and bool(palette)
        r = palette.get("R") if has_palette else None
        g = palette.get("G") if has_palette else None
        b = palette.get("B") if has_palette else None
        w = palette.get("W") if has_palette else None

        frames_cnt = res.get("frames_count")
        fps_rate = value("fps_rate")

        vals = [
            res.get("title", "Untitled"),
            show("{:.1f} BPM (Beat Tracking)", "bpm"),
            show("{:.1f}s", "duration_sec") if value("duration_sec") is not None else "- (not measured)",
            show("{:.3f} (Dinamika Master Dimmer)", "rms"),
            show("{:.1f} Hz (Kecerahan Timbre Audio)", "spectral_centroid"),
            res.get("chroma_key", "- (not measured)"),
            show("{:.3f} / 1,000 (Indeks Tekstur Akustik Ternormalisasi)", "mfcc_density"),
            show("{:.3f} / 1,000 (Kepadatan Onset Ritmik Ternormalisasi)", "spectral_flux"),
            f"{v:+.2f} ({'Praise/Joyful' if v >= 0 else 'Worship/Solemn'})",
            f"{a:+.2f} ({'Dynamic/High' if a >= 0 else 'Ambient/Calm'})",
            f"{quad}",
            (f"R:{r} G:{g} B:{b} W:{w} (Anti-Washout)" if has_palette
             else "- (no palette assigned)"),
        ]
        for row, val_str in enumerate(vals):
            self.table.item(row, 1).setText(val_str)

        # Fold the frame/rate detail into the duration cell only when known.
        if frames_cnt is not None and fps_rate is not None:
            self.table.item(2, 1).setText(
                f"{res.get('duration_sec', 0.0):.1f}s ({frames_cnt:,} Frame @ {fps_rate:.2f} FPS)"
            )

        if has_palette:
            self.lbl_palette_desc.setText(
                f"<b>Recommended Stage Lighting Color:</b><br>"
                f"<span style='color: rgb({r},{g},{b}); font-size: 14px;'>"
                f"RGBW: ({r}, {g}, {b}, {w})</span>"
            )
        else:
            self.lbl_palette_desc.setText("<b>Recommended Stage Lighting Color:</b> not assigned.")

    def _on_export_clicked(self) -> None:
        if self.current_analysis:
            self.export_to_perform.emit(self.current_analysis)
