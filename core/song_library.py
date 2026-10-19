"""Satu daftar lagu untuk Analyze, Result, dan Perform.

Sebelumnya Analyze memiliki daftar berkas sesinya sendiri dan Perform memiliki
daftar lagu pertunjukannya sendiri. Keduanya tidak saling tahu: menambahkan lagu
di Analyze tidak muncul di Perform, dan mengubah urutan di Perform tidak terlihat
di Analyze. Operator yang menyiapkan ibadah harus memasukkan bahan yang sama dua
kali, dan mudah berakhir dengan dua urutan yang berbeda.

SongLibrary adalah sumber tunggalnya. Setiap tab membaca daftar yang sama dan
mendengar sinyal yang sama, sehingga menambah, menghapus, memilih, dan mengubah
urutan terjadi sekali dan langsung terlihat di ketiga tab.

Objek lagu menyimpan apa yang sudah diketahui dan apa yang belum. Berkas audio
diketahui begitu dimuat; hasil analisis baru terisi setelah Analyze dijalankan.
Perbedaan itu penting untuk kejujuran tampilan: lagu yang belum dianalisis tidak
boleh menampilkan BPM atau kuadran seolah sudah diukur.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional


@dataclass
class SongEntry:
    """One song, its file when it has one, and whatever analysis it has produced.

    A song can enter the library two ways, and the difference matters. Loading
    an audio file gives a path and no analysis yet. Exporting a finished result
    from the Result tab gives analysis and may have no file at all - Perform
    schedules cues from analysis, so a song analysed on another machine is
    perfectly usable without the audio being present. Keeping both optional
    avoids inventing a fake path to satisfy the dataclass.
    """

    path: str = ""
    analysis: Optional[dict[str, Any]] = None

    @property
    def name(self) -> str:
        if self.path:
            return Path(self.path).name
        return self.title

    @property
    def title(self) -> str:
        """Display title: the analysed song title when known, else the filename."""
        if isinstance(self.analysis, dict):
            value = self.analysis.get("title")
            if isinstance(value, str) and value.strip():
                return value.strip()
        if self.path:
            return Path(self.path).stem
        return "Untitled"

    @property
    def is_analyzed(self) -> bool:
        return isinstance(self.analysis, dict) and bool(self.analysis)

    def summary(self) -> str:
        """One line for the list. Never invents numbers for an unanalysed song."""
        if not self.is_analyzed:
            return "not analysed"
        analysis = self.analysis or {}
        parts: list[str] = []
        quadrant = analysis.get("quadrant")
        if isinstance(quadrant, str) and quadrant:
            parts.append(quadrant)
        bpm = analysis.get("bpm")
        if isinstance(bpm, (int, float)) and bpm > 0:
            parts.append(f"{bpm:.0f} BPM")
        return ", ".join(parts) if parts else "analysed"


class SongLibrary:
    """The single ordered list of songs shared by every tab.

    Listeners are plain callables rather than Qt signals. This object is shared
    state owned by the main window, not a widget, and the repository defines Qt
    signals only on QWidget subclasses; keeping it free of Qt also lets the
    order and duplicate rules be tested without starting a GUI.
    """

    def __init__(self) -> None:
        self._songs: list[SongEntry] = []
        self._selected: int = -1
        self._on_changed: list[Callable[[], None]] = []
        self._on_selection: list[Callable[[int], None]] = []
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []

    # -- undo / redo -----------------------------------------------------

    def _snapshot(self) -> dict:
        return {
            "songs": [
                SongEntry(path=s.path, analysis=dict(s.analysis) if isinstance(s.analysis, dict) else None)
                for s in self._songs
            ],
            "selected": self._selected,
        }

    def _restore_snapshot(self, snap: dict) -> None:
        self._songs = [
            SongEntry(path=s.path, analysis=dict(s.analysis) if isinstance(s.analysis, dict) else None)
            for s in snap.get("songs", [])
        ]
        self._selected = snap.get("selected", -1)
        self._broadcast_changed()
        self._broadcast_selection()

    def record_undo(self) -> None:
        """Save current state to undo stack before modifying song list."""
        self._undo_stack.append(self._snapshot())
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def undo(self) -> bool:
        if not self.can_undo():
            return False
        self._redo_stack.append(self._snapshot())
        snap = self._undo_stack.pop()
        self._restore_snapshot(snap)
        return True

    def redo(self) -> bool:
        if not self.can_redo():
            return False
        self._undo_stack.append(self._snapshot())
        snap = self._redo_stack.pop()
        self._restore_snapshot(snap)
        return True

    # -- listeners -------------------------------------------------------

    def on_changed(self, callback: Callable[[], None]) -> None:
        """Register a callback fired whenever songs are added, removed or moved."""
        self._on_changed.append(callback)

    def on_selection_changed(self, callback: Callable[[int], None]) -> None:
        """Register a callback fired when the selected index changes."""
        self._on_selection.append(callback)

    def _broadcast_changed(self) -> None:
        for callback in list(self._on_changed):
            callback()

    def _broadcast_selection(self) -> None:
        for callback in list(self._on_selection):
            callback(self._selected)

    # -- reading ---------------------------------------------------------

    @property
    def songs(self) -> list[SongEntry]:
        return list(self._songs)

    def __len__(self) -> int:
        return len(self._songs)

    @property
    def selected_index(self) -> int:
        return self._selected

    def selected(self) -> Optional[SongEntry]:
        if 0 <= self._selected < len(self._songs):
            return self._songs[self._selected]
        return None

    def index_of_path(self, path: str) -> int:
        """Index of a song by file path, or -1 when it is not in the list.

        Adding the same file twice would analyse it twice and show two identical
        rows, so callers use this to detect a duplicate before appending.
        """
        target = str(Path(path))
        for index, song in enumerate(self._songs):
            if str(Path(song.path)) == target:
                return index
        return -1

    # -- writing ---------------------------------------------------------

    def add_path(self, path: str, select: bool = True) -> int:
        """Append a song file. Returns its index, or the existing one if present."""
        existing = self.index_of_path(path)
        if existing >= 0:
            if select:
                self.select(existing)
            return existing
        self.record_undo()
        self._songs.append(SongEntry(path=str(path)))
        index = len(self._songs) - 1
        if select:
            self._selected = index
        self._broadcast_changed()
        self._broadcast_selection()
        return index

    @staticmethod
    def _matches_title(song: SongEntry, wanted: str) -> bool:
        """True when a song is the same track as `wanted`, however it arrived.

        A file-loaded entry has no analysis yet, so its title falls back to the
        filename stem, while an exported entry carries the analysed title. Both
        spellings are compared, case-insensitively, so "Bapa Yang Kekal" and
        "Bapa_Yang_Kekal.wav" are recognised as one song.
        """
        candidates = {song.title.strip().lower()}
        if song.path:
            candidates.add(Path(song.path).stem.strip().lower())
        if isinstance(song.analysis, dict):
            analysed = song.analysis.get("title")
            if isinstance(analysed, str) and analysed.strip():
                candidates.add(analysed.strip().lower())
        want = wanted.lower()
        # Compare with separators flattened, so underscores and spaces match.
        def normalise(text: str) -> str:
            return " ".join(text.replace("_", " ").replace("-", " ").split())
        return any(normalise(c) == normalise(want) for c in candidates)

    def add_analysis(self, analysis: dict[str, Any], select: bool = True) -> int:
        """Append a song that arrives as finished analysis rather than a file.

        The Result tab exports this way: it has a result to schedule and the
        audio may not be on this machine at all. An entry already carrying the
        same file path or title is reused so re-exporting a song does not duplicate it.
        """
        target_path = analysis.get("file_path") if isinstance(analysis, dict) else None
        target_idx = -1

        if isinstance(target_path, str) and target_path.strip():
            target_idx = self.index_of_path(target_path.strip())

        title = analysis.get("title") if isinstance(analysis, dict) else None
        if target_idx < 0 and isinstance(title, str) and title.strip():
            wanted = title.strip()
            for index, song in enumerate(self._songs):
                if self._matches_title(song, wanted):
                    target_idx = index
                    break

        if target_idx >= 0:
            old_cues = self._songs[target_idx].analysis.get("custom_cues") if isinstance(self._songs[target_idx].analysis, dict) else None
            new_analysis = dict(analysis)
            if old_cues and "custom_cues" not in new_analysis:
                new_analysis["custom_cues"] = [dict(c) for c in old_cues if isinstance(c, dict)]
            self._songs[target_idx].analysis = new_analysis
            if select:
                self._selected = target_idx
            self._broadcast_changed()
            self._broadcast_selection()
            return target_idx

        self._songs.append(SongEntry(path=str(target_path) if target_path else "", analysis=analysis))
        index = len(self._songs) - 1
        if select:
            self._selected = index
        self._broadcast_changed()
        self._broadcast_selection()
        return index

    def set_analysis(self, index: int, analysis: dict[str, Any]) -> None:
        if not 0 <= index < len(self._songs):
            return
        old_cues = self._songs[index].analysis.get("custom_cues") if isinstance(self._songs[index].analysis, dict) else None
        new_analysis = dict(analysis)
        if old_cues and "custom_cues" not in new_analysis:
            new_analysis["custom_cues"] = [dict(c) for c in old_cues if isinstance(c, dict)]
        self._songs[index].analysis = new_analysis
        self._broadcast_changed()

    def set_analysis_by_path(self, path: str, analysis: dict[str, Any]) -> None:
        index = self.index_of_path(path)
        if index >= 0:
            self.set_analysis(index, analysis)

    def remove(self, indices: list[int]) -> None:
        """Remove songs by index. Invalid indices are ignored."""
        valid = sorted({i for i in indices if 0 <= i < len(self._songs)}, reverse=True)
        if not valid:
            return
        self.record_undo()
        removed_below = sum(1 for i in valid if i < self._selected)
        selection_removed = self._selected in valid

        for index in valid:
            del self._songs[index]

        if selection_removed or self._selected < 0:
            self._selected = min(self._selected, len(self._songs) - 1)
        else:
            self._selected = max(0, min(self._selected - removed_below, len(self._songs) - 1))

        self._broadcast_changed()
        self._broadcast_selection()

    def move(self, index: int, delta: int) -> int:
        target = index + delta
        if not (0 <= index < len(self._songs)):
            return index
        if not (0 <= target < len(self._songs)):
            return index

        self.record_undo()
        selected_song = self._songs[self._selected] if 0 <= self._selected < len(self._songs) else None

        self._songs[index], self._songs[target] = self._songs[target], self._songs[index]

        if selected_song is not None:
            self._selected = next(
                (i for i, song in enumerate(self._songs) if song is selected_song),
                self._selected,
            )

        self._broadcast_changed()
        self._broadcast_selection()
        return target

    def reorder(self, from_index: int, to_index: int) -> None:
        """Arbitrary position reorder for drag-and-drop playlist rearrangements."""
        if not (0 <= from_index < len(self._songs) and 0 <= to_index < len(self._songs)):
            return
        self.record_undo()
        selected_song = self._songs[self._selected] if 0 <= self._selected < len(self._songs) else None
        item = self._songs.pop(from_index)
        self._songs.insert(to_index, item)
        if selected_song is not None:
            self._selected = next(
                (i for i, song in enumerate(self._songs) if song is selected_song),
                self._selected,
            )
        self._broadcast_changed()
        self._broadcast_selection()

    def select(self, index: int) -> None:
        if index == self._selected:
            return
        self._selected = index if 0 <= index < len(self._songs) else -1
        self._broadcast_selection()

    def clear(self) -> None:
        if self._songs:
            self.record_undo()
        self._songs.clear()
        self._selected = -1
        self._broadcast_changed()
        self._broadcast_selection()
