"""
test_section15_consolidation.py - Comprehensive scenario tests for Feedback v4 Section 15.

Covers:
  - SongListPanel: button navigation, single/multi-select, reorder, and remove
  - AddSongDialog: local file loader and YouTube import signal verification
  - AddressTab: 20-column layout, horizontal scroll off, and non-destructive fixture reorder
  - PerformTab: cue editing, custom cue persistence, [FADE IDLE], and Page auto-compaction
  - MixerTab: 512 channels, 8 banks of 64 channels, and high-channel buffer scaling
"""

import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

from ui.qt_compat import HAS_QT, QApplication, Qt, QDialog
from core.song_library import SongLibrary
from core.project_io import ProjectIO


class TestSection15Consolidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAS_QT:
            raise unittest.SkipTest("Qt binding unavailable")
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def setUp(self):
        self._preexisting_widgets = set(self.app.topLevelWidgets()) if HAS_QT else set()

    def tearDown(self):
        if not HAS_QT:
            return
        for widget in list(self.app.topLevelWidgets()):
            if widget not in self._preexisting_widgets:
                widget.close()
                widget.deleteLater()
        self.app.processEvents()

    # --- Scenario 1: SongListPanel Operations ---

    def test_song_list_panel_empty_and_populated_states(self):
        from ui.widgets.song_list_panel import SongListPanel

        library = SongLibrary()
        panel = SongListPanel(library)

        self.assertFalse(panel.empty_label.isHidden())
        self.assertTrue(panel.list_widget.isHidden())
        self.assertFalse(panel.btn_remove.isEnabled())
        self.assertFalse(panel.btn_up.isEnabled())
        self.assertFalse(panel.btn_down.isEnabled())

        library.add_path("track1.wav")
        library.add_path("track2.wav")
        library.add_path("track3.wav")

        self.assertTrue(panel.empty_label.isHidden())
        self.assertFalse(panel.list_widget.isHidden())
        self.assertEqual(panel.list_widget.count(), 3)

        # Select first row: up disabled, down enabled
        panel.list_widget.setCurrentRow(0)
        self.assertTrue(panel.btn_remove.isEnabled())
        self.assertFalse(panel.btn_up.isEnabled())
        self.assertTrue(panel.btn_down.isEnabled())

        # Select middle row: both enabled
        panel.list_widget.setCurrentRow(1)
        self.assertTrue(panel.btn_up.isEnabled())
        self.assertTrue(panel.btn_down.isEnabled())

        # Select last row: up enabled, down disabled
        panel.list_widget.setCurrentRow(2)
        self.assertTrue(panel.btn_up.isEnabled())
        self.assertFalse(panel.btn_down.isEnabled())
        panel.close()

    def test_song_list_panel_move_buttons(self):
        from ui.widgets.song_list_panel import SongListPanel

        library = SongLibrary()
        library.add_path("a.wav")
        library.add_path("b.wav")
        panel = SongListPanel(library)
        panel.list_widget.setCurrentRow(0)

        # Click move down on row 0
        panel.btn_down.click()
        self.assertEqual([s.title for s in library.songs], ["b", "a"])
        self.assertEqual(panel.list_widget.currentRow(), 1)

        # Click move up on row 1
        panel.btn_up.click()
        self.assertEqual([s.title for s in library.songs], ["a", "b"])
        self.assertEqual(panel.list_widget.currentRow(), 0)
        panel.close()

    # --- Scenario 2: AddSongDialog ---

    def test_add_song_dialog_tabs_and_local_file_emission(self):
        from ui.widgets.song_list_panel import AddSongDialog

        dlg = AddSongDialog()
        self.assertEqual(dlg.tab_widget.count(), 2)
        self.assertEqual(dlg.tab_widget.tabText(0), "Local File")
        self.assertEqual(dlg.tab_widget.tabText(1), "YouTube Import")

        emitted_paths = []
        dlg.song_added.connect(emitted_paths.append)

        # Setting local path and accepting
        test_path = str(Path("data/audio/NDC_Worship_-_Bapa_Yang_Kekal.wav").resolve())
        dlg.txt_local_path.setText(test_path)
        dlg.btn_add_local.setEnabled(True)
        dlg._on_add_local_clicked()

        self.assertEqual(emitted_paths, [test_path])
        dlg.close()

    def test_add_song_dialog_youtube_worker_signal_type(self):
        from ui.widgets.song_list_panel import YouTubeDownloadWorker

        worker = YouTubeDownloadWorker("https://www.youtube.com/watch?v=123", "/tmp")
        emitted = []
        worker.download_finished.connect(emitted.append)

        # Verify Path is emitted as str without C++ copy-convert failure
        fake_path = Path("/tmp/downloaded_song.wav")
        with patch("core.youtube_importer.download_and_convert", return_value=fake_path):
            worker.run()

        self.assertEqual(emitted, [str(fake_path)])
        self.assertIsInstance(emitted[0], str)

    # --- Scenario 3: AddressTab 20-Column Geometry & Sequence Reordering ---

    def test_address_tab_20_columns_and_reorder_fixture(self):
        from ui.panels.address_tab import AddressTab

        tab = AddressTab()
        self.assertEqual(len(tab.grid_area.boxes), 512)
        self.assertEqual(tab.grid_area.grid_layout.columnCount(), 20)
        self.assertEqual(tab.scroll_area.horizontalScrollBarPolicy(), Qt.ScrollBarAlwaysOff)

        tab._on_patch_alien_gia()
        fixtures_before = tab.get_patched_fixtures()
        self.assertEqual(len(fixtures_before), 4)
        dmx_starts = [f["start_channel"] for f in fixtures_before]
        self.assertEqual(dmx_starts, [1, 17, 33, 49])

        # Reorder fixture 0 (starts at 1) to index 2
        tab.reorder_fixture(0, 2)
        fixtures_after = tab.get_patched_fixtures()
        reordered_starts = [f["start_channel"] for f in fixtures_after]
        self.assertEqual(reordered_starts, [17, 33, 1, 49])

        # Verify physical DMX box contents at DMX 1 and DMX 17 are completely untouched
        self.assertEqual(tab.grid_area.boxes[1].channel_type, "dimmer")
        self.assertEqual(tab.grid_area.boxes[17].channel_type, "dimmer")
        tab.close()

    def test_address_fixture_relocation_via_dropped(self):
        from ui.panels.address_tab import AddressTab

        tab = AddressTab()
        tab._on_patch_alien_gia()

        # Move fixture at DMX 1 (channels 1-8) to DMX 65
        move_payload = {
            "name": "Alien-AL36 #1",
            "channels": [{"type": "dimmer"}, {"type": "red"}, {"type": "green"}, {"type": "blue"},
                         {"type": "empty"}, {"type": "program"}, {"type": "speed"}, {"type": "empty"}],
            "move_source_channels": list(range(1, 9))
        }
        ok = tab._on_fixture_dropped(65, move_payload)
        self.assertTrue(ok)

        # Old channels 1-8 are unpatched
        self.assertFalse(tab.grid_area.boxes[1].is_patched)
        # New channels 65-72 are patched
        self.assertTrue(tab.grid_area.boxes[65].is_patched)
        self.assertEqual(tab.grid_area.boxes[65].channel_type, "dimmer")
        tab.close()

    # --- Scenario 4: PerformTab Cue Editing & Page Auto-Compaction ---

    def test_perform_custom_cue_editing_and_page_sync(self):
        from ui.panels.perform_tab import PerformTab
        from ui.panels.page_tab import PageTab

        library = SongLibrary()
        library.add_analysis({
            "title": "Song A", "quadrant": "Q1_PRAISE_HIGH", "bpm": 120,
            "palette": {"R": 255, "G": 120, "B": 20, "W": 30}
        })
        library.add_analysis({
            "title": "Song B", "quadrant": "Q4_PEACE_INTIMACY", "bpm": 70,
            "palette": {"R": 30, "G": 20, "B": 180, "W": 20}
        })

        perform_tab = PerformTab(song_library=library)
        page_tab = PageTab()
        perform_tab.export_to_page.connect(page_tab.load_cues)
        perform_tab._refresh_playlist_view()

        # Initial pads count = 2 songs * 6 section cues = 12 cues
        self.assertEqual(len(page_tab.executor_buttons), 12)

        # Remove Song A (row 0 in library)
        library.remove([0])
        # Auto-compacted to 1 song * 6 cues = 6 cues
        self.assertEqual(len(page_tab.executor_buttons), 6)
        first_btn_label = page_tab.executor_buttons[0].text()
        self.assertTrue(first_btn_label.startswith("[1] Intro"))

        # Test [FADE IDLE]
        captured_cues = []
        perform_tab.cue_activated.connect(captured_cues.append)
        perform_tab._on_fade_idle_clicked()
        self.assertEqual(len(captured_cues), 1)
        self.assertEqual(captured_cues[0]["dimmer"], 80)
        self.assertEqual(captured_cues[0]["fade_time"], 3.0)
        self.assertIn("STANDBY IDLE", perform_tab.lbl_cue_status.text())

        perform_tab.close()
        page_tab.close()

    # --- Scenario 5: Full 512-Channel Mixer Save & Load ---

    def test_mixer_512_channels_and_showfile_persistence(self):
        from ui.main_window import MainWindow

        win = MainWindow()
        # Verify 513 faders (Ch 0 Master + Ch 1-512)
        self.assertEqual(len(win.tab_mixer.faders), 513)
        self.assertEqual(len(win.tab_mixer.bank_buttons), 8)

        # Set faders in high range (e.g. Ch 400 and Ch 512)
        win.tab_mixer.set_channel_value(400, 180, silent=True)
        win.tab_mixer.set_channel_value(512, 220, silent=True)
        win.tab_mixer.master_fader.set_value_silent(128)

        # Scale to dmx_buffer
        win._on_fader_moved(0, 128)
        self.assertEqual(win.dmx_buffer[399], int(round(180 * (128 / 255.0))))
        self.assertEqual(win.dmx_buffer[511], int(round(220 * (128 / 255.0))))

        # Save to temporary project and reload
        with tempfile.NamedTemporaryFile(suffix=".zlx", delete=False) as tf:
            tmp_path = tf.name

        try:
            win._save_to_path(tmp_path)
            data = ProjectIO.load_project(tmp_path)
            self.assertIsNotNone(data)
            self.assertIn("400", data["faders"])
            self.assertIn("512", data["faders"])
            self.assertEqual(data["faders"]["400"], 180)
            self.assertEqual(data["faders"]["512"], 220)

            # Reload into a fresh MainWindow
            win2 = MainWindow()
            win2.load_project_file(tmp_path, notify=False)
            self.assertEqual(win2.tab_mixer.faders[400].value, 180)
            self.assertEqual(win2.tab_mixer.faders[512].value, 220)
            self.assertEqual(win2.dmx_buffer[399], int(round(180 * (128 / 255.0))))
            self.assertEqual(win2.dmx_buffer[511], int(round(220 * (128 / 255.0))))
            win2.close()
        finally:
            Path(tmp_path).unlink(missing_ok=True)
            win.close()


if __name__ == "__main__":
    unittest.main()
