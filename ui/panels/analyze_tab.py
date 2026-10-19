"""
analyze_tab.py | Core Skripsi Audio Analysis & Affective Mood Recognition Panel
Integrates STFT Engine, Spectral Feature Extraction, YouTube Audio Importer,
and Russell 2D Affective Plane Mapping via non-blocking asynchronous QThread.
"""

from __future__ import annotations
import os
import time
import numpy as np
from pathlib import Path

from ui.qt_compat import (
    HAS_QT, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QProgressBar, QFrame, QFileDialog, QMessageBox,
    QSplitter, QGroupBox, QGridLayout, Qt, Signal, QThread,
    QPainter, QColor, QPen, QBrush, QFont
)
from ui.styles import Theme
from core.song_library import SongLibrary
from ui.widgets.youtube_dialog import YouTubeDialog
from ui.widgets.song_list_panel import SongListPanel, AddSongDialog
from core.audio_loader import AudioLoader
from core.feature_extractor import FeatureExtractor
from core.emotion_model import EmotionModel
from core.models import EmotionCoordinate


class AudioAnalysisWorker(QThread if HAS_QT else object):
    """Background worker thread executing STFT & MIR analysis asynchronously."""
    progress_updated = Signal(int, str)  # (percent, scientific_status)
    analysis_finished = Signal(dict)     # (analysis_results_dict)
    analysis_failed = Signal(str)        # (error_message)

    def __init__(self, file_path: str):
        if not HAS_QT: return
        super().__init__()
        self.file_path = file_path

    def run(self) -> None:
        try:
            self.progress_updated.emit(10, "Loading audio file (decoding signal to PCM 22,050 Hz)...")
            loader = AudioLoader()
            signal, _loaded_sample_rate = loader.load_audio(self.file_path)

            self.progress_updated.emit(25, "Applying Hann windowing (N=2048, H=512) to attenuate spectral leakage...")
            time.sleep(0.2)

            self.progress_updated.emit(45, "Computing FFT & extracting Spectral Centroid...")
            extractor = FeatureExtractor()
            frames = extractor.analyze_audio_stream(signal)
            time.sleep(0.2)

            self.progress_updated.emit(65, "Extracting 12-semitone Chroma STFT for tonality analysis...")
            time.sleep(0.2)

            self.progress_updated.emit(85, "Computing 13 MFCC coefficients & Spectral Flux onset detection...")
            time.sleep(0.2)

            self.progress_updated.emit(95, "Mapping affective coordinates to Russell 2D Plane (Valence-Arousal)...")

            # Compute aggregate metrics
            avg_v = sum(f.emotion.valence for f in frames) / len(frames) if frames else 0.0
            avg_a = sum(f.emotion.arousal for f in frames) / len(frames) if frames else 0.0
            avg_rms = sum(f.rms_energy for f in frames) / len(frames) if frames else 0.0
            avg_centroid = sum(f.spectral_centroid for f in frames) / len(frames) if frames else 0.0

            # 1. 12-Semitone Chroma STFT analysis & Tonality Detection
            #
            # Silence and near-silence must not produce a key claim. Every chroma
            # bin is zero for silent input, so argmax() returned index 0 and the
            # report confidently said "C Major (Praise character)" for two
            # seconds of digital silence and even for a zero-sample file. For a
            # research tool that is fabricated evidence, so tonality is gated on
            # the summed chroma energy being above an audibility floor.
            pitch_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
            chroma_sums = [sum(f.chroma_vector[i] for f in frames) for i in range(12)] if frames else [0.0] * 12
            chroma_energy = float(sum(chroma_sums))
            has_tonal_content = bool(frames) and chroma_energy > 1e-6

            if has_tonal_content:
                dominant_idx = int(np.argmax(chroma_sums))
                dominant_pitch = pitch_names[dominant_idx]
                # In musical harmony (Krumhansl profile): Major 3rd (+4 semitones) vs Minor 3rd (+3 semitones)
                maj_energy = chroma_sums[(dominant_idx + 4) % 12]
                min_energy = chroma_sums[(dominant_idx + 3) % 12]
                if maj_energy >= min_energy:
                    tonality_str = f"{dominant_pitch} Major (Praise character)"
                else:
                    tonality_str = f"{dominant_pitch} Minor (Worship character)"
            else:
                dominant_pitch = "-"
                tonality_str = "No tonal content (silent or unanalysable input)"

            # 2. MFCC acoustic texture, on the engine's normalized 0-1 scale.
            #
            # The raw frame-wise mean of |c1..c12| is an unbounded quantity
            # (about 24 to 48 in practice), yet the Result tab labels it an
            # "Index". The engine already provides _normalize_mfcc_contrast(),
            # which min-max normalizes the same contrast to 0-1, so use that and
            # keep the reported number on the scale the label claims.
            if frames and any(f.mfcc_coeffs for f in frames):
                mfcc_matrix = np.array([f.mfcc_coeffs for f in frames], dtype=np.float64).T
                normalized = extractor._normalize_mfcc_contrast(mfcc_matrix)
                mfcc_density = float(np.mean(normalized)) if normalized.size else 0.0
            else:
                mfcc_density = 0.0

            # 3. Spectral flux, likewise normalized to 0-1 by the engine.
            #
            # extract_spectral_flux() returns an unbounded per-frame sum (0 to
            # about 258 on real audio). extract_onset_strength() normalizes that
            # same flux by its track peak, matching the "Density" label.
            stft_mat = extractor.stft_engine.compute_stft(signal)
            mag_spec = extractor.stft_engine.compute_magnitude_spectrogram(stft_mat)
            onset_vals = extractor.extract_onset_strength(mag_spec)
            spectral_flux = float(np.mean(onset_vals)) if len(onset_vals) > 0 else 0.0

            # A quadrant only means something when there is audio to classify.
            # Silence produced valence 0 and arousal 0, which the quadrant
            # mapping still resolved into a worship quadrant, so the report read
            # as a real affective finding for empty input.
            if has_tonal_content:
                quad = EmotionCoordinate(valence=avg_v, arousal=avg_a).quadrant
            else:
                quad = "Idle"

            # Palette representative.
            #
            # The palette must describe the SAME moment as the Valence and Arousal
            # this report shows, and those are track averages. It used to be taken
            # from frames[len//2], a single middle frame, so the table printed an
            # average mood next to the colour of one arbitrary instant. On a track
            # whose mood moves, the two disagreed: measured on a calm-dark then
            # loud-bright signal, the average was V=+0.00 A=+0.14 while the middle
            # frame read V=+0.03 A=+0.54, and the exported "RGBW algoritmik" column
            # of Bab 4 Tabel 4.6 is defined per track, alongside average V/A. Feed
            # the averages back through the same ColorEngine so the palette is the
            # colour of the reported mood. When there is no analysable audio, fall
            # back to the neutral centre the engine would produce anyway.
            if has_tonal_content:
                representative = extractor.color_engine.process_frame(
                    EmotionCoordinate(valence=avg_v, arousal=avg_a),
                    rms_energy=avg_rms,
                    master_dimmer=1.0,
                )
                palette = {
                    "R": representative.red,
                    "G": representative.green,
                    "B": representative.blue,
                    "W": representative.white,
                }
            else:
                palette = {"R": 0, "G": 0, "B": 0, "W": 0}

            duration_sec = len(signal) / float(extractor.sample_rate)
            bpm_est = extractor.estimate_tempo_bpm(signal)

            result = {
                "file_path": self.file_path,
                "title": Path(self.file_path).stem,
                "duration_sec": duration_sec,
                "frames_count": len(frames),
                "fps_rate": float(extractor.stft_engine.fps),
                "valence": avg_v,
                "arousal": avg_a,
                "rms": avg_rms,
                "spectral_centroid": avg_centroid,
                "chroma_key": tonality_str,
                "dominant_pitch": dominant_pitch,
                "mfcc_density": mfcc_density,
                "spectral_flux": spectral_flux,
                "quadrant": quad,
                "bpm": bpm_est,
                "palette": palette,
            }

            self.progress_updated.emit(100, "Audio acoustic analysis & mood modeling complete.")
            self.analysis_finished.emit(result)

        except Exception as e:
            self.analysis_failed.emit(str(e))


class RussellPlaneWidget(QFrame if HAS_QT else object):
    """Visualizes audio mood coordinate in Russell 2D Valence-Arousal Plane."""
    def __init__(self, parent: QWidget | None = None):
        if not HAS_QT: return
        super().__init__(parent)
        self.setFixedSize(240, 240)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.SURFACE_INPUT};
                border: 1px solid {Theme.BORDER_STRONG};
                border-radius: 6px;
            }}
        """)
        self.valence = 0.0
        self.arousal = 0.0
        self.quadrant_text = "Idle"

    def set_coordinates(self, v: float, a: float, quad: str = ""):
        self.valence = max(-1.0, min(1.0, v))
        self.arousal = max(-1.0, min(1.0, a))
        self.quadrant_text = quad
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        # Axes
        pen_axis = QPen(QColor(Theme.BORDER_STRONG), 1.5, Qt.DashLine)
        painter.setPen(pen_axis)
        painter.drawLine(15, cy, w - 15, cy)
        painter.drawLine(cx, 15, cx, h - 15)

        # Labels
        painter.setFont(QFont("Inter", 8))
        painter.setPen(QColor(Theme.TEXT_MUTED))
        painter.drawText(w - 70, cy - 6, "+V (Praise)")
        painter.drawText(10, cy - 6, "-V (Worship)")
        painter.drawText(cx + 6, 20, "+A (Energetic)")
        painter.drawText(cx + 6, h - 10, "-A (Calm)")

        # Quadrant labels
        painter.setPen(QColor(Theme.ACCENT_AMBER))
        painter.drawText(w - 75, 36, "Q1: Praise")
        painter.setPen(QColor(Theme.ACCENT_CYAN))
        painter.drawText(15, h - 30, "Q3: Worship")

        # Current Mood Point
        px = cx + int(self.valence * (cx - 25))
        py = cy - int(self.arousal * (cy - 25))

        # Glow halo
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(6, 182, 212, 60))
        painter.drawEllipse(px - 12, py - 12, 24, 24)

        # Center dot
        painter.setBrush(QColor(Theme.ACCENT_CYAN))
        painter.drawEllipse(px - 5, py - 5, 10, 10)
        painter.end()


class AnalyzeTab(QWidget if HAS_QT else object):
    """
    Tab Analyze: Core Audio DSP & Mood Analyzer.
    Supports local audio files (.wav, .mp3, .flac, .ogg) and direct YouTube link imports.
    """
    analysis_ready = Signal(dict)

    def __init__(self, project_state=None, parent: QWidget | None = None,
                 song_library=None):
        if not HAS_QT: return
        super().__init__(parent)
        self.project_state = project_state
        self.worker: AudioAnalysisWorker | None = None
        # The shared song list. When the main window supplies one, this tab reads
        # and writes that single list so Analyze, Result and Perform agree; when
        # it does not (tests constructing the tab alone), the tab keeps its own
        # so behaviour stays identical for a single-tab caller.
        self.song_library = song_library if song_library is not None else SongLibrary()
        self.song_library.on_changed(self._refresh_song_list)
        self.song_library.on_selection_changed(self._on_library_selection)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(12)

        # Top Section: Title & Controls
        top_bar = QHBoxLayout()

        top_bar.addStretch()

        self.btn_load_file = QPushButton("LOAD AUDIO...")
        self.btn_load_file.clicked.connect(self._on_load_audio_file)
        top_bar.addWidget(self.btn_load_file)

        self.btn_import_yt = QPushButton("IMPORT YOUTUBE...")
        self.btn_import_yt.setStyleSheet(f"font-weight: 600;")
        self.btn_import_yt.clicked.connect(self._on_open_youtube_dialog)
        top_bar.addWidget(self.btn_import_yt)

        self.btn_analyze = QPushButton("ANALYZE")
        self.btn_analyze.setStyleSheet(f"background-color: {Theme.STATUS_SUCCESS_BG}; color: {Theme.COLOR_SUCCESS}; font-weight: bold;")
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.clicked.connect(self._on_start_analysis)
        top_bar.addWidget(self.btn_analyze)

        main_layout.addLayout(top_bar)

        # Splitter: Left Songlist, Right Visualizer & Progress
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {Theme.BORDER_SUBTLE}; }}")

        # Left Container: Standardized Song List Panel
        self.song_panel = SongListPanel(self.song_library, self)
        self.song_list_widget = self.song_panel.list_widget
        self.btn_remove = self.song_panel.btn_remove  # backward compatibility alias
        self.song_panel.song_selected.connect(self._on_song_selected)
        splitter.addWidget(self.song_panel)

        # Right Container: Analysis Visualization & Status
        right_box = QGroupBox("DSP Engine & Russell 2D Affective Plane")
        right_box.setStyleSheet(f"QGroupBox {{ font-weight: 700; color: {Theme.TEXT_PRIMARY}; }}")
        right_layout = QVBoxLayout(right_box)

        vis_row = QHBoxLayout()
        self.russell_plane = RussellPlaneWidget()
        vis_row.addWidget(self.russell_plane)

        # Stats Card
        self.stats_label = QLabel("Load audio track (.mp3/.wav or YouTube link) and click Analyze.")
        self.stats_label.setStyleSheet(f"font-size: 12px; color: {Theme.TEXT_SECONDARY}; line-height: 1.5;")
        self.stats_label.setWordWrap(True)
        vis_row.addWidget(self.stats_label, 1)
        right_layout.addLayout(vis_row)

        # Scientific Ticker & Progress
        self.lbl_dsp_status = QLabel("Engine ready.")
        self.lbl_dsp_status.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Theme.ACCENT_CYAN};")
        right_layout.addWidget(self.lbl_dsp_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Theme.SURFACE_INPUT};
                border: 1px solid {Theme.BORDER_STRONG};
                border-radius: 4px;
                text-align: center;
                color: {Theme.TEXT_PRIMARY};
                height: 22px;
            }}
            QProgressBar::chunk {{
                background-color: {Theme.ACCENT_AMBER};
                border-radius: 3px;
            }}
        """)
        right_layout.addWidget(self.progress_bar)

        splitter.addWidget(right_box)
        splitter.setSizes([320, 680])
        main_layout.addWidget(splitter, 1)

    def _on_load_audio_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a *.webm *.opus *.aac);;All Files (*.*)",
        )
        if file_path:
            self._add_audio_path(file_path)

    def _on_open_youtube_dialog(self) -> None:
        dlg = YouTubeDialog(self)
        dlg.audio_imported.connect(self._add_audio_path)
        dlg.exec()

    def _refresh_song_list(self) -> None:
        """Repaint this tab's list from the shared library."""
        if hasattr(self, "song_panel"):
            self.song_panel.refresh_list()

    def _on_library_selection(self, index: int) -> None:
        """Follow a selection made in another tab."""
        if hasattr(self, "song_panel"):
            self.song_panel._on_library_selection_changed(index)
        has_sel = 0 <= index < len(self.song_library)
        self.btn_analyze.setEnabled(has_sel)

    def _add_audio_path(self, path_str: str) -> None:
        """Add a track to the shared list, which repaints every tab's view."""
        self.song_library.add_path(path_str)
        self.btn_analyze.setEnabled(True)
        self.lbl_dsp_status.setText(f"Track ready: {Path(path_str).name}")

    def _on_song_selected(self, row: int) -> None:
        """Mirror the list widget's selection into the shared library."""
        has_sel = 0 <= row < len(self.song_library)
        self.btn_analyze.setEnabled(has_sel)
        if has_sel:
            entry = self.song_library.songs[row]
            if entry.is_analyzed and isinstance(entry.analysis, dict):
                res = entry.analysis
                v = float(res.get("valence", 0.0))
                a = float(res.get("arousal", 0.0))
                quad = str(res.get("quadrant", "Idle"))
                self.russell_plane.set_coordinates(v, a, quad)
                bpm = res.get("bpm", 0.0)
                rms = res.get("rms", 0.0)
                key = res.get("chroma_key", "-")
                self.stats_label.setText(
                    f"Track: {entry.title}\n"
                    f"BPM: {bpm:.1f} | RMS: {rms:.4f} | Tonality: {key}\n"
                    f"Mood: {quad} (Valence: {v:+.2f}, Arousal: {a:+.2f})"
                )

    def _on_remove_song(self) -> None:
        if hasattr(self, "song_panel"):
            self.song_panel._on_remove_clicked()

    def _on_start_analysis(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        row = self.song_list_widget.currentRow()
        if not (0 <= row < len(self.song_library)):
            return

        entry = self.song_library.songs[row]
        target_file = entry.path
        self._analysis_target_path = entry.path
        self.btn_analyze.setEnabled(False)
        self.btn_load_file.setEnabled(False)
        self.btn_import_yt.setEnabled(False)
        self.progress_bar.setValue(5)

        self.worker = AudioAnalysisWorker(target_file)
        self.worker.progress_updated.connect(self._on_analysis_progress)
        self.worker.analysis_finished.connect(self._on_analysis_finished)
        self.worker.analysis_failed.connect(self._on_analysis_failed)
        self.worker.finished.connect(self._release_worker)
        self.worker.start()

    def _release_worker(self) -> None:
        """Release the finished worker deterministically so threads are not leaked."""
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None

    def _on_analysis_progress(self, percent: int, msg: str) -> None:
        self.progress_bar.setValue(percent)
        self.lbl_dsp_status.setText(msg)

    def _on_analysis_finished(self, res: dict) -> None:
        self.progress_bar.setValue(100)
        self.btn_analyze.setEnabled(True)
        self.btn_load_file.setEnabled(True)
        self.btn_import_yt.setEnabled(True)

        v = res.get("valence", 0.0)
        a = res.get("arousal", 0.0)
        quad = res.get("quadrant", "Idle")
        bpm = res.get("bpm", 120.0)
        rms = res.get("rms", 0.0)

        self.russell_plane.set_coordinates(v, a, quad)

        self.stats_label.setText(
            f"<b>Track:</b> {res.get('title')}<br>"
            f"<b>Duration:</b> {res.get('duration_sec'):.1f} s | <b>STFT Frames:</b> {res.get('frames_count')}<br>"
            f"<b>Estimated BPM:</b> {bpm:.1f} | <b>RMS Energy:</b> {rms:.3f}<br>"
            f"<b>Russell Affective:</b> Valence = {v:+.2f}, Arousal = {a:+.2f}<br>"
            f"<b>Worship Mood:</b> <span style='color: {Theme.ACCENT_AMBER}; font-weight: bold;'>{quad}</span><br>"
            f"<b>Stage Color:</b> RGBW ({res['palette']['R']}, {res['palette']['G']}, {res['palette']['B']}, {res['palette']['W']})"
        )

        self.analysis_ready.emit(res)

    def _on_analysis_failed(self, err_msg: str) -> None:
        self.btn_analyze.setEnabled(True)
        self.btn_load_file.setEnabled(True)
        self.btn_import_yt.setEnabled(True)
        self.progress_bar.setValue(0)
        self.lbl_dsp_status.setText("Audio analysis failed.")
        # Clear the previous run's metrics. Leaving them on screen made a failed
        # re-analysis look like it had produced a result: the stats card and the
        # Russell plane still showed the earlier track's numbers.
        self.stats_label.setText(
            "<b>Analysis failed.</b><br>"
            "No metrics are available for this file. Fix the input and analyse again."
        )
        if hasattr(self, "russell_plane"):
            self.russell_plane.set_coordinates(0.0, 0.0, "Idle")
        QMessageBox.critical(self, "DSP Analysis Error", f"Failed to analyze audio:\n{err_msg}")
