#!/usr/bin/env python3
"""
run_all_tab_scenarios.py - Master Orchestrator Pengujian Seluruh Skenario Per Tab (Tab 1 s.d. Tab 6).
Menjalankan:
  - Tahap 1: Tab Address (9 Skenario)
  - Tahap 2: Tab Analyze (6 Skenario)
  - Tahap 3: Tab Result (4 Skenario)
  - Tahap 4: Tab Perform (8 Skenario)
  - Tahap 5: Tab Page (4 Skenario)
  - Tahap 6: Tab Mixer (7 Skenario)
Total: 38 Skenario Uji Komprehensif.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from test_stage1_address import run_stage1_tests
from test_stage2_analyze import run_stage2_tests
from test_stage3_result import run_stage3_tests
from test_stage4_perform import run_stage4_tests
from test_stage5_page import run_stage5_tests
from test_stage6_mixer import run_stage6_tests


def main():
    print("\n" + "=" * 90)
    print("🌟 MASTER SUITE PENGUJIAN PER TAB ZZLUXORA v10 (38 SKENARIO)")
    print("=" * 90 + "\n")

    stages = [
        ("Tahap 1: Tab Address (DMX 512 & Patching)", run_stage1_tests),
        ("Tahap 2: Tab Analyze (Audio Loader & DSP STFT)", run_stage2_tests),
        ("Tahap 3: Tab Result (Russell 2D & RGBW Dashboard)", run_stage3_tests),
        ("Tahap 4: Tab Perform (Live Show Sequencer & Cues)", run_stage4_tests),
        ("Tahap 5: Tab Page (Virtual Executor & Auto-Compaction)", run_stage5_tests),
        ("Tahap 6: Tab Mixer (512 Faders & grandMA3 Deck)", run_stage6_tests),
    ]

    report = []
    all_ok = True

    for name, runner in stages:
        success = runner()
        report.append((name, "LULUS (100%)" if success else "GAGAL"))
        if not success:
            all_ok = False

    print("\n" + "=" * 90)
    print("📋 REKAPITULASI AKHIR PENGUJIAN 6 TAHAP (TAB ADDRESS s.d. TAB MIXER)")
    print("=" * 90)
    for name, status in report:
        mark = "✅" if "LULUS" in status else "❌"
        print(f"  {mark} {name:<55} : {status}")
    print("=" * 90)

    if all_ok:
        print("\n🎉 SEMUA 38 SKENARIO PENGUJIAN DARI TAB 1 SAMPAI TAB 6 LULUS 100% TANPA CACAT! 🎉\n")
        return 0
    else:
        print("\n❌ TERDAPAT SKENARIO YANG GAGAL. SILAKAN PERIKSA DETAIL DI ATAS.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
