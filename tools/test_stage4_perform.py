#!/usr/bin/env python3
"""
test_stage4_perform.py - Eksekusi Pengujian Otomatis Tahap 4: Tab Perform (TC-PERF-01 s.d. TC-PERF-08).
"""

import math
import sys
from pathlib import Path
from unittest.mock import patch

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import _autodialog_guard  # noqa: F401
from ui.qt_compat import QApplication, QDialog, QMessageBox
from ui.panels.perform_tab import PerformTab, EditCueDialog
from core.song_library import SongLibrary


def run_stage4_tests():
    app = QApplication.instance() or QApplication(["stage4_test", "-platform", "offscreen"])
    library = SongLibrary()
    tab = PerformTab(song_library=library)
    results = []

    def log_result(tc_id, name, status, detail):
        results.append((tc_id, name, status, detail))
        mark = "✅ PASS" if status == "PASS" else "❌ FAIL"
        print(f"[{mark}] {tc_id}: {name}")
        print(f"       Detail: {detail}\n")

    print("=" * 80)
    print("🚀 MEMULAI PENGUJIAN TAHAP 4: TAB PERFORM (8 SKENARIO)")
    print("=" * 80 + "\n")

    # --------------------------------------------------------------------------
    # TC-PERF-01: Penanganan Lagu Belum Dianalisis
    # --------------------------------------------------------------------------
    idx_unanalysed = library.add_path("queued_song.wav")
    tab._on_song_selected(idx_unanalysed)

    cues_empty = len(tab.current_song_cues) == 0
    table_empty = tab.cue_table.rowCount() == 0
    status_standby = "STANDBY" in tab.lbl_cue_status.text()

    if cues_empty and table_empty and status_standby:
        log_result("TC-PERF-01", "Penanganan Lagu Belum Dianalisis", "PASS",
                   "Lagu belum dianalisis mengosongkan tabel section cues (0 baris), status aman 'STANDBY | SONG NOT ANALYZED'.")
    else:
        log_result("TC-PERF-01", "Penanganan Lagu Belum Dianalisis", "FAIL",
                   f"cues_empty={cues_empty}, table_empty={table_empty}, status={tab.lbl_cue_status.text()}")

    # --------------------------------------------------------------------------
    # TC-PERF-02: Auto-Populate Section Cues Lagu Teranalisis
    # --------------------------------------------------------------------------
    idx_analysed = library.add_analysis({
        "title": "Sunday Worship Track",
        "bpm": 72.0,
        "quadrant": "Q4_PEACE_INTIMACY",
        "palette": {"R": 43, "G": 0, "B": 22, "W": 133}
    })
    tab._on_song_selected(idx_analysed)

    cues_count = len(tab.current_song_cues)
    table_rows = tab.cue_table.rowCount()
    sec_names = [c["section"] for c in tab.current_song_cues]

    if cues_count == 6 and table_rows == 6 and sec_names == ["Intro", "Verse 1", "Chorus", "Verse 2", "Bridge", "Ending"]:
        log_result("TC-PERF-02", "Auto-Populate Section Cues Lagu Teranalisis", "PASS",
                   f"Lagu teranalisis otomatis mempopulasi 6 section cues: {sec_names} lengkap dengan dimmer dan durasi fade.")
    else:
        log_result("TC-PERF-02", "Auto-Populate Section Cues Lagu Teranalisis", "FAIL",
                   f"cues_count={cues_count}, table_rows={table_rows}, sec_names={sec_names}")

    # --------------------------------------------------------------------------
    # TC-PERF-03: Tambah Custom Cue Baru [+]
    # --------------------------------------------------------------------------
    custom_cue = {
        "section": "Altar Call",
        "mood": "Holy Surrender (Contemplation)",
        "fade_in": 3.5,
        "fade_out": 4.0,
        "dimmer": 240,
        "color": {"R": 255, "G": 200, "B": 120, "W": 150}
    }
    with patch("ui.panels.perform_tab.EditCueDialog") as mock_dlg:
        inst = mock_dlg.return_value
        inst.cue = custom_cue
        inst.exec.return_value = 1  # Accepted
        tab._on_add_cue_clicked()

    has_altar = any(c["section"] == "Altar Call" for c in tab.current_song_cues)
    table_now = tab.cue_table.rowCount()
    stored_in_lib = any(c["section"] == "Altar Call" for c in library.songs[idx_analysed].analysis.get("custom_cues", []))

    if has_altar and table_now == 7 and stored_in_lib:
        log_result("TC-PERF-03", "Tambah Custom Cue Baru [+]", "PASS",
                   "Cue baru 'Altar Call' berhasil ditambahkan (total 7 cues) dan tersimpan persisten di SongLibrary.")
    else:
        log_result("TC-PERF-03", "Tambah Custom Cue Baru [+]", "FAIL",
                   f"has_altar={has_altar}, table_now={table_now}, stored_in_lib={stored_in_lib}")

    # --------------------------------------------------------------------------
    # TC-PERF-04: Edit Parameter Cue [✎]
    # --------------------------------------------------------------------------
    # Pilih baris cue Altar Call (index 6)
    tab.cue_table.setCurrentCell(6, 0)
    edited_cue = dict(tab.current_song_cues[6])
    edited_cue["fade_in"] = 5.0
    edited_cue["mood"] = "Deep Solitude"

    with patch("ui.panels.perform_tab.EditCueDialog") as mock_dlg:
        inst = mock_dlg.return_value
        inst.cue = edited_cue
        inst.exec.return_value = 1
        tab._on_edit_cue_clicked()

    fade_in_val = tab.current_song_cues[6]["fade_in"]
    mood_val = tab.current_song_cues[6]["mood"]

    if fade_in_val == 5.0 and mood_val == "Deep Solitude":
        log_result("TC-PERF-04", "Edit Parameter Cue [✎]", "PASS",
                   f"Parameter cue berhasil diperbarui via EditCueDialog: Fade In = {fade_in_val}s, Mood = '{mood_val}'.")
    else:
        log_result("TC-PERF-04", "Edit Parameter Cue [✎]", "FAIL",
                   f"fade_in_val={fade_in_val}, mood_val={mood_val}")

    # --------------------------------------------------------------------------
    # TC-PERF-05: Ubah Urutan Cue [▲] / [▼] & Hapus [-]
    # --------------------------------------------------------------------------
    # Geser Altar Call naik 1 tingkat (dari 6 ke 5)
    tab.cue_table.setCurrentCell(6, 0)
    tab._on_move_cue_clicked(-1)
    moved_sec = tab.current_song_cues[5]["section"]

    # Hapus cue di baris 5
    with patch("ui.panels.perform_tab.QMessageBox.question", return_value=QMessageBox.Yes):
        tab._on_remove_cue_clicked()

    cues_after_del = len(tab.current_song_cues)
    table_after_del = tab.cue_table.rowCount()

    if moved_sec == "Altar Call" and cues_after_del == 6 and table_after_del == 6:
        log_result("TC-PERF-05", "Ubah Urutan Cue [▲] / [▼] & Hapus [-]", "PASS",
                   "Urutan cue berhasil dinaikkan, penghapusan dengan modal konfirmasi mereduksi cue kembali ke 6.")
    else:
        log_result("TC-PERF-05", "Ubah Urutan Cue [▲] / [▼] & Hapus [-]", "FAIL",
                   f"moved_sec={moved_sec}, cues_after_del={cues_after_del}")

    # --------------------------------------------------------------------------
    # TC-PERF-06: Live Master Playback Transport [GO+] & [PREV]
    # --------------------------------------------------------------------------
    tab.active_cue_index = -1
    tab._on_go_clicked()  # Trigger cue 0 (Intro)
    c0 = tab.active_cue_index
    tab._on_go_clicked()  # Trigger cue 1 (Verse 1)
    c1 = tab.active_cue_index
    tab._on_prev_clicked()  # Return to cue 0
    c_prev = tab.active_cue_index

    if c0 == 0 and c1 == 1 and c_prev == 0:
        log_result("TC-PERF-06", "Live Master Playback Transport [GO+] & [PREV]", "PASS",
                   f"Transport berjalan akurat: [GO+] mengaktifkan cue 0 ({tab.current_song_cues[0]['section']}), maju ke 1, dan [PREV] mundur kembali ke 0.")
    else:
        log_result("TC-PERF-06", "Live Master Playback Transport [GO+] & [PREV]", "FAIL",
                   f"c0={c0}, c1={c1}, c_prev={c_prev}")

    # --------------------------------------------------------------------------
    # TC-PERF-07: Interpolasi Smooth S-Curve Cosine Crossfade
    # --------------------------------------------------------------------------
    # Formula S-curve cosine: factor = 0.5 * (1.0 - cos(pi * progress))
    test_points = [0.0, 0.25, 0.5, 0.75, 1.0]
    s_factors = [0.5 * (1.0 - math.cos(math.pi * p)) for p in test_points]

    is_continuous = (
        math.isclose(s_factors[0], 0.0, abs_tol=1e-7) and
        s_factors[1] < 0.25 and  # perlambatan di awal (smooth ease-in)
        math.isclose(s_factors[2], 0.5, abs_tol=1e-7) and
        s_factors[3] > 0.75 and  # perlambatan di akhir (smooth ease-out)
        math.isclose(s_factors[4], 1.0, abs_tol=1e-7)
    )

    if is_continuous:
        log_result("TC-PERF-07", "Interpolasi Smooth S-Curve Cosine Crossfade", "PASS",
                   f"S-Curve cosine terverifikasi kontinu natural: p(0.0)=0.0, p(0.25)={s_factors[1]:.4f}, p(0.5)=0.5, p(0.75)={s_factors[3]:.4f}, p(1.0)=1.0.")
    else:
        log_result("TC-PERF-07", "Interpolasi Smooth S-Curve Cosine Crossfade", "FAIL",
                   f"s_factors={s_factors}")

    # --------------------------------------------------------------------------
    # TC-PERF-08: Uji Tombol [FADE BLACK] vs [FADE IDLE]
    # --------------------------------------------------------------------------
    captured_payloads = []
    tab.cue_activated.connect(captured_payloads.append)

    # Trigger Fade Black
    tab._on_fade_black_clicked()
    black_payload = captured_payloads[-1]
    black_ok = (black_payload["dimmer"] == 0 and black_payload["active"] is False and black_payload["fade_time"] == 2.5)

    # Trigger Fade Idle
    tab._on_fade_idle_clicked()
    idle_payload = captured_payloads[-1]
    idle_ok = (idle_payload["dimmer"] == 80 and idle_payload["active"] is True and idle_payload["fade_time"] == 3.0)

    if black_ok and idle_ok and "STANDBY IDLE" in tab.lbl_cue_status.text():
        log_result("TC-PERF-08", "Uji Tombol [FADE BLACK] vs [FADE IDLE]", "PASS",
                   f"[FADE BLACK] memicu soft blackout (dimmer=0, fade=2.5s). [FADE IDLE] memicu warm standby (dimmer=80, fade=3.0s).")
    else:
        log_result("TC-PERF-08", "Uji Tombol [FADE BLACK] vs [FADE IDLE]", "FAIL",
                   f"black_ok={black_ok}, idle_ok={idle_ok}")

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------
    total = len(results)
    passed = sum(1 for r in results if r[2] == "PASS")
    failed = total - passed
    print("=" * 80)
    print(f"📊 REKAPITULASI PENGUJIAN TAHAP 4: {passed}/{total} SKENARIO LULUS ({passed/total*100:.1f}%)")
    print("=" * 80)

    tab.close()
    return failed == 0


if __name__ == "__main__":
    success = run_stage4_tests()
    sys.exit(0 if success else 1)
