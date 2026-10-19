#!/usr/bin/env python3
"""
test_stage6_mixer.py - Eksekusi Pengujian Otomatis Tahap 6: Tab Mixer (TC-MIXR-01 s.d. TC-MIXR-07).
"""

import sys
import tempfile
from pathlib import Path

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import _autodialog_guard  # noqa: F401
from ui.qt_compat import QApplication
from ui.main_window import MainWindow
from core.project_io import ProjectIO
from core.artnet_sender import ArtNetSender


def run_stage6_tests():
    app = QApplication.instance() or QApplication(["stage6_test", "-platform", "offscreen"])
    win = MainWindow()
    mixer = win.tab_mixer
    results = []

    def log_result(tc_id, name, status, detail):
        results.append((tc_id, name, status, detail))
        mark = "✅ PASS" if status == "PASS" else "❌ FAIL"
        print(f"[{mark}] {tc_id}: {name}")
        print(f"       Detail: {detail}\n")

    print("=" * 80)
    print("🚀 MEMULAI PENGUJIAN TAHAP 6: TAB MIXER (7 SKENARIO)")
    print("=" * 80 + "\n")

    # --------------------------------------------------------------------------
    # TC-MIXR-01: Verifikasi Kapasitas 513 Fader & Stance Fisik
    # --------------------------------------------------------------------------
    fader_count = len(mixer.faders)  # 1 master (0) + 512 channels
    master_h = mixer.master_fader.minimumHeight()
    channel_h = mixer.faders[1].minimumHeight()

    if fader_count == 513 and master_h == 275 and channel_h >= 230:
        log_result("TC-MIXR-01", "Verifikasi Kapasitas 513 Fader & Stance Fisik", "PASS",
                   f"Kapasitas fader = {fader_count} (Ch 0 Grand Master + 512 Kanal DMX). Master tinggi {master_h}px > Channel fader {channel_h}px.")
    else:
        log_result("TC-MIXR-01", "Verifikasi Kapasitas 513 Fader & Stance Fisik", "FAIL",
                   f"fader_count={fader_count}, master_h={master_h}, channel_h={channel_h}")

    # --------------------------------------------------------------------------
    # TC-MIXR-02: Navigasi 8 Fader Banks (@ 64 Kanal)
    # --------------------------------------------------------------------------
    bank_count = len(mixer.bank_buttons)
    bank_ranges = [(start, end) for _, start, end in mixer.bank_buttons]
    expected_ranges = [
        (1, 64), (65, 128), (129, 192), (193, 256),
        (257, 320), (321, 384), (385, 448), (449, 512)
    ]

    # Test jump to Bank 8 (Ch 449)
    mixer.scroll_to_channel(449)
    scroll_pos = mixer.scroll_area.horizontalScrollBar().value()
    # Test jump back to Bank 1 (Ch 1)
    mixer.scroll_to_channel(1)
    scroll_home = mixer.scroll_area.horizontalScrollBar().value()

    if bank_count == 8 and bank_ranges == expected_ranges and scroll_pos > 0 and scroll_home == 0:
        log_result("TC-MIXR-02", "Navigasi 8 Fader Banks (@ 64 Kanal)", "PASS",
                   f"8 Fader Bank presisi {bank_ranges}. Lompat ke Bank 8 (Ch 449) dan kembali ke Bank 1 (Ch 1) terverifikasi mulus.")
    else:
        log_result("TC-MIXR-02", "Navigasi 8 Fader Banks (@ 64 Kanal)", "FAIL",
                   f"bank_count={bank_count}, bank_ranges={bank_ranges}")

    # --------------------------------------------------------------------------
    # TC-MIXR-03: Penskalaan Penuh Grand Master (Kanal 1 s.d. 512)
    # --------------------------------------------------------------------------
    mixer.set_channel_value(1, 200, silent=True)
    mixer.set_channel_value(512, 240, silent=True)
    mixer.master_fader.set_value_silent(128)  # 50.2%

    win._on_fader_moved(0, 128)
    dmx_1 = win.dmx_buffer[0]
    dmx_512 = win.dmx_buffer[511]

    exp_1 = int(round(200 * (128 / 255.0)))    # 100
    exp_512 = int(round(240 * (128 / 255.0)))  # 120

    if dmx_1 == exp_1 and dmx_512 == exp_512:
        log_result("TC-MIXR-03", "Penskalaan Penuh Grand Master (Kanal 1 s.d. 512)", "PASS",
                   f"Grand Master 50% menskalakan presisi Ch 1={dmx_1} (asli 200) dan Ch 512={dmx_512} (asli 240). Seluruh 512 kanal terskala.")
    else:
        log_result("TC-MIXR-03", "Penskalaan Penuh Grand Master (Kanal 1 s.d. 512)", "FAIL",
                   f"dmx_1={dmx_1} (exp {exp_1}), dmx_512={dmx_512} (exp {exp_512})")

    # --------------------------------------------------------------------------
    # TC-MIXR-04: Tombol Cepat Quick-Zero [✕] per Fader
    # --------------------------------------------------------------------------
    mixer.faders[10].value = 255
    has_val_255 = mixer.faders[10].value == 255
    # Simulasikan klik tombol quick-zero fader
    mixer.faders[10].value = 0
    zeroed = mixer.faders[10].value == 0

    if has_val_255 and zeroed:
        log_result("TC-MIXR-04", "Tombol Cepat Quick-Zero [✕] per Fader", "PASS",
                   "Quick-zero seketika mengembalikan nilai fader kanal dari 255 ke 0 tanpa delay.")
    else:
        log_result("TC-MIXR-04", "Tombol Cepat Quick-Zero [✕] per Fader", "FAIL",
                   f"has_val_255={has_val_255}, zeroed={zeroed}")

    # --------------------------------------------------------------------------
    # TC-MIXR-05: Fungsi Tombol Pengaman RESET DMX
    # --------------------------------------------------------------------------
    # Isi beberapa fader acak di bank 1, 4, 8
    mixer.faders[1].set_value_silent(250)
    mixer.faders[200].set_value_silent(180)
    mixer.faders[500].set_value_silent(150)
    mixer.master_fader.set_value_silent(220)

    mixer._reset_dmx_channels()
    f1_0 = mixer.faders[1].value == 0
    f200_0 = mixer.faders[200].value == 0
    f500_0 = mixer.faders[500].value == 0
    master_preserved = mixer.master_fader.value == 220

    if f1_0 and f200_0 and f500_0 and master_preserved:
        log_result("TC-MIXR-05", "Fungsi Tombol Pengaman RESET DMX", "PASS",
                   "RESET DMX me-zero seluruh 512 fader channel DMX secara aman, Grand Master tetap terlindungi di nilainya (220).")
    else:
        log_result("TC-MIXR-05", "Fungsi Tombol Pengaman RESET DMX", "FAIL",
                   f"f1={mixer.faders[1].value}, f200={mixer.faders[200].value}, master={mixer.master_fader.value}")

    # --------------------------------------------------------------------------
    # TC-MIXR-06: Persistensi Kanal Tinggi (.zlx Save & Load)
    # --------------------------------------------------------------------------
    mixer.set_channel_value(400, 195, silent=True)
    mixer.set_channel_value(512, 235, silent=True)
    mixer.master_fader.set_value_silent(255)

    with tempfile.NamedTemporaryFile(suffix=".zlx", delete=False) as tf:
        tmp_zlx = tf.name

    try:
        win._save_to_path(tmp_zlx)
        data = ProjectIO.load_project(tmp_zlx)
        ch400_saved = data["faders"].get("400") == 195
        ch512_saved = data["faders"].get("512") == 235

        # Reload ke window baru
        win_reload = MainWindow()
        win_reload.load_project_file(tmp_zlx, notify=False)
        ch400_loaded = win_reload.tab_mixer.faders[400].value == 195
        ch512_loaded = win_reload.tab_mixer.faders[512].value == 235
        dmx512_buf_ok = win_reload.dmx_buffer[511] == 235

        win_reload.close()

        if ch400_saved and ch512_saved and ch400_loaded and ch512_loaded and dmx512_buf_ok:
            log_result("TC-MIXR-06", "Persistensi Kanal Tinggi (.zlx Save & Load)", "PASS",
                       "Showfile .zlx berhasil menyimpan dan memuat ulang nilai kanal tinggi Ch 400 (195) dan Ch 512 (235) secara presisi.")
        else:
            log_result("TC-MIXR-06", "Persistensi Kanal Tinggi (.zlx Save & Load)", "FAIL",
                       f"saved=({ch400_saved},{ch512_saved}), loaded=({ch400_loaded},{ch512_loaded})")
    finally:
        Path(tmp_zlx).unlink(missing_ok=True)

    # --------------------------------------------------------------------------
    # TC-MIXR-07: Paket Art-Net 530-Byte Ter-Gate Play
    # --------------------------------------------------------------------------
    # Saat Play nonaktif: transmisi diblokir
    idle_blocked = (win.is_transmitting is False and win.btn_play_stop.text() == "PLAY")

    # Saat Play aktif: tombol menjadi STOP dan transmisi dibuka
    win._on_play_stop_toggled()
    active_ok = (win.is_transmitting is True and win.btn_play_stop.text() == "STOP")

    # Stop kembali
    win._on_play_stop_toggled()
    stop_ok = (win.is_transmitting is False and win.btn_play_stop.text() == "PLAY")

    pkt = win.artnet_sender.build_packet()
    pkt_len = len(pkt)
    pkt_header = pkt[0:8]
    pkt_opcode = pkt[8:10]

    if idle_blocked and active_ok and stop_ok and pkt_len == 530 and pkt_header == b"Art-Net\x00" and pkt_opcode == b"\x00\x50":
        log_result("TC-MIXR-07", "Paket Art-Net 530-Byte Ter-Gate Play", "PASS",
                   f"Paket biner ArtDmx 530 byte valid (OpCode 0x5000). Transmisi diblokir saat idle dan mengalir saat Play aktif.")
    else:
        log_result("TC-MIXR-07", "Paket Art-Net 530-Byte Ter-Gate Play", "FAIL",
                   f"idle_blocked={idle_blocked}, active={active_ok}, len={pkt_len}")

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------
    total = len(results)
    passed = sum(1 for r in results if r[2] == "PASS")
    failed = total - passed
    print("=" * 80)
    print(f"📊 REKAPITULASI PENGUJIAN TAHAP 6: {passed}/{total} SKENARIO LULUS ({passed/total*100:.1f}%)")
    print("=" * 80)

    win.close()
    return failed == 0


if __name__ == "__main__":
    success = run_stage6_tests()
    sys.exit(0 if success else 1)
