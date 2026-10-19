#!/usr/bin/env python3
"""
test_global_undo_redo.py - Verifikasi Otomatis Smart Context-Aware Undo/Redo Engine (QLC+ & grandMA Style).
"""

import sys
from pathlib import Path
from unittest.mock import patch

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import _autodialog_guard  # noqa: F401
from ui.qt_compat import QApplication, QDialog
from ui.main_window import MainWindow


def run_undo_redo_tests():
    app = QApplication.instance() or QApplication(["undo_test", "-platform", "offscreen"])
    win = MainWindow()
    results = []

    def log(tc_id, name, status, detail):
        results.append((tc_id, name, status, detail))
        mark = "✅ PASS" if status == "PASS" else "❌ FAIL"
        print(f"[{mark}] {tc_id}: {name}")
        print(f"       Detail: {detail}\n")

    print("\n" + "=" * 90)
    print("🔁 PENGUJIAN SMART CONTEXT-AWARE UNDO / REDO ENGINE ZZLUXORA v10")
    print("=" * 90 + "\n")

    # --------------------------------------------------------------------------
    # TC-UNDO-01: Undo/Redo Patch di Tab Address
    # --------------------------------------------------------------------------
    win._switch_workspace(0)  # Address Tab
    win.tab_address._on_patch_alien_gia()
    has_patches_before = len(win.tab_address.get_patched_fixtures()) == 4

    # Tekan Global Undo
    win._on_global_undo()
    has_patches_after_undo = len(win.tab_address.get_patched_fixtures()) == 0

    # Tekan Global Redo
    win._on_global_redo()
    has_patches_after_redo = len(win.tab_address.get_patched_fixtures()) == 4

    if has_patches_before and has_patches_after_undo and has_patches_after_redo:
        log("TC-UNDO-01", "Undo/Redo Patch di Tab Address", "PASS",
            "Saat di Tab Address: Ctrl+Z membatalkan patch (4 -> 0 fixture); Ctrl+Y memulihkan patch (0 -> 4 fixture).")
    else:
        log("TC-UNDO-01", "Undo/Redo Patch di Tab Address", "FAIL",
            f"before={has_patches_before}, undo={has_patches_after_undo}, redo={has_patches_after_redo}")

    # --------------------------------------------------------------------------
    # TC-UNDO-02: Undo/Redo Penambahan Custom Cue di Tab Perform
    # --------------------------------------------------------------------------
    win._switch_workspace(3)  # Perform Tab
    win.song_library.add_analysis({
        "title": "Worship Track", "bpm": 70, "quadrant": "Q4_PEACE_INTIMACY",
        "palette": {"R": 30, "G": 20, "B": 180, "W": 20}
    })
    win.tab_perform._on_song_selected(0)
    initial_cues_count = len(win.tab_perform.current_song_cues)  # 6 cues

    # Tambah cue kustom via [+]
    custom_cue = {
        "section": "Altar Call", "mood": "Prayer", "fade_in": 3.0, "fade_out": 2.0,
        "dimmer": 200, "color": {"R": 255, "G": 200, "B": 50, "W": 80}
    }
    with patch("ui.panels.perform_tab.EditCueDialog") as mock_dlg:
        inst = mock_dlg.return_value
        inst.cue = custom_cue
        inst.exec.return_value = 1  # Accepted
        win.tab_perform._on_add_cue_clicked()

    added_cues_count = len(win.tab_perform.current_song_cues)  # 7 cues

    # Tekan Global Undo di Tab Perform
    win._on_global_undo()
    undo_cues_count = len(win.tab_perform.current_song_cues)  # Kembali ke 6 cues

    # Tekan Global Redo di Tab Perform
    win._on_global_redo()
    redo_cues_count = len(win.tab_perform.current_song_cues)  # Kembali ke 7 cues

    if added_cues_count == 7 and undo_cues_count == 6 and redo_cues_count == 7:
        log("TC-UNDO-02", "Undo/Redo Penambahan Custom Cue di Tab Perform", "PASS",
            f"Saat di Tab Perform: Ctrl+Z membatalkan penambahan cue (7 -> 6 cues); Ctrl+Y memulihkan cue 'Altar Call' (6 -> 7 cues).")
    else:
        log("TC-UNDO-02", "Undo/Redo Penambahan Custom Cue di Tab Perform", "FAIL",
            f"added={added_cues_count}, undo={undo_cues_count}, redo={redo_cues_count}")

    # --------------------------------------------------------------------------
    # TC-UNDO-03: Undo/Redo Edit Parameter Cue di Tab Perform
    # --------------------------------------------------------------------------
    win.tab_perform.cue_table.setCurrentCell(0, 0)
    orig_fade = win.tab_perform.current_song_cues[0]["fade_in"]

    # Edit parameter cue via [✎]
    edited_cue = dict(win.tab_perform.current_song_cues[0])
    edited_cue["fade_in"] = 6.5
    with patch("ui.panels.perform_tab.EditCueDialog") as mock_dlg:
        inst = mock_dlg.return_value
        inst.cue = edited_cue
        inst.exec.return_value = 1
        win.tab_perform._on_edit_cue_clicked()

    new_fade = win.tab_perform.current_song_cues[0]["fade_in"]

    # Undo edit
    win._on_global_undo()
    restored_fade = win.tab_perform.current_song_cues[0]["fade_in"]

    # Redo edit
    win._on_global_redo()
    redo_fade = win.tab_perform.current_song_cues[0]["fade_in"]

    if new_fade == 6.5 and restored_fade == orig_fade and redo_fade == 6.5:
        log("TC-UNDO-03", "Undo/Redo Edit Parameter Cue di Tab Perform", "PASS",
            f"Edit Fade In (dari {orig_fade}s ke 6.5s) berhasil dibatalkan oleh Ctrl+Z kembali ke {restored_fade}s, dan dipulihkan kembali oleh Ctrl+Y ke {redo_fade}s.")
    else:
        log("TC-UNDO-03", "Undo/Redo Edit Parameter Cue di Tab Perform", "FAIL",
            f"new={new_fade}, restored={restored_fade}, redo={redo_fade}")

    # --------------------------------------------------------------------------
    # TC-UNDO-04: Undo/Redo Daftar Lagu (Song Library Playlist)
    # --------------------------------------------------------------------------
    win._switch_workspace(1)  # Analyze Tab (fokus di Song Library)
    total_songs_before = len(win.song_library)
    win.song_library.add_path("test_track_x.wav")
    songs_after_add = len(win.song_library)

    # Undo penambahan lagu
    win._on_global_undo()
    songs_after_undo = len(win.song_library)

    # Redo penambahan lagu
    win._on_global_redo()
    songs_after_redo = len(win.song_library)

    if songs_after_add == total_songs_before + 1 and songs_after_undo == total_songs_before and songs_after_redo == songs_after_add:
        log("TC-UNDO-04", "Undo/Redo Daftar Lagu (Song Library Playlist)", "PASS",
            f"Penambahan/penghapusan lagu pada Song Library berhasil di-undo (berkurang) dan di-redo (pulih kembali).")
    else:
        log("TC-UNDO-04", "Undo/Redo Daftar Lagu (Song Library Playlist)", "FAIL",
            f"before={total_songs_before}, after={songs_after_add}, undo={songs_after_undo}, redo={songs_after_redo}")

    # --------------------------------------------------------------------------
    # TC-UNDO-05: Perlindungan Aman pada Tab Live Surface (Mixer & Page)
    # --------------------------------------------------------------------------
    # Set nilai fader channel 1 = 200
    win.tab_mixer.set_channel_value(1, 200)
    win.dmx_buffer[0] = 200

    # Buka Tab Mixer (Live Surface)
    win._switch_workspace(5)  # Mixer Tab
    # Tekan Ctrl+Z saat di Mixer
    win._on_global_undo()
    dmx_after_mixer_undo = win.dmx_buffer[0]
    fader_after_mixer_undo = win.tab_mixer.faders[1].value

    # Buka Tab Page (Live Playback Pad)
    win._switch_workspace(4)  # Page Tab
    # Tekan Ctrl+Z saat di Page
    win._on_global_undo()
    dmx_after_page_undo = win.dmx_buffer[0]

    # Buffer DMX dan fader tidak boleh berubah sama sekali (live show dilindungi)
    surface_protected = (dmx_after_mixer_undo == 200 and fader_after_mixer_undo == 200 and dmx_after_page_undo == 200)

    if surface_protected:
        log("TC-UNDO-05", "Perlindungan Aman pada Tab Live Surface (Mixer & Page)", "PASS",
            "Saat di Tab Mixer atau Tab Page, Ctrl+Z diabaikan secara aman: nilai DMX panggung dan posisi fader terlindungi 100% dari lonjakan liar.")
    else:
        log("TC-UNDO-05", "Perlindungan Aman pada Tab Live Surface (Mixer & Page)", "FAIL",
            f"dmx_after_mixer={dmx_after_mixer_undo}, fader={fader_after_mixer_undo}")

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------
    total = len(results)
    passed = sum(1 for r in results if r[2] == "PASS")
    failed = total - passed
    print("=" * 90)
    print(f"📊 REKAPITULASI PENGUJIAN UNDO/REDO: {passed}/{total} SKENARIO LULUS ({passed/total*100:.1f}%)")
    print("=" * 90)

    win.close()
    return failed == 0


if __name__ == "__main__":
    success = run_undo_redo_tests()
    sys.exit(0 if success else 1)
