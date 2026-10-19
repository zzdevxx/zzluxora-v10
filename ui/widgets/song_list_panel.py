"""
song_list_panel.py | Unified Song Panel and Add Song Dialog

Provides a standardized, professional left panel for song playlists in Analyze,
Result, and Perform tabs, along with a single unified Add Song dialog (Local File & YouTube).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from ui.qt_compat import (
    HAS_QT, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDialog, QTabWidget, QLineEdit,
    QProgressBar, QFileDialog, QMessageBox, Qt, Signal, QThread,
)
from ui.styles import Theme, CONSOLE_QSS
from core.song_library import SongLibrary
from core.audio_loader import AudioLoader


class YouTubeDownloadWorker(QThread if HAS_QT else object):
    """Background worker for non-blocking YouTube download and conversion."""
    progress_updated = Signal(int, str)
    download_finished = Signal(str)
    download_failed = Signal(str)

    def __init__(self, url: str, output_dir: str):
        if not HAS_QT:
            return
        super().__init__()
        self.url = url
        self.output_dir = output_dir

    def run(self) -> None:
        from core import youtube_importer as yt

        def progress_cb(percent: int, message: str) -> None:
            self.progress_updated.emit(percent, message)

        try:
            wav_path = yt.download_and_convert(self.url, self.output_dir, progress=progress_cb)
            self.download_finished.emit(wav_path)
        except yt.YouTubeImportError as err:
            self.download_failed.emit(str(err))
        except Exception as exc:
            self.download_failed.emit(f"Unexpected error: {exc}")


class AddSongDialog(QDialog if HAS_QT else object):
    """Single unified dialog for adding songs via Local File or YouTube."""
    song_added = Signal(str)  # Emits file path of added audio

    def __init__(self, parent: QWidget | None = None):
        if not HAS_QT:
            return
        super().__init__(parent)
        self.setWindowTitle("Add Song to Library")
        self.resize(500, 320)
        self.setStyleSheet(CONSOLE_QSS)
        self._worker: Optional[YouTubeDownloadWorker] = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        self.tab_widget = QTabWidget(self)

        # Tab 1: Local File
        tab_local = QWidget()
        loc_layout = QVBoxLayout(tab_local)
        loc_layout.setContentsMargins(12, 12, 12, 12)
        loc_layout.setSpacing(10)

        lbl_desc = QLabel("Select an audio file from local disk (.wav, .mp3, .flac, .ogg):")
        lbl_desc.setStyleSheet(f"color: {Theme.TEXT_SECONDARY}; font-size: 11px;")
        loc_layout.addWidget(lbl_desc)

        file_row = QHBoxLayout()
        self.txt_local_path = QLineEdit()
        self.txt_local_path.setReadOnly(True)
        self.txt_local_path.setPlaceholderText("Choose audio file...")
        self.txt_local_path.setStyleSheet(
            f"background-color: {Theme.SURFACE_INPUT}; border: 1px solid {Theme.BORDER_STRONG}; color: {Theme.TEXT_PRIMARY};"
        )
        file_row.addWidget(self.txt_local_path, 1)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._on_browse_local)
        file_row.addWidget(btn_browse)
        loc_layout.addLayout(file_row)

        self.lbl_file_info = QLabel("")
        self.lbl_file_info.setStyleSheet(f"color: {Theme.ACCENT_CYAN}; font-size: 11px;")
        loc_layout.addWidget(self.lbl_file_info)

        loc_layout.addStretch()

        self.btn_add_local = QPushButton("Add Local File")
        self.btn_add_local.setStyleSheet(
            f"background-color: {Theme.STATUS_SUCCESS_BG}; color: {Theme.COLOR_SUCCESS}; font-weight: bold; padding: 6px 14px;"
        )
        self.btn_add_local.setEnabled(False)
        self.btn_add_local.clicked.connect(self._on_add_local_clicked)
        loc_layout.addWidget(self.btn_add_local, alignment=Qt.AlignRight)

        self.tab_widget.addTab(tab_local, "Local File")

        # Tab 2: YouTube Import
        tab_yt = QWidget()
        yt_layout = QVBoxLayout(tab_yt)
        yt_layout.setContentsMargins(12, 12, 12, 12)
        yt_layout.setSpacing(10)

        lbl_yt_desc = QLabel("Enter YouTube video or audio link to download and convert to PCM 22,050 Hz:")
        lbl_yt_desc.setStyleSheet(f"color: {Theme.TEXT_SECONDARY}; font-size: 11px;")
        yt_layout.addWidget(lbl_yt_desc)

        self.txt_yt_url = QLineEdit()
        self.txt_yt_url.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.txt_yt_url.setStyleSheet(
            f"background-color: {Theme.SURFACE_INPUT}; border: 1px solid {Theme.BORDER_STRONG}; color: {Theme.TEXT_PRIMARY};"
        )
        yt_layout.addWidget(self.txt_yt_url)

        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setFixedHeight(8)
        self.prog_bar.setTextVisible(False)
        self.prog_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Theme.SURFACE_INPUT};
                border: 1px solid {Theme.BORDER_SUBTLE};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {Theme.COLOR_SUCCESS};
                border-radius: 3px;
            }}
        """)
        yt_layout.addWidget(self.prog_bar)

        self.lbl_yt_status = QLabel("Ready to download.")
        self.lbl_yt_status.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px;")
        yt_layout.addWidget(self.lbl_yt_status)

        yt_layout.addStretch()

        self.btn_dl_yt = QPushButton("Download & Add")
        self.btn_dl_yt.setStyleSheet(
            f"background-color: {Theme.STATUS_SUCCESS_BG}; color: {Theme.COLOR_SUCCESS}; font-weight: bold; padding: 6px 14px;"
        )
        self.btn_dl_yt.clicked.connect(self._on_start_yt_download)
        yt_layout.addWidget(self.btn_dl_yt, alignment=Qt.AlignRight)

        self.tab_widget.addTab(tab_yt, "YouTube Import")
        layout.addWidget(self.tab_widget, 1)

        # Bottom Close button
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

    def _on_browse_local(self) -> None:
        init_dir = str(Path("data/audio").resolve()) if Path("data/audio").exists() else ""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            init_dir,
            "Audio Files (*.wav *.mp3 *.flac *.ogg);;All Files (*.*)",
        )
        if not path:
            return
        self.txt_local_path.setText(path)
        try:
            loader = AudioLoader()
            sig, sr = loader.load_audio(path)
            duration = len(sig) / float(sr) if sr else 0.0
            self.lbl_file_info.setText(f"Loaded: {duration:.1f}s | Sample Rate: {sr} Hz | Mono PCM")
            self.btn_add_local.setEnabled(True)
        except Exception as exc:
            self.lbl_file_info.setText(f"Warning: {exc}")
            self.btn_add_local.setEnabled(True)

    def _on_add_local_clicked(self) -> None:
        path = self.txt_local_path.text().strip()
        if path and Path(path).exists():
            self.song_added.emit(path)
            self.accept()

    def _on_start_yt_download(self) -> None:
        url = self.txt_yt_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid YouTube URL.")
            return

        out_dir = Path("data/audio").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        self.btn_dl_yt.setEnabled(False)
        self.prog_bar.setValue(5)
        self.lbl_yt_status.setText("Connecting to YouTube...")

        self._worker = YouTubeDownloadWorker(url, str(out_dir))
        self._worker.progress_updated.connect(self._on_yt_progress)
        self._worker.download_finished.connect(self._on_yt_success)
        self._worker.download_failed.connect(self._on_yt_failed)
        self._worker.start()

    def _on_yt_progress(self, percent: int, msg: str) -> None:
        self.prog_bar.setValue(percent)
        self.lbl_yt_status.setText(msg)

    def _on_yt_success(self, wav_path: str) -> None:
        self.prog_bar.setValue(100)
        self.lbl_yt_status.setText("Download & conversion complete!")
        self.btn_dl_yt.setEnabled(True)
        self.song_added.emit(wav_path)
        self.accept()

    def _on_yt_failed(self, error: str) -> None:
        self.prog_bar.setValue(0)
        self.lbl_yt_status.setText(f"Error: {error}")
        self.btn_dl_yt.setEnabled(True)
        QMessageBox.critical(self, "Import Failed", f"Failed to import YouTube audio:\n{error}")


class DraggableSongListWidget(QListWidget if HAS_QT else object):
    """QListWidget with internal drag-and-drop reorder signal."""
    order_dropped = Signal(int, int)  # (from_row, to_row)

    def dropEvent(self, event):
        src_row = self.currentRow()
        super().dropEvent(event)
        dest_row = self.currentRow()
        if src_row != dest_row and src_row >= 0 and dest_row >= 0:
            self.order_dropped.emit(src_row, dest_row)


class SongListPanel(QWidget if HAS_QT else object):
    """
    Standardized left panel for managing songs across Analyze, Result, and Perform tabs.
    Features 4 icon buttons ([+], [-], [▲], [▼]), single & multi-selection, and drag reordering.
    """
    PANEL_WIDTH = 210
    song_selected = Signal(int)  # Emits selected song index
    add_requested = Signal()

    def __init__(self, song_library: SongLibrary, parent: QWidget | None = None):
        if not HAS_QT:
            return
        super().__init__(parent)
        self.setFixedWidth(self.PANEL_WIDTH)
        self.song_library = song_library
        self._init_ui()
        self.song_library.on_changed(self.refresh_list)
        self.song_library.on_selection_changed(self._on_library_selection_changed)
        self.refresh_list()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header Bar
        bar = QHBoxLayout()
        bar.setContentsMargins(6, 0, 0, 0)
        bar.setSpacing(4)

        lbl = QLabel("SONGS")
        lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 800; letter-spacing: 0.6px; color: {Theme.TEXT_SECONDARY};"
        )
        bar.addWidget(lbl)
        bar.addStretch()

        self.btn_add = QPushButton("+")
        self.btn_add.setFixedSize(24, 22)
        self.btn_add.setToolTip("Add song (Local file or YouTube)")
        self.btn_add.clicked.connect(self._on_add_clicked)
        bar.addWidget(self.btn_add)

        self.btn_remove = QPushButton("-")
        self.btn_remove.setFixedSize(24, 22)
        self.btn_remove.setToolTip("Remove selected song(s)")
        self.btn_remove.setEnabled(False)
        self.btn_remove.clicked.connect(self._on_remove_clicked)
        bar.addWidget(self.btn_remove)

        self.btn_up = QPushButton("▲")
        self.btn_up.setFixedSize(24, 22)
        self.btn_up.setToolTip("Move selected song up in order")
        self.btn_up.setEnabled(False)
        self.btn_up.clicked.connect(lambda: self._on_move_clicked(-1))
        bar.addWidget(self.btn_up)

        self.btn_down = QPushButton("▼")
        self.btn_down.setFixedSize(24, 22)
        self.btn_down.setToolTip("Move selected song down in order")
        self.btn_down.setEnabled(False)
        self.btn_down.clicked.connect(lambda: self._on_move_clicked(1))
        bar.addWidget(self.btn_down)

        layout.addLayout(bar)

        # Song List Widget
        self.list_widget = DraggableSongListWidget(self)
        self.list_widget.setDragEnabled(True)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.order_dropped.connect(self.song_library.reorder)

        drag_only = getattr(QListWidget, "InternalMove", None)
        if drag_only is None:
            drag_mode = getattr(QListWidget, "DragDropMode", None)
            drag_only = getattr(drag_mode, "InternalMove", 4)
        self.list_widget.setDragDropMode(drag_only)

        sel_mode = getattr(QListWidget, "ExtendedSelection", None)
        if sel_mode is None:
            sel_enum = getattr(QListWidget, "SelectionMode", None)
            sel_mode = getattr(sel_enum, "ExtendedSelection", 3)
        self.list_widget.setSelectionMode(sel_mode)

        self.list_widget.setUniformItemSizes(True)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {Theme.SURFACE_INPUT};
                border: 1px solid {Theme.BORDER_SUBTLE};
                border-radius: 4px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 6px 8px;
                border-bottom: 1px solid {Theme.BORDER_SUBTLE};
                color: {Theme.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QListWidget::item:selected {{
                background-color: {Theme.BG_ELEVATED};
                color: {Theme.TEXT_PRIMARY};
            }}
        """)
        layout.addWidget(self.list_widget, 1)

        self.empty_label = QLabel("No songs in library.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; padding: 12px;")
        layout.addWidget(self.empty_label)

    def refresh_list(self) -> None:
        """Rebuilds the list items from the SongLibrary."""
        songs = self.song_library.songs
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        for idx, song in enumerate(songs, 1):
            summary = song.summary()
            text = f"[{idx}] {song.title}\n     {summary}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, idx - 1)
            self.list_widget.addItem(item)

        sel_idx = self.song_library.selected_index
        if 0 <= sel_idx < self.list_widget.count():
            self.list_widget.setCurrentRow(sel_idx)

        self.list_widget.blockSignals(False)

        has_songs = bool(songs)
        self.list_widget.setVisible(has_songs)
        self.empty_label.setVisible(not has_songs)
        self._update_button_states()

    def _update_button_states(self) -> None:
        selected_rows = [self.list_widget.row(item) for item in self.list_widget.selectedItems()]
        has_sel = bool(selected_rows)
        self.btn_remove.setEnabled(has_sel)
        row = self.list_widget.currentRow()
        count = self.list_widget.count()
        self.btn_up.setEnabled(has_sel and row > 0)
        self.btn_down.setEnabled(has_sel and 0 <= row < count - 1)

    def _on_selection_changed(self) -> None:
        self._update_button_states()
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.song_library):
            self.song_library.select(row)
            self.song_selected.emit(row)

    def _on_library_selection_changed(self, index: int) -> None:
        if 0 <= index < self.list_widget.count() and self.list_widget.currentRow() != index:
            self.list_widget.blockSignals(True)
            self.list_widget.setCurrentRow(index)
            self.list_widget.blockSignals(False)
        self._update_button_states()

    def _on_add_clicked(self) -> None:
        dlg = AddSongDialog(self)
        dlg.song_added.connect(lambda path: self.song_library.add_path(path, select=True))
        dlg.exec()

    def _on_remove_clicked(self) -> None:
        selected_rows = sorted([self.list_widget.row(item) for item in self.list_widget.selectedItems()])
        if not selected_rows:
            return

        names = [self.song_library.songs[r].title for r in selected_rows if r < len(self.song_library.songs)]
        daftar = "\n".join(f"  - {n}" for n in names)
        jawab = QMessageBox.question(
            self,
            "Remove Songs",
            f"Remove {len(selected_rows)} song(s) from library?\n\n{daftar}\n\n"
            f"(This will also remove their scheduled section cues in Perform and Page).",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if jawab == QMessageBox.Yes:
            self.song_library.remove(selected_rows)

    def _on_move_clicked(self, delta: int) -> None:
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.song_library):
            new_idx = self.song_library.move(row, delta)
            self.list_widget.setCurrentRow(new_idx)
