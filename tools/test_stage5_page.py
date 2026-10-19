#!/usr/bin/env python3
"""
test_stage5_page.py - Eksekusi Pengujian Otomatis Tahap 5: Tab Page (TC-PAGE-01 s.d. TC-PAGE-04).
"""

import sys
from pathlib import Path

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import _autodialog_guard  # noqa: F401
from ui.qt_compat import QApplication
from ui.main_window import MainWindow
from ui.panels.page_tab import PageTab
from ui.panels.perform_tab import PerformTab
from core.song_library import SongLibrary


def run_stage5_tests():
    app = QApplication.instance() or QApplication(["stage5_test", "-platform", "offscreen"])
    library = SongLibrary()
    perform_tab = PerformTab(song_library=library)
    page_tab = PageTab()
    perform_tab.export_to_page.connect(page_tab.load_cues)
    results = []

    def log_result(tc_id, name, status, detail):
        results.append((tc_id, name, status, detail))
        mark = "✅ PASS" if status == "PASS" else "❌ FAIL"
        print(f"[{mark}] {tc_id}: {name}")
        print(f"       Detail: {detail}\n")

    print("=" * 80)
    print("🚀 MEMULAI PENGUJIAN TAHAP 5: TAB PAGE (4 SKENARIO)")
    print("=" * 80 + "\n")

    # --------------------------------------------------------------------------
    # TC-PAGE-01: Auto-Generate Kisi-Kisi Pad dari Perform
    # --------------------------------------------------------------------------
    library.add_analysis({
        "title": "Track Praise 1", "bpm": 125, "quadrant": "Q1_PRAISE_HIGH",
        "palette": {"R": 255, "G": 180, "B": 20, "W": 30}
    })
    library.add_analysis({
        "title": "Track Worship 2", "bpm": 68, "quadrant": "Q4_PEACE_INTIMACY",
        "palette": {"R": 30, "G": 10, "B": 190, "W": 40}
    })

    # Setiap lagu menghasilkan 6 section cues -> total 12 pads
    pad_count = len(page_tab.executor_buttons)
    btn1_text = page_tab.executor_buttons[0].text() if pad_count > 0 else ""
    btn7_text = page_tab.executor_buttons[6].text() if pad_count > 6 else ""

    if pad_count == 12 and "[1] Intro" in btn1_text and "[2] Intro" in btn7_text:
        log_result("TC-PAGE-01", "Auto-Generate Kisi-Kisi Pad dari Perform", "PASS",
                   f"Dua lagu teranalisis otomatis mempopulasi {pad_count} tombol pad eksekutor (Lagu 1: {btn1_text.splitlines()[0]}, Lagu 2: {btn7_text.splitlines()[0]}).")
    else:
        log_result("TC-PAGE-01", "Auto-Generate Kisi-Kisi Pad dari Perform", "FAIL",
                   f"pad_count={pad_count}, btn1={btn1_text}, btn7={btn7_text}")

    # --------------------------------------------------------------------------
    # TC-PAGE-02: Eksekusi Pad Spontan Panggung
    # --------------------------------------------------------------------------
    triggered_cues = []
    page_tab.cue_activated.connect(triggered_cues.append)

    # Klik pad pertama
    first_btn = page_tab.executor_buttons[0]
    first_btn.click()

    if triggered_cues and triggered_cues[-1]["label"] == first_btn.cue_data["label"]:
        log_result("TC-PAGE-02", "Eksekusi Pad Spontan Panggung", "PASS",
                   f"Klik tombol pad memancarkan sinyal cue_activated ({triggered_cues[-1]['label'].replace(chr(10), ' ')}) ke panggung secara instan.")
    else:
        log_result("TC-PAGE-02", "Eksekusi Pad Spontan Panggung", "FAIL",
                   f"triggered_cues={triggered_cues}")

    # --------------------------------------------------------------------------
    # TC-PAGE-03: Uji Auto-Compaction Saat Lagu Dihapus (Skenario Andreas)
    # --------------------------------------------------------------------------
    # Tambahkan 3 lagu lagi sehingga total ada 5 lagu
    for i in range(3, 6):
        library.add_analysis({
            "title": f"Song {i}", "bpm": 100 + i, "quadrant": "Q1_PRAISE_HIGH",
            "palette": {"R": 200, "G": 100, "B": 50, "W": 20}
        })
    pads_5_songs = len(page_tab.executor_buttons)  # 5 * 6 = 30 pads

    # Sekarang hapus lagu nomor 2 dan 3 (0-indexed: index 1 dan 2)
    library.remove([1, 2])
    pads_after_compact = len(page_tab.executor_buttons)  # 3 * 6 = 18 pads

    # Periksa penomoran pad
    labels_after = [b.text().splitlines()[0] for b in page_tab.executor_buttons]
    first_cues = [labels_after[i * 6] for i in range(3)]  # first cue of each song

    if pads_5_songs == 30 and pads_after_compact == 18 and first_cues == ["[1] Intro", "[2] Intro", "[3] Intro"]:
        log_result("TC-PAGE-03", "Uji Auto-Compaction Saat Lagu Dihapus", "PASS",
                   f"Lagu 2 & 3 dihapus: total pad berkurang dari 30 ke 18, lagu 4 & 5 otomatis merapat ke atas menjadi nomor [2] dan [3].")
    else:
        log_result("TC-PAGE-03", "Uji Auto-Compaction Saat Lagu Dihapus", "FAIL",
                   f"pads_5={pads_5_songs}, pads_after={pads_after_compact}, first_cues={first_cues}")

    # --------------------------------------------------------------------------
    # TC-PAGE-04: Tombol Flash Momentary & Restorasi Look
    # --------------------------------------------------------------------------
    win = MainWindow()
    win.tab_address._on_patch_alien_gia()
    # Pasang look latar belakang di buffer DMX
    win.dmx_buffer[0:4] = [200, 150, 100, 50]

    flash_cue = {
        "label": "BLIND WHITE FLASH",
        "type": "flash",
        "color": {"R": 255, "G": 255, "B": 255, "W": 255},
        "dimmer": 255,
        "fade_time": 0.0
    }
    # 1. Simulasikan Flash Ditekan (active=True)
    win._on_cue_activated({**flash_cue, "active": True})
    flash_on_dmx1 = win.dmx_buffer[0]  # Dimmer
    flash_on_dmx2 = win.dmx_buffer[1]  # Red

    # 2. Simulasikan Flash Dilepas (active=False) -> harus memulihkan look lama
    win._on_cue_activated({**flash_cue, "active": False})
    restored_dmx1 = win.dmx_buffer[0]
    restored_dmx2 = win.dmx_buffer[1]

    if (flash_on_dmx1 == 255 and flash_on_dmx2 == 255 and
            restored_dmx1 == 200 and restored_dmx2 == 150):
        log_result("TC-PAGE-04", "Tombol Flash Momentary & Restorasi Look", "PASS",
                   f"Saat flash ditekan: DMX naik ke (Dimmer=255, R=255). Saat dilepas: DMX pulih seketika ke look awal (Dimmer=200, R=150).")
    else:
        log_result("TC-PAGE-04", "Tombol Flash Momentary & Restorasi Look", "FAIL",
                   f"flash_on=({flash_on_dmx1},{flash_on_dmx2}), restored=({restored_dmx1},{restored_dmx2})")

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------
    total = len(results)
    passed = sum(1 for r in results if r[2] == "PASS")
    failed = total - passed
    print("=" * 80)
    print(f"📊 REKAPITULASI PENGUJIAN TAHAP 5: {passed}/{total} SKENARIO LULUS ({passed/total*100:.1f}%)")
    print("=" * 80)

    perform_tab.close()
    page_tab.close()
    win.close()
    return failed == 0


if __name__ == "__main__":
    success = run_stage5_tests()
    sys.exit(0 if success else 1)
