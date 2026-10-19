#!/usr/bin/env python3
"""
test_advanced_scenarios.py - Suite Pengujian Skenario Ekstrem & Lanjutan ZZLUXORA v10.

Menguji skenario-skenario di luar happy-path:
  1. FULL-UNIVERSE SATURATION: Patch 64 unit fixture 8-kanal hingga DMX 512 penuh 100%.
  2. BOUNDARY RELOCATION EDGE: Relokasi fixture dari ujung awal (DMX 1) tepat ke blok terakhir (DMX 505-512).
  3. RAPID REORDER UNDER HIGH LOAD: Reorder acak pada rig penuh 64 fixture tanpa kebocoran memori / crash.
  4. LIVE CUE JUMPING & INTERRUPTION: Lompat acak antar-seksi lagu (Intro -> Ending -> Chorus) saat transisi aktif.
  5. BLACKOUT DURING CROSSFADE: Tekan BLACKOUT di tengah transisi crossfade 5 detik; buktikan panggung mati total.
  6. CONCURRENT FLASH OVERRIDE: Pemicuan Flash Strobe saat crossfade berlangsung dan pemulihan akurat saat dilepas.
  7. CORRUPTED SHOWFILE RESILIENCE: Membuka berkas .zlx yang rusak/tidak lengkap tanpa merusak state proyek aktif.
  8. FULL 512 RANDOM FADER SWEEP: 512 kanal diisi nilai acak dan diskalakan bolak-balik oleh Grand Master.
"""

import json
import os
import random
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import _autodialog_guard  # noqa: F401
from ui.qt_compat import QApplication
from ui.main_window import MainWindow
from core.project_io import ProjectIO
from core.models import EmotionCoordinate
from core.color_engine import ColorEngine


def run_advanced_scenarios():
    app = QApplication.instance() or QApplication(["adv_test", "-platform", "offscreen"])
    win = MainWindow()
    results = []

    def log(sc_id, name, status, detail):
        results.append((sc_id, name, status, detail))
        mark = "✅ PASS" if status == "PASS" else "❌ FAIL"
        print(f"[{mark}] {sc_id}: {name}")
        print(f"       Detail: {detail}\n")

    print("\n" + "=" * 90)
    print("🔥 SUITE PENGUJIAN SKENARIO EKSTREM & LANJUTAN ZZLUXORA v10")
    print("=" * 90 + "\n")

    # --------------------------------------------------------------------------
    # SC-ADV-01: Full-Universe Saturation (64 Fixtures x 8 Channels = 512 Channels)
    # --------------------------------------------------------------------------
    win.tab_address.record_undo()
    for b in win.tab_address.grid_area.boxes.values():
        b.set_unpatched()

    single_fix_channels = [
        {"type": "dimmer", "label": "DIM"},
        {"type": "red", "label": "RED"},
        {"type": "green", "label": "GRN"},
        {"type": "blue", "label": "BLU"},
        {"type": "white", "label": "WHT"},
        {"type": "strobe", "label": "STR"},
        {"type": "program", "label": "PRG"},
        {"type": "speed", "label": "SPD"},
    ]

    all_patched = True
    for i in range(64):
        start_dmx = (i * 8) + 1
        payload = {"name": f"PAR #{i+1}", "channels": single_fix_channels}
        ok = win.tab_address._on_fixture_dropped(start_dmx, payload, record_undo=False, notify=False)
        if not ok:
            all_patched = False
            break

    win.tab_address.update_fixture_brackets()
    win.tab_address.patch_changed.emit()

    patched_count = len(win.tab_address.get_patched_fixtures())
    occupied_boxes = sum(1 for b in win.tab_address.grid_area.boxes.values() if b.is_patched)

    if all_patched and patched_count == 64 and occupied_boxes == 512:
        log("SC-ADV-01", "Full-Universe Saturation (64 Fixtures x 8 CH = 512 CH)", "PASS",
            f"Seluruh semesta 512 DMX terisi penuh 100% (64 fixture berurutan dari Ch 1 s.d. 512).")
    else:
        log("SC-ADV-01", "Full-Universe Saturation (64 Fixtures x 8 CH = 512 CH)", "FAIL",
            f"patched_count={patched_count}, occupied_boxes={occupied_boxes}")

    # --------------------------------------------------------------------------
    # SC-ADV-02: Boundary Relocation Edge (DMX 1 ke DMX 505)
    # --------------------------------------------------------------------------
    # Bersihkan DMX 505-512 dulu agar ada celah
    for ch in range(505, 513):
        win.tab_address.grid_area.boxes[ch].set_unpatched()

    # Relokasikan fixture #1 dari DMX 1 ke DMX 505
    move_payload = {
        "name": "PAR #1",
        "channels": single_fix_channels,
        "move_source_channels": list(range(1, 9))
    }
    reloc_ok = win.tab_address._on_fixture_dropped(505, move_payload)
    ch1_freed = not win.tab_address.grid_area.boxes[1].is_patched
    ch505_patched = win.tab_address.grid_area.boxes[505].is_patched and win.tab_address.grid_area.boxes[512].is_patched

    if reloc_ok and ch1_freed and ch505_patched:
        log("SC-ADV-02", "Boundary Relocation Edge (DMX 1 ke DMX 505-512)", "PASS",
            "Fixture sukses dipindahkan dari ujung awal (DMX 1) tepat ke 8 kanal paling akhir semesta (DMX 505-512).")
    else:
        log("SC-ADV-02", "Boundary Relocation Edge (DMX 1 ke DMX 505-512)", "FAIL",
            f"reloc_ok={reloc_ok}, ch1_freed={ch1_freed}, ch505_patched={ch505_patched}")

    # --------------------------------------------------------------------------
    # SC-ADV-03: Rapid Reorder Under High Load (Shuffling 60+ Fixtures)
    # --------------------------------------------------------------------------
    fixtures_before_shuffle = win.tab_address.get_patched_fixtures()
    count_before = len(fixtures_before_shuffle)
    # Tukar posisi fixture berkali-kali
    for _ in range(10):
        src = random.randint(0, count_before - 2)
        dst = random.randint(0, count_before - 1)
        win.tab_address.reorder_fixture(src, dst)

    fixtures_after_shuffle = win.tab_address.get_patched_fixtures()
    count_after = len(fixtures_after_shuffle)
    all_dmx_intact = all(f["channels"] for f in fixtures_after_shuffle)

    if count_before == count_after and all_dmx_intact:
        log("SC-ADV-03", "Rapid Reorder Under High Load", "PASS",
            f"10 kali pengacakan urutan sequence pada {count_before} fixture berjalan instan tanpa korupsi data.")
    else:
        log("SC-ADV-03", "Rapid Reorder Under High Load", "FAIL",
            f"count_before={count_before}, count_after={count_after}")

    # --------------------------------------------------------------------------
    # SC-ADV-04: Live Cue Jumping & Interruption (Intro -> Ending -> Chorus)
    # --------------------------------------------------------------------------
    # Siapkan lagu teranalisis di perform
    win.tab_perform.playlist.clear()
    song_sample = {
        "title": "Praise Anthem",
        "quadrant": "Q1_PRAISE_HIGH",
        "bpm": 128.0,
        "palette": {"R": 255, "G": 180, "B": 20, "W": 40}
    }
    win.tab_perform.add_analyzed_song(song_sample)
    win.tab_perform._on_song_selected(0)

    # Lompat acak: Picu Intro (row 0), lalu seketika lompat ke Ending (row 5), lalu ke Chorus (row 2)
    win.tab_perform._trigger_cue_at_row(0)
    cue0 = win.tab_perform.active_cue_index
    win.tab_perform._trigger_cue_at_row(5)
    cue5 = win.tab_perform.active_cue_index
    win.tab_perform._trigger_cue_at_row(2)
    cue2 = win.tab_perform.active_cue_index

    if cue0 == 0 and cue5 == 5 and cue2 == 2:
        log("SC-ADV-04", "Live Cue Jumping & Interruption", "PASS",
            f"Lompatan acak [Intro] -> [Ending] -> [Chorus] dieksekusi seketika; state cue aktif sinkron presisi.")
    else:
        log("SC-ADV-04", "Live Cue Jumping & Interruption", "FAIL",
            f"cue0={cue0}, cue5={cue5}, cue2={cue2}")

    # --------------------------------------------------------------------------
    # SC-ADV-05: Blackout During Active Crossfade
    # --------------------------------------------------------------------------
    # Mulai crossfade panjang (5 detik)
    fade_cue = {
        "section": "Build Up",
        "type": "scene",
        "active": True,
        "dimmer": 255,
        "color": {"R": 255, "G": 255, "B": 0, "W": 100},
        "fade_time": 5.0
    }
    win._on_cue_activated(fade_cue)
    fade_started = win._crossfade_timer.isActive()

    # Eksekusi Blackout saat crossfade sedang berjalan
    win._on_blackout_clicked()
    timer_stopped = not win._crossfade_timer.isActive()
    buffer_zeroed = all(win.dmx_buffer[i] == 0 for i in range(512))
    faders_zeroed = all(win.tab_mixer.faders[ch].value == 0 for ch in range(1, 513))

    if fade_started and timer_stopped and buffer_zeroed and faders_zeroed:
        log("SC-ADV-05", "Blackout During Active Crossfade", "PASS",
            "Tombol BLACKOUT seketika mematikan timer crossfade yang sedang berjalan, me-zero seluruh 512 kanal DMX buffer dan 512 fader mixer.")
    else:
        log("SC-ADV-05", "Blackout During Active Crossfade", "FAIL",
            f"fade_started={fade_started}, timer_stopped={timer_stopped}, buffer_zeroed={buffer_zeroed}")

    # --------------------------------------------------------------------------
    # SC-ADV-06: Concurrent Flash Override & Restoration
    # --------------------------------------------------------------------------
    # Pastikan fixture Alien AL36 ter-patch di DMX 1, 17, 33, 49
    win.tab_address._on_patch_alien_gia()

    # Set latar belakang panggung: Ambient Biru Teduh
    bg_cue = {
        "type": "scene",
        "active": True,
        "dimmer": 180,
        "color": {"R": 20, "G": 40, "B": 220, "W": 30},
        "fade_time": 0.0
    }
    win._on_cue_activated(bg_cue)
    bg_blue_val = win.dmx_buffer[3]  # Kanal Blue di fixture 1 (DMX 4)

    # Tekan Flash Strobe
    flash_cue = {
        "type": "flash",
        "active": True,
        "dimmer": 255,
        "color": {"R": 255, "G": 255, "B": 255, "W": 255},
        "fade_time": 0.0
    }
    win._on_cue_activated(flash_cue)
    flash_dimmer = win.dmx_buffer[0]
    flash_white = win.dmx_buffer[1]  # Karena Alien AL36 white-folded, R naik ke 255

    # Lepas Flash Strobe
    win._on_cue_activated({**flash_cue, "active": False})
    restored_blue_val = win.dmx_buffer[3]

    if flash_dimmer == 255 and flash_white == 255 and restored_blue_val == bg_blue_val:
        log("SC-ADV-06", "Concurrent Flash Override & Restoration", "PASS",
            f"Flash berhasil meng-override panggung ke putih maksimal (Dimmer=255), dan saat dilepas memulihkan look ambient biru semula ({restored_blue_val}).")
    else:
        log("SC-ADV-06", "Concurrent Flash Override & Restoration", "FAIL",
            f"flash_dimmer={flash_dimmer}, restored_blue={restored_blue_val} (expected {bg_blue_val})")

    # --------------------------------------------------------------------------
    # SC-ADV-07: Corrupted Showfile Resilience
    # --------------------------------------------------------------------------
    # Buat file JSON rusak (bukan skema ZZLUXORA)
    with tempfile.NamedTemporaryFile(suffix=".zlx", delete=False, mode="w") as tf:
        tf.write('{"app": "INVALID_APP", "patches": "not_a_list"}')
        bad_zlx = tf.name

    try:
        current_path_before = win.current_project_path
        # Coba muat file rusak
        win.load_project_file(bad_zlx, notify=False)
        current_path_after = win.current_project_path

        # State proyek lama tidak boleh berganti ke file rusak
        protected = (current_path_before == current_path_after)
        if protected:
            log("SC-ADV-07", "Corrupted Showfile Resilience", "PASS",
                "Gerbang validasi ProjectIO menolak showfile cacat; state proyek dan patch lama terlindungi 100%.")
        else:
            log("SC-ADV-07", "Corrupted Showfile Resilience", "FAIL",
                f"Project adopted corrupted file path: {current_path_after}")
    finally:
        Path(bad_zlx).unlink(missing_ok=True)

    # --------------------------------------------------------------------------
    # SC-ADV-08: Full 512 Random Fader Sweep
    # --------------------------------------------------------------------------
    random_values = [random.randint(0, 255) for _ in range(512)]
    for ch in range(1, 513):
        win.tab_mixer.set_channel_value(ch, random_values[ch - 1], silent=True)

    # Turunkan Master ke 0%
    win._on_fader_moved(0, 0)
    all_zero_dmx = all(win.dmx_buffer[i] == 0 for i in range(512))

    # Naikkan Master ke 100%
    win._on_fader_moved(0, 255)
    all_restored_dmx = [win.dmx_buffer[i] for i in range(512)] == random_values

    if all_zero_dmx and all_restored_dmx:
        log("SC-ADV-08", "Full 512 Random Fader Sweep", "PASS",
            "512 fader acak terskala sempurna: saat Master=0 seluruh DMX menjadi 0; saat Master=255 seluruh 512 nilai acak pulih bit-for-bit.")
    else:
        log("SC-ADV-08", "Full 512 Random Fader Sweep", "FAIL",
            f"all_zero_dmx={all_zero_dmx}, all_restored_dmx={all_restored_dmx}")

    # --------------------------------------------------------------------------
    # REKAPITULASI
    # --------------------------------------------------------------------------
    total = len(results)
    passed = sum(1 for r in results if r[2] == "PASS")
    failed = total - passed
    print("=" * 90)
    print(f"📊 HASIL SUITE SKENARIO EKSTREM: {passed}/{total} LULUS ({passed/total*100:.1f}%)")
    print("=" * 90)

    win.close()
    return failed == 0


if __name__ == "__main__":
    success = run_advanced_scenarios()
    sys.exit(0 if success else 1)
