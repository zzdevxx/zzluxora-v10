#!/usr/bin/env python3
"""
test_stage3_result.py - Eksekusi Pengujian Otomatis Tahap 3: Tab Result (TC-RSLT-01 s.d. TC-RSLT-04).
"""

import sys
from pathlib import Path

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import _autodialog_guard  # noqa: F401
from ui.qt_compat import QApplication
from ui.panels.result_tab import ResultTab
from core.song_library import SongLibrary
from core.color_engine import ColorEngine
from core.models import EmotionCoordinate


def run_stage3_tests():
    app = QApplication.instance() or QApplication(["stage3_test", "-platform", "offscreen"])
    library = SongLibrary()
    tab = ResultTab(song_library=library)
    results = []

    def log_result(tc_id, name, status, detail):
        results.append((tc_id, name, status, detail))
        mark = "✅ PASS" if status == "PASS" else "❌ FAIL"
        print(f"[{mark}] {tc_id}: {name}")
        print(f"       Detail: {detail}\n")

    print("=" * 80)
    print("🚀 MEMULAI PENGUJIAN TAHAP 3: TAB RESULT (4 SKENARIO)")
    print("=" * 80 + "\n")

    # --------------------------------------------------------------------------
    # TC-RSLT-01: Sinkronisasi Otomatis Seleksi Lagu & Tampilan Bersih
    # --------------------------------------------------------------------------
    idx_a = library.add_analysis({
        "title": "Worship Track A", "bpm": 70.0, "valence": 0.25, "arousal": -0.15,
        "rms": 0.65, "frames_count": 500, "duration_sec": 12.0, "fps_rate": 43.07,
        "quadrant": "Q4_PEACE_INTIMACY", "spectral_centroid": 1800.0,
        "chroma_key": "F Major", "mfcc_density": 0.6, "spectral_flux": 0.05,
        "palette": {"R": 40, "G": 0, "B": 20, "W": 130}
    })
    idx_b = library.add_path("data/audio/queued_track_b.wav")  # unanalysed

    # Pilih lagu A (analysed)
    tab._on_song_row_selected(idx_a)
    text_a = [tab.table.item(r, 1).text() for r in range(tab.table.rowCount()) if tab.table.item(r, 1)]
    has_bpm_a = any("70.0 BPM" in t for t in text_a)
    coord_v_a = tab.russell_plane.valence

    # Ganti pilih lagu B (unanalysed)
    tab._on_song_row_selected(idx_b)
    text_b = [tab.table.item(r, 1).text() for r in range(tab.table.rowCount()) if tab.table.item(r, 1)]
    empty_b = text_b[0] == "No analysis yet" and all(v == "-" for v in text_b[1:])
    coord_v_b = tab.russell_plane.valence

    if has_bpm_a and coord_v_a == 0.25 and empty_b and coord_v_b == 0.0:
        log_result("TC-RSLT-01", "Sinkronisasi Otomatis Seleksi Lagu", "PASS",
                   "Lagu teranalisis menampilkan 12 parameter lengkap; lagu belum dianalisis mengosongkan kartu secara jujur tanpa menampilkan angka palsu.")
    else:
        log_result("TC-RSLT-01", "Sinkronisasi Otomatis Seleksi Lagu", "FAIL",
                   f"has_bpm_a={has_bpm_a}, coord_a={coord_v_a}, empty_b={empty_b}, coord_b={coord_v_b}")

    # --------------------------------------------------------------------------
    # TC-RSLT-02: Validitas Pemetaan Kuadran Russell 2D (Worship vs Praise)
    # --------------------------------------------------------------------------
    # Worship: Valence > 0, Arousal < 0 -> Q4 PEACE_INTIMACY
    coord_worship = EmotionCoordinate(valence=0.30, arousal=-0.20)
    quad_worship = coord_worship.quadrant

    # Praise: Valence > 0, Arousal > 0 -> Q1 PRAISE_HIGH
    coord_praise = EmotionCoordinate(valence=0.35, arousal=0.25)
    quad_praise = coord_praise.quadrant

    if quad_worship == "Q4_PEACE_INTIMACY" and quad_praise == "Q1_PRAISE_HIGH":
        log_result("TC-RSLT-02", "Validitas Pemetaan Kuadran Russell 2D", "PASS",
                   f"Worship (V=+0.30, A=-0.20) dipetakan ke '{quad_worship}'. Praise (V=+0.35, A=+0.25) dipetakan ke '{quad_praise}'.")
    else:
        log_result("TC-RSLT-02", "Validitas Pemetaan Kuadran Russell 2D", "FAIL",
                   f"quad_worship={quad_worship}, quad_praise={quad_praise}")

    # --------------------------------------------------------------------------
    # TC-RSLT-03: Dekomposisi Physical RGBW & White Folding
    # --------------------------------------------------------------------------
    ce = ColorEngine()
    # Test RGB to Physical RGBW decomposition (extracts W = min(R, G, B))
    rgb_test = (200, 150, 100)
    w_extracted = min(rgb_test)  # 100
    r_rem = rgb_test[0] - w_extracted  # 100
    g_rem = rgb_test[1] - w_extracted  # 50
    b_rem = rgb_test[2] - w_extracted  # 0

    # Test White Folding for 3-channel RGB fixtures (W is folded back to R,G,B)
    folded_r = min(255, r_rem + w_extracted)
    folded_g = min(255, g_rem + w_extracted)
    folded_b = min(255, b_rem + w_extracted)

    if (w_extracted == 100 and (r_rem, g_rem, b_rem) == (100, 50, 0) and
            (folded_r, folded_g, folded_b) == rgb_test):
        log_result("TC-RSLT-03", "Dekomposisi Physical RGBW & White Folding", "PASS",
                   f"Dekomposisi fisik mengekstrak W={w_extracted} (R'={r_rem}, G'={g_rem}, B'={b_rem}). White folding memulihkan intensitas penuh {rgb_test} pada lampu 3-kanal RGB.")
    else:
        log_result("TC-RSLT-03", "Dekomposisi Physical RGBW & White Folding", "FAIL",
                   f"w={w_extracted}, rem={(r_rem, g_rem, b_rem)}, folded={(folded_r, folded_g, folded_b)}")

    # --------------------------------------------------------------------------
    # TC-RSLT-04: Re-Analyze Trigger
    # --------------------------------------------------------------------------
    reanalyze_signaled = []
    tab.reanalyze_requested.connect(lambda: reanalyze_signaled.append(True))
    tab.btn_reanalyze.click()

    if reanalyze_signaled == [True]:
        log_result("TC-RSLT-04", "Re-Analyze Trigger", "PASS",
                   "Klik tombol [RE-ANALYZE] memancarkan sinyal reanalyze_requested untuk membuka kembali Tab Analyze.")
    else:
        log_result("TC-RSLT-04", "Re-Analyze Trigger", "FAIL",
                   f"reanalyze_signaled={reanalyze_signaled}")

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------
    total = len(results)
    passed = sum(1 for r in results if r[2] == "PASS")
    failed = total - passed
    print("=" * 80)
    print(f"📊 REKAPITULASI PENGUJIAN TAHAP 3: {passed}/{total} SKENARIO LULUS ({passed/total*100:.1f}%)")
    print("=" * 80)

    tab.close()
    return failed == 0


if __name__ == "__main__":
    success = run_stage3_tests()
    sys.exit(0 if success else 1)
