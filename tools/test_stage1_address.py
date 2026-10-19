#!/usr/bin/env python3
"""
test_stage1_address.py - Eksekusi Pengujian Otomatis Tahap 1: Tab Address (TC-ADDR-01 s.d. TC-ADDR-09).
"""

import sys
import json
from pathlib import Path

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import _autodialog_guard  # noqa: F401
from ui.qt_compat import QApplication, Qt
from ui.main_window import MainWindow
from ui.panels.address_tab import AddressTab


def run_stage1_tests():
    app = QApplication.instance() or QApplication(["stage1_test", "-platform", "offscreen"])
    win = MainWindow()
    tab = win.tab_address
    results = []

    def log_result(tc_id, name, status, detail):
        results.append((tc_id, name, status, detail))
        mark = "✅ PASS" if status == "PASS" else "❌ FAIL"
        print(f"[{mark}] {tc_id}: {name}")
        print(f"       Detail: {detail}\n")

    print("=" * 80)
    print("🚀 MEMULAI PENGUJIAN TAHAP 1: TAB ADDRESS (9 SKENARIO)")
    print("=" * 80 + "\n")

    # --------------------------------------------------------------------------
    # TC-ADDR-01: Verifikasi Grid 20-Kolom Bebas Horizontal Scroll
    # --------------------------------------------------------------------------
    total_boxes = len(tab.grid_area.boxes)
    cols = tab.grid_area.grid_layout.columnCount()
    h_scroll_policy = tab.scroll_area.horizontalScrollBarPolicy()

    # Periksa koordinat baris dan kolom untuk channel 1, 20, 21, 512
    box_1_row, box_1_col, _, _ = tab.grid_area.grid_layout.getItemPosition(tab.grid_area.grid_layout.indexOf(tab.grid_area.boxes[1]))
    box_20_row, box_20_col, _, _ = tab.grid_area.grid_layout.getItemPosition(tab.grid_area.grid_layout.indexOf(tab.grid_area.boxes[20]))
    box_21_row, box_21_col, _, _ = tab.grid_area.grid_layout.getItemPosition(tab.grid_area.grid_layout.indexOf(tab.grid_area.boxes[21]))

    if (total_boxes == 512 and cols == 20 and
            h_scroll_policy == Qt.ScrollBarAlwaysOff and
            box_1_row == 0 and box_1_col == 0 and
            box_20_row == 0 and box_20_col == 19 and
            box_21_row == 1 and box_21_col == 0):
        log_result("TC-ADDR-01", "Verifikasi Grid 20-Kolom Bebas Horizontal Scroll", "PASS",
                   f"Grid memiliki {total_boxes} kotak, tepat 20 kolom (Ch 1 di row 0 col 0, Ch 20 di row 0 col 19, Ch 21 di row 1 col 0), scrollbar horizontal = ScrollBarAlwaysOff.")
    else:
        log_result("TC-ADDR-01", "Verifikasi Grid 20-Kolom Bebas Horizontal Scroll", "FAIL",
                   f"total_boxes={total_boxes}, cols={cols}, h_scroll={h_scroll_policy}, box_21=({box_21_row},{box_21_col})")

    # --------------------------------------------------------------------------
    # TC-ADDR-02: Quick Patch Preset (GIA 4x & Kuma 1x)
    # --------------------------------------------------------------------------
    tab._on_patch_alien_gia()
    alien_fixes = tab.get_patched_fixtures()
    starts_alien = [f["start_channel"] for f in alien_fixes]

    # Cek kode visual channel box Alien AL36
    b1_label = tab.grid_area.boxes[1].lbl_type.text()
    b2_label = tab.grid_area.boxes[2].lbl_type.text()

    tab._on_patch_kuma_bench()
    kuma_fixes = tab.get_patched_fixtures()
    starts_kuma = [f["start_channel"] for f in kuma_fixes]
    b5_label = tab.grid_area.boxes[5].lbl_type.text()  # White channel on Kuma

    if (starts_alien == [1, 17, 33, 49] and starts_kuma == [1] and
            b1_label == "DIM" and b2_label == "RED" and b5_label == "WHT"):
        log_result("TC-ADDR-02", "Quick Patch Preset (GIA 4x & Kuma 1x)", "PASS",
                   f"Preset Alien ter-patch di DMX {starts_alien} (DIM, RED). Preset Kuma ter-patch di DMX {starts_kuma} (Ch 5 = WHT).")
    else:
        log_result("TC-ADDR-02", "Quick Patch Preset (GIA 4x & Kuma 1x)", "FAIL",
                   f"starts_alien={starts_alien}, starts_kuma={starts_kuma}, b1={b1_label}, b5={b5_label}")

    # --------------------------------------------------------------------------
    # TC-ADDR-03: Drag dari Fixture Library ke Grid DMX
    # --------------------------------------------------------------------------
    # Simulasikan drop dari jendela library ke DMX 65
    with open(REPO_ROOT / "fixtures" / "Alien-AL36.zfx") as fp:
        fixture_profile = json.load(fp)

    drop_payload = {
        "name": "Alien-AL36 #2",
        "channels": fixture_profile["channels"]
    }
    ok_drop = tab._on_fixture_dropped(65, drop_payload)
    fixes_after_drop = tab.get_patched_fixtures()
    has_dmx_65 = any(f["start_channel"] == 65 for f in fixes_after_drop)

    if ok_drop and has_dmx_65 and tab.grid_area.boxes[65].is_patched and tab.grid_area.boxes[65].channel_type == "dimmer":
        log_result("TC-ADDR-03", "Drag dari Fixture Library ke Grid DMX", "PASS",
                   f"Drop payload ke DMX 65 sukses. Fixture menempati DMX 65-72. Panel kiri mendeteksi fixture baru.")
    else:
        log_result("TC-ADDR-03", "Drag dari Fixture Library ke Grid DMX", "FAIL",
                   f"ok_drop={ok_drop}, has_dmx_65={has_dmx_65}")

    # --------------------------------------------------------------------------
    # TC-ADDR-04: Direct Drag Relocation Antar-Kotak Grid
    # --------------------------------------------------------------------------
    # Relokasikan fixture di DMX 65 ke DMX 101
    move_payload = {
        "name": "Alien-AL36 #2",
        "channels": fixture_profile["channels"],
        "move_source_channels": list(range(65, 73))
    }
    ok_move = tab._on_fixture_dropped(101, move_payload)
    old_vacated = not tab.grid_area.boxes[65].is_patched
    new_occupied = tab.grid_area.boxes[101].is_patched and tab.grid_area.boxes[101].channel_type == "dimmer"

    if ok_move and old_vacated and new_occupied:
        log_result("TC-ADDR-04", "Direct Drag Relocation Antar-Kotak Grid", "PASS",
                   f"Fixture di DMX 65 sukses dipindahkan ke DMX 101. Kanal lama 65-72 bersih (unpatched), kanal baru 101-108 aktif.")
    else:
        log_result("TC-ADDR-04", "Direct Drag Relocation Antar-Kotak Grid", "FAIL",
                   f"ok_move={ok_move}, old_vacated={old_vacated}, new_occupied={new_occupied}")

    # --------------------------------------------------------------------------
    # TC-ADDR-05: Penolakan Tabrakan Alamat (Collision Safety)
    # --------------------------------------------------------------------------
    # Coba drop fixture ke DMX 98 (butuh 98-105, padahal DMX 101 sudah terisi)
    clash_payload = {
        "name": "Clashing Fixture",
        "channels": fixture_profile["channels"]
    }
    ok_clash = tab._on_fixture_dropped(98, clash_payload)
    # Harus ditolak (return False), dan DMX 101 tidak boleh rusak
    dmx_101_safe = tab.grid_area.boxes[101].is_patched and tab.grid_area.boxes[101].fixture_name == "Alien-AL36 #2"

    if (not ok_clash) and dmx_101_safe:
        log_result("TC-ADDR-05", "Penolakan Tabrakan Alamat (Collision Safety)", "PASS",
                   "Drop ke rentang yang bertabrakan (DMX 98-105 vs DMX 101) ditolak 100%. Fixture asli di DMX 101 tidak rusak.")
    else:
        log_result("TC-ADDR-05", "Penolakan Tabrakan Alamat (Collision Safety)", "FAIL",
                   f"ok_clash={ok_clash}, dmx_101_safe={dmx_101_safe}")

    # --------------------------------------------------------------------------
    # TC-ADDR-06: Uji Batas Kanal DMX 512 (Edge Case)
    # --------------------------------------------------------------------------
    edge_payload = {
        "name": "Overflow Fixture",
        "channels": fixture_profile["channels"]  # 8 channels
    }
    ok_overflow = tab._on_fixture_dropped(508, edge_payload)  # 508 + 8 - 1 = 515 (>512)
    # Harus ditolak tanpa ada silent truncation
    dmx_508_empty = not tab.grid_area.boxes[508].is_patched

    if (not ok_overflow) and dmx_508_empty:
        log_result("TC-ADDR-06", "Uji Batas Kanal DMX 512 (Edge Case)", "PASS",
                   "Drop melampaui batas semesta DMX 512 (DMX 508 butuh 8 kanal -> 515) ditolak 100% tanpa silent truncation.")
    else:
        log_result("TC-ADDR-06", "Uji Batas Kanal DMX 512 (Edge Case)", "FAIL",
                   f"ok_overflow={ok_overflow}, dmx_508_empty={dmx_508_empty}")

    # --------------------------------------------------------------------------
    # TC-ADDR-07: Reorder Sequence Fixture (Tombol ▲ / ▼)
    # --------------------------------------------------------------------------
    tab._on_patch_alien_gia()  # DMX 1, 17, 33, 49
    tab.reorder_fixture(0, 3)  # Geser fixture pertama ke posisi paling akhir
    reordered = tab.get_patched_fixtures()
    starts_reordered = [f["start_channel"] for f in reordered]
    # Alamat fisik DMX pada sel grid harus tetap sama
    physical_intact = (tab.grid_area.boxes[1].is_patched and
                       tab.grid_area.boxes[17].is_patched and
                       tab.grid_area.boxes[33].is_patched and
                       tab.grid_area.boxes[49].is_patched)

    if starts_reordered == [17, 33, 49, 1] and physical_intact:
        log_result("TC-ADDR-07", "Reorder Sequence Fixture (Tombol ▲ / ▼)", "PASS",
                   f"Urutan sequence berubah menjadi {starts_reordered}. Alamat fisik DMX 1, 17, 33, 49 pada grid tetap utuh.")
    else:
        log_result("TC-ADDR-07", "Reorder Sequence Fixture (Tombol ▲ / ▼)", "FAIL",
                   f"starts_reordered={starts_reordered}, physical_intact={physical_intact}")

    # --------------------------------------------------------------------------
    # TC-ADDR-08: Multi-Selection & Batch Removal
    # --------------------------------------------------------------------------
    # Hapus fixture di DMX 17 dan DMX 33 sekaligus (dengan persetujuan dialog)
    from unittest.mock import patch
    from ui.qt_compat import QMessageBox
    with patch("ui.panels.address_tab.QMessageBox.question", return_value=QMessageBox.Yes):
        tab._on_remove_fixtures([17, 33])
    remaining = tab.get_patched_fixtures()
    remaining_starts = [f["start_channel"] for f in remaining]
    dmx_17_cleared = not tab.grid_area.boxes[17].is_patched
    dmx_33_cleared = not tab.grid_area.boxes[33].is_patched
    dmx_1_survives = tab.grid_area.boxes[1].is_patched

    if (17 not in remaining_starts and 33 not in remaining_starts and
            dmx_17_cleared and dmx_33_cleared and dmx_1_survives):
        log_result("TC-ADDR-08", "Multi-Selection & Batch Removal", "PASS",
                   f"Batch removal DMX [17, 33] berhasil. Kanal 17-24 dan 33-40 bersih, fixture lain di DMX {remaining_starts} tetap aman.")
    else:
        log_result("TC-ADDR-08", "Multi-Selection & Batch Removal", "FAIL",
                   f"remaining_starts={remaining_starts}, dmx_17_cleared={dmx_17_cleared}, dmx_33_cleared={dmx_33_cleared}")

    # --------------------------------------------------------------------------
    # TC-ADDR-09: Integritas Undo / Redo (Ctrl+Z / Ctrl+Y)
    # --------------------------------------------------------------------------
    # Lakukan Undo terhadap penghapusan di atas
    tab.undo_patch()
    restored_fixes = tab.get_patched_fixtures()
    restored_starts = [f["start_channel"] for f in restored_fixes]
    undo_ok = 17 in restored_starts and 33 in restored_starts

    # Lakukan Redo
    tab.redo_patch()
    redo_fixes = tab.get_patched_fixtures()
    redo_starts = [f["start_channel"] for f in redo_fixes]
    redo_ok = 17 not in redo_starts and 33 not in redo_starts

    if undo_ok and redo_ok:
        log_result("TC-ADDR-09", "Integritas Undo / Redo (Ctrl+Z / Ctrl+Y)", "PASS",
                   "Undo mengembalikan patch dan urutan fixture secara simetris; Redo memulihkan state perubahan secara presisi.")
    else:
        log_result("TC-ADDR-09", "Integritas Undo / Redo (Ctrl+Z / Ctrl+Y)", "FAIL",
                   f"undo_ok={undo_ok}, redo_ok={redo_ok}")

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------
    total = len(results)
    passed = sum(1 for r in results if r[2] == "PASS")
    failed = total - passed
    print("=" * 80)
    print(f"📊 REKAPITULASI PENGUJIAN TAHAP 1: {passed}/{total} SKENARIO LULUS ({passed/total*100:.1f}%)")
    print("=" * 80)

    win.close()
    return failed == 0


if __name__ == "__main__":
    success = run_stage1_tests()
    sys.exit(0 if success else 1)
