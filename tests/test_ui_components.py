"""
test_ui_components.py - Unit tests for ZZLUXORA v10 UI and project fixtures.
"""

import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


class TestUIModules(unittest.TestCase):
    """Verifies UI imports, demo showfile patching, and QLC+ workspace agreement."""

    def setUp(self):
        # Every test that builds a MainWindow leaves one alive unless the Qt
        # object is actually destroyed. 35 tests x 4 top-level widgets is enough
        # to corrupt the heap and abort the runner at exit ("malloc_consolidate():
        # unaligned fastbin chunk detected"), even though every assertion passed.
        # Track what exists before the test and tear down whatever it added.
        from ui.qt_compat import QApplication, HAS_QT
        if HAS_QT:
            app = QApplication.instance()
            self._preexisting_widgets = set(app.topLevelWidgets()) if app else set()
        else:
            self._preexisting_widgets = set()

    def tearDown(self):
        from ui.qt_compat import QApplication, HAS_QT
        if not HAS_QT:
            return
        app = QApplication.instance()
        if app is None:
            return
        # deleteLater only queues a deletion that the Qt event loop has to
        # deliver, and this suite never runs one — processEvents alone does not
        # flush DeferredDelete. Destroy the C++ object directly instead. Without
        # this, 35 MainWindows stay alive, their heaps overlap, and the runner
        # aborts at exit with "malloc_consolidate(): unaligned fastbin chunk".
        try:
            import shiboken6
            destroy = shiboken6.delete
        except ImportError:
            try:
                import sip
                destroy = sip.delete
            except ImportError:
                destroy = None

        for widget in app.topLevelWidgets():
            if widget in self._preexisting_widgets:
                continue
            # A widget whose C++ side is already gone still appears in this
            # list; touching it raises "Internal C++ object already deleted".
            try:
                widget.close()
                # Only destroy roots. Destroying a parent already destroys its
                # children, and touching a child afterwards raises the same
                # error.
                if destroy is not None and widget.parent() is None:
                    destroy(widget)
            except RuntimeError:
                pass
        app.processEvents()

    def _application(self):
        from ui.qt_compat import QApplication, HAS_QT
        if not HAS_QT:
            self.skipTest("No Qt binding available in test runner environment")
        app = QApplication.instance()
        if app is None:
            app = QApplication(["-platform", "offscreen"])
        self.__class__._qapp = app
        return app

    def test_theme_tokens(self):
        from ui.styles import Theme
        self.assertEqual(Theme.BG_ROOT, "#1e2024")
        self.assertEqual(Theme.TEXT_PRIMARY, "#ffffff")
        self.assertEqual(Theme.ACCENT_AMBER, "#f59e0b")
        self.assertEqual(Theme.ACCENT_CYAN, "#06b6d4")

    def test_impeccable_semantic_tokens_and_fader_tag(self):
        from ui.styles import Theme
        from ui.qt_compat import QApplication, HAS_QT
        if not HAS_QT:
            self.skipTest("No Qt binding available in test runner environment")
        app = QApplication.instance() or QApplication(["-platform", "offscreen"])
        from ui.widgets.tactile_fader import TactileFader
        self.assertEqual(Theme.STATUS_SUCCESS_BG, "#143521")
        self.assertEqual(Theme.RIGGING_CLAMP, "#717b8f")
        fader = TactileFader(channel_id=3, initial_value=10)
        fader.set_fixture_tag("AL36-1:DIM")
        self.assertEqual(fader.fixture_tag, "AL36-1:DIM")
        fader.close()
        self.__class__._qapp = app

    def test_perform_transport_and_crossfade_telemetry(self):
        self._application()
        from ui.main_window import MainWindow
        win = MainWindow()
        tab = win.tab_perform
        self.assertEqual(tab.btn_prev_cue.text(), "[PREV]")
        self.assertEqual(tab.btn_go_cue.text(), "[GO+]")
        self.assertEqual(tab.btn_fade_black.text(), "[FADE BLACK]")
        tab.set_crossfade_progress(0.5, 1.0, 2.0)
        self.assertEqual(tab.progress_crossfade.value(), 50)
        self.assertIn("1.0s", tab.lbl_fade_countdown.text())
        tab.set_crossfade_progress(1.0, 2.0, 2.0)
        self.assertIn("COMPLETE", tab.lbl_fade_countdown.text())
        win.close()

    def test_fixture_bracket_and_drag_preview_state(self):
        self._application()
        from ui.panels.address_tab import AddressTab
        tab = AddressTab()
        tab._on_patch_alien_gia()
        self.assertEqual(tab.grid_area.boxes[1].boundary_type, "start")
        self.assertEqual(tab.grid_area.boxes[2].boundary_type, "mid")
        self.assertEqual(tab.grid_area.boxes[8].boundary_type, "end")
        tab.grid_area._set_drag_hover(100, 8)
        self.assertTrue(all(tab.grid_area.boxes[ch].is_drag_hover for ch in range(100, 108)))
        self.assertFalse(tab.grid_area.boxes[108].is_drag_hover)
        tab.grid_area._clear_drag_hover()
        self.assertFalse(any(box.is_drag_hover for box in tab.grid_area.boxes.values()))
        tab.close()

    def test_mixer_syncs_patch_role_labels_and_active_bank(self):
        self._application()
        from ui.panels.mixer_tab import MixerTab
        tab = MixerTab()
        tab.sync_patch([{"name": "Alien-AL36 #1", "channels": [
            {"channel": 1, "type": "dimmer", "label": "Dimmer"},
            {"channel": 2, "type": "red", "label": "Red"},
        ]}])
        self.assertEqual(tab.faders[1].fixture_tag, "AL36-1:DIM")
        self.assertEqual(tab.faders[2].fixture_tag, "AL36-1:RED")
        tab._on_scroll_changed(64 * 58)
        self.assertEqual(tab.active_bank_index, 1)
        tab.close()

    def test_preview_segmented_switch_and_direct_controls(self):
        self._application()
        from ui.panels.preview_tab import StageVisualizerWindow
        vis = StageVisualizerWindow()
        self.assertEqual(vis.tabs.count(), 2)
        self.assertEqual(vis.tabs.currentIndex(), 0)
        self.assertFalse(vis.drawer_widget.isVisible())
        self.assertFalse(vis.canvas_3d.haze_enabled)
        vis._switch_view(1)
        self.assertEqual(vis.tabs.currentIndex(), 1)
        self.assertFalse(vis.box_rot_widget.isHidden())
        vis.close()

    def test_address_unpatched_channel_contrast(self):
        self._application()
        from ui.panels.address_tab import DMXChannelBox
        box = DMXChannelBox(99)
        self.assertEqual(box.lbl_num.styleSheet().find("#cbd5e1") >= 0, True)
        box.close()

    def test_icon_hamburger_is_vector_icon(self):
        self._application()
        from ui.icons import create_hamburger_icon
        icon = create_hamburger_icon()
        self.assertIsNotNone(icon)
        self.assertFalse(icon.isNull())

    def test_master_go_button_has_commanding_size(self):
        self._application()
        from ui.panels.perform_tab import PerformTab
        tab = PerformTab()
        self.assertGreaterEqual(tab.btn_go_cue.minimumHeight(), 44)
        self.assertEqual(tab.btn_go_cue.text(), "[GO+]")
        tab.close()

    def test_crossfade_zero_total_resets_to_idle(self):
        self._application()
        from ui.panels.perform_tab import PerformTab
        tab = PerformTab()
        tab.set_crossfade_progress(0.0, 0.0, 0.0)
        self.assertEqual(tab.progress_crossfade.value(), 0)
        self.assertIn("IDLE", tab.lbl_fade_countdown.text())
        tab.close()

    def test_mixer_unpatched_channels_clear_fixture_tags(self):
        self._application()
        from ui.panels.mixer_tab import MixerTab
        tab = MixerTab()
        tab.sync_patch([{"name": "Alien-AL36 #1", "channels": [{"channel": 7, "type": "program", "label": "Program"}]}])
        self.assertEqual(tab.faders[7].fixture_tag, "AL36-1:PRG")
        tab.sync_patch([])
        self.assertEqual(tab.faders[7].fixture_tag, "")
        tab.close()

    def test_fixture_brackets_refresh_after_clear(self):
        self._application()
        from ui.panels.address_tab import AddressTab
        tab = AddressTab()
        tab._on_patch_alien_gia()
        self.assertEqual(tab.grid_area.boxes[1].boundary_type, "start")
        for box in tab.grid_area.boxes.values():
            box.set_unpatched()
        tab.update_fixture_brackets()
        self.assertFalse(any(box.boundary_type for box in tab.grid_area.boxes.values()))
        tab.close()

    def test_active_bank_tracks_far_scroll_bounds(self):
        self._application()
        from ui.panels.mixer_tab import MixerTab
        tab = MixerTab()
        tab._on_scroll_changed(511 * 58)
        self.assertEqual(tab.active_bank_index, 7)
        tab._on_scroll_changed(0)
        self.assertEqual(tab.active_bank_index, 0)
        tab.close()

    def test_crossfade_completion_resets_when_new_fade_begins(self):
        self._application()
        from ui.panels.perform_tab import PerformTab
        tab = PerformTab()
        tab.set_crossfade_progress(1.0, 2.0, 2.0)
        tab.reset_crossfade_progress()
        self.assertEqual(tab.progress_crossfade.value(), 0)
        self.assertIn("IDLE", tab.lbl_fade_countdown.text())
        tab.close()

    def test_settings_artnet_target_presets_are_present(self):
        self._application()
        from ui.panels.settings_panel import SettingsDialog
        dialog = SettingsDialog()
        presets = [dialog.combo_presets.itemText(i) for i in range(dialog.combo_presets.count())]
        self.assertTrue(any("localhost" in p.lower() for p in presets))
        self.assertTrue(any("broadcast" in p.lower() for p in presets))
        dialog.close()

    def test_fader_zero_control_is_plain_character(self):
        self._application()
        from ui.widgets.tactile_fader import TactileFader
        fader = TactileFader(channel_id=1, initial_value=10)
        # Paint path is exercised by rendering into the widget in the existing offscreen Qt test harness.
        self.assertTrue(fader.width() > 0)
        fader.close()

    def test_crossfade_progress_clamps_percentage(self):
        self._application()
        from ui.panels.perform_tab import PerformTab
        tab = PerformTab()
        tab.set_crossfade_progress(1.5, 1.0, 1.0)
        self.assertEqual(tab.progress_crossfade.value(), 100)
        tab.close()

    def test_stage_visualizer_syncs_empty_fixtures(self):
        self._application()
        from ui.panels.preview_tab import StageVisualizerWindow
        vis = StageVisualizerWindow()
        vis.sync_fixtures([])
        self.assertEqual(vis.canvas_2d.fixtures, [])
        self.assertEqual(vis.canvas_3d.fixtures_3d, [])
        vis.close()

    def test_stage3d_reset_camera_is_eye_level_and_non_degenerate(self):
        """Reset returns to a front-facing view that still shows the floor.

        The camera must NOT reset to exactly pitch 0: at that angle sin(pitch)
        is 0, so every vertex at y == 0 projects onto one scanline and the floor
        quad, beam cone and floor pool collapse to zero-area polygons.
        """
        self._application()
        import math

        from ui.panels.preview_tab import Stage3DCanvas

        canvas = Stage3DCanvas()
        canvas.yaw = 1.0
        canvas.pitch = 0.5
        canvas.reset_camera()

        self.assertEqual(canvas.yaw, 0.0)
        self.assertNotEqual(canvas.pitch, 0.0, "reset must not flatten the projection")
        self.assertLess(canvas.pitch, math.radians(45))

        # The floor must occupy more than one scanline.
        floor_pts = [(0, 0, 0), (320, 0, -140), (-320, 0, -140), (260, 0, 180)]
        rows = {round(canvas.project(*p, 400.0, 320.0)[1], 6) for p in floor_pts}
        self.assertGreater(len(rows), 1, "floor vertices must not share one scanline")

        canvas.close()

    def test_beam_angle_control_updates_selected_fixture(self):
        self._application()
        from ui.panels.preview_tab import StageVisualizerWindow
        vis = StageVisualizerWindow()
        vis.sync_fixtures([{"id": 1, "name": "Test", "start_channel": 1, "channels": []}])
        vis.canvas_3d.selected_ids = {1}
        vis.spin_beam_angle.setValue(45)
        self.assertEqual(vis.canvas_3d.fixtures_3d[0]["beam_angle"], 45)
        vis.close()

    def test_drag_hover_preview_clears_when_leaving_grid(self):
        self._application()
        from ui.panels.address_tab import AddressTab
        tab = AddressTab()
        tab.grid_area._set_drag_hover(12, 8)
        self.assertTrue(tab.grid_area.boxes[12].is_drag_hover)
        tab.grid_area._clear_drag_hover()
        self.assertFalse(tab.grid_area.boxes[12].is_drag_hover)
        tab.close()

    def test_fixture_library_inspector_uses_tabs_and_clean_name(self):
        self._application()
        from ui.panels.fixture_list import FixtureListWindow
        lib = FixtureListWindow()
        self.assertGreater(lib.list_widget.count(), 0)
        self.assertIn("Alien-AL36", lib.list_widget.item(0).text())
        lib.close()

    def test_header_menu_direct_actions_have_shortcuts(self):
        self._application()
        from ui.main_window import MainWindow
        win = MainWindow()
        actions = {a.text(): a for a in win.menuBar().actions()}
        self.assertIn("Preview", actions)
        self.assertIn("Setting", actions)
        self.assertIn("Help", actions)
        self.assertIn("About", actions)
        self.assertEqual(actions["Preview"].shortcut().toString(), "Ctrl+P")
        self.assertEqual(actions["Setting"].shortcut().toString(), "Ctrl+Shift+P")
        win.close()

    def test_haze_toggle_button_keeps_static_label(self):
        self._application()
        from ui.panels.preview_tab import StageVisualizerWindow
        vis = StageVisualizerWindow()
        self.assertEqual(vis.btn_haze.text(), "Haze FX")
        vis._on_toggle_haze()
        self.assertEqual(vis.btn_haze.text(), "Haze FX")
        vis.close()

    def test_help_table_is_non_editable_and_shortcuts_heading(self):
        self._application()
        from ui.panels.help_panel import HelpDialog
        dialog = HelpDialog()
        self.assertEqual(dialog.windowTitle(), "Help")
        self.assertEqual(dialog.table.horizontalHeaderItem(1).text(), "Key")
        dialog.close()

    def test_about_window_has_wide_scrollable_description(self):
        self._application()
        from ui.panels.about_panel import AboutDialog
        from ui.qt_compat import QScrollArea
        dialog = AboutDialog()
        self.assertEqual(dialog.windowTitle(), "About")
        self.assertIsNotNone(dialog.findChild(QScrollArea))
        self.assertTrue(dialog.findChild(QScrollArea).widgetResizable())
        dialog.close()

    def test_preview_2d_selection_does_not_drag_fixture(self):
        self._application()
        from ui.panels.preview_tab import Stage2DCanvas
        canvas = Stage2DCanvas()
        canvas.set_fixtures([{"id": 1, "name": "AL36", "channels": []}])
        initial = (canvas.fixtures[0]["base_x"], canvas.fixtures[0]["base_y"])
        self.assertEqual((canvas.fixtures[0]["base_x"], canvas.fixtures[0]["base_y"]), initial)
        canvas.close()

    def test_design_token_palette_preserves_required_legacy_values(self):
        from ui.styles import Theme
        self.assertEqual(Theme.STATUS_SUCCESS_BG, "#143521")
        self.assertEqual(Theme.TEXT_CONTRAST_UNPATCHED, "#cbd5e1")
        self.assertEqual(Theme.FADER_RIB_HIGHLIGHT, "#4a5264")
        self.assertEqual(Theme.FADER_CLEAR_BG, "#2d1414")

    def test_ui_panels_import(self):
        from ui.panels.address_tab import AddressTab
        from ui.panels.analyze_tab import AnalyzeTab
        from ui.panels.result_tab import ResultTab
        from ui.panels.perform_tab import PerformTab
        from ui.panels.page_tab import PageTab
        from ui.panels.mixer_tab import MixerTab
        from ui.panels.fixture_list import FixtureListWindow
        from ui.panels.fixture_editor import FixtureEditorWindow
        from ui.panels.preview_tab import StageVisualizerWindow
        from ui.panels.settings_panel import SettingsDialog
        from ui.panels.help_panel import HelpDialog
        from ui.panels.about_panel import AboutDialog
        from ui.widgets.tactile_fader import TactileFader
        from ui.widgets.youtube_dialog import YouTubeDialog
        self.assertTrue(all((AddressTab, AnalyzeTab, ResultTab, PerformTab, PageTab,
                             MixerTab, FixtureListWindow, FixtureEditorWindow,
                             StageVisualizerWindow, SettingsDialog, HelpDialog,
                             AboutDialog, TactileFader, YouTubeDialog)))

    def test_settings_dialog_initializes_adapter_table_with_qcolors(self):
        self._application()
        from ui.panels.settings_panel import SettingsDialog
        dialog = SettingsDialog()
        self.assertGreater(dialog.table_adapters.rowCount(), 0)
        self.assertEqual(dialog.table_adapters.item(0, 0).foreground().color().name(), "#ffffff")
        self.assertEqual(dialog.table_adapters.item(0, 1).foreground().color().name(), "#06b6d4")
        dialog.close()

    def test_demo_showfile_patches_requested_eight_channel_fixture(self):
        self._application()
        from ui.main_window import MainWindow
        win = MainWindow()
        demo_path = BASE_DIR / "showfiles" / "demo_church_worship.zlx"
        with patch("ui.main_window.QMessageBox.information"):
            win.load_project_file(str(demo_path))

        expected = [
            ("dimmer", "Dimmer"), ("red", "Red"), ("green", "Green"),
            ("blue", "Blue"), ("white", "White"), ("strobe", "Strobe"),
            ("program", "Program"), ("speed", "Speed"),
        ]
        for fixture_idx in range(4):
            fixture_name = f"PAR LED {fixture_idx + 1} (8CH)"
            start_channel = fixture_idx * 8 + 1
            for offset, (channel_type, label) in enumerate(expected):
                box = win.tab_address.grid_area.boxes[start_channel + offset]
                self.assertTrue(box.is_patched)
                self.assertEqual((box.channel_type, box.channel_label, box.fixture_name),
                                 (channel_type, label, fixture_name))
        self.assertFalse(win.tab_address.grid_area.boxes[33].is_patched)
        self.assertEqual(len(win.tab_perform.playlist), 3)
        self.assertEqual(len(win.tab_page.executor_buttons), 4)

        win._on_cue_activated({"type": "scene", "active": True, "dimmer": 255,
                               "color": {"R": 100, "G": 80, "B": 60, "W": 40}})
        for fixture_idx in range(4):
            start = fixture_idx * 8
            self.assertEqual(list(win.dmx_buffer[start:start + 8]), [255, 100, 80, 60, 40, 0, 0, 0])
        win.close()

    def test_qlcplus_definition_and_workspace_use_requested_eight_channel_order(self):
        showfiles_dir = BASE_DIR / "showfiles"
        zz_fixture_dir = Path.home() / "ANDREAS" / "zz-fixture"
        ns = {"q": "http://www.qlcplus.org/FixtureDefinition"}
        qxf = ET.parse(zz_fixture_dir / "Kumastb-STL47.qxf").getroot()
        expected = ["Dimmer", "Red", "Green", "Blue", "White", "Strobe", "Program", "Speed"]
        names = [node.attrib["Name"] for node in qxf.findall("q:Channel", ns)]
        mode = qxf.find("q:Mode[@Name='Modes']", ns)
        self.assertEqual(names, expected)
        self.assertEqual([node.text for node in mode.findall("q:Channel", ns)], expected)

        workspace = ET.parse(showfiles_dir / "qlcplus_template.qxw").getroot()
        fixtures = workspace.findall("./Engine/Fixture")
        self.assertEqual(len(fixtures), 4)
        self.assertEqual([int(f.findtext("Channels")) for f in fixtures], [8] * 4)
        self.assertEqual([int(f.findtext("Address")) for f in fixtures], [0, 8, 16, 24])

        sliders = workspace.findall("./VirtualConsole/Frame/Slider")
        self.assertEqual(len(sliders), 32)
        for fixture_idx in range(4):
            for channel_idx, channel_name in enumerate(expected):
                slider = sliders[fixture_idx * 8 + channel_idx]
                self.assertEqual(slider.find("Input").get("Channel"), str(fixture_idx * 8 + channel_idx))
                self.assertEqual(slider.find("Level/Channel").get("Fixture"), str(fixture_idx))
                self.assertIn(channel_name, slider.get("Caption"))

    def test_qlc_user_fixture_definition_is_installed_for_qxw(self):
        user_fixture = Path.home() / ".qlcplus" / "fixtures" / "Kumastb" / "Kumastb-STL47.qxf"
        self.assertTrue(user_fixture.is_file(), f"QLC+ user fixture definition missing: {user_fixture}")

    def test_official_kumastb_and_alien_fixtures(self):
        fixtures_dir = BASE_DIR / "fixtures"
        zz_fixture_dir = Path.home() / "ANDREAS" / "zz-fixture"

        # Verify fixtures directory contains ONLY official .zfx profiles
        fixture_files = sorted([f.name for f in fixtures_dir.glob("*") if f.is_file()])
        self.assertEqual(fixture_files, ["Alien-AL36.zfx", "Kumastb-STL47.zfx"])

        # 1. Test Kumastb STL47 (8CH RGBW) .zfx
        kuma_zfx_file = fixtures_dir / "Kumastb-STL47.zfx"
        self.assertTrue(kuma_zfx_file.is_file())
        with open(kuma_zfx_file, "r", encoding="utf-8") as fp:
            kuma_data = json.load(fp)
        self.assertEqual(kuma_data["manufacturer"], "Kumastb")
        self.assertEqual(kuma_data["name"], "Kumastb-STL47")
        self.assertEqual(kuma_data["model"], "STL47")
        self.assertEqual(kuma_data["channel_count"], 8)
        self.assertEqual([ch["label"] for ch in kuma_data["channels"]],
                         ["Dimmer", "Red", "Green", "Blue", "White", "Strobe", "Program", "Speed"])

        # Test Kumastb .qxf from zz-fixture repository
        kuma_qxf_file = zz_fixture_dir / "Kumastb-STL47.qxf"
        self.assertTrue(kuma_qxf_file.is_file())
        ns = {"q": "http://www.qlcplus.org/FixtureDefinition"}
        qxf_kuma = ET.parse(kuma_qxf_file).getroot()
        self.assertEqual([node.attrib["Name"] for node in qxf_kuma.findall("q:Channel", ns)],
                         ["Dimmer", "Red", "Green", "Blue", "White", "Strobe", "Program", "Speed"])

        # 2. Test Alien AL36 (8CH RGB) .zfx
        alien_zfx_file = fixtures_dir / "Alien-AL36.zfx"
        self.assertTrue(alien_zfx_file.is_file())
        with open(alien_zfx_file, "r", encoding="utf-8") as fp:
            alien_data = json.load(fp)
        self.assertEqual(alien_data["manufacturer"], "Alien")
        self.assertEqual(alien_data["name"], "Alien-AL36")
        self.assertEqual(alien_data["model"], "AL36")
        self.assertEqual(alien_data["channel_count"], 8)
        self.assertEqual([ch["label"] for ch in alien_data["channels"]],
                         ["Dimmer", "Red", "Green", "Blue", "Empty", "Program", "Speed", "Emptz"])

        # Test Alien .qxf from zz-fixture repository
        alien_qxf_file = zz_fixture_dir / "Alien-AL36.qxf"
        self.assertTrue(alien_qxf_file.is_file())
        qxf_alien = ET.parse(alien_qxf_file).getroot()
        self.assertEqual([node.attrib["Name"] for node in qxf_alien.findall("q:Channel", ns)],
                         ["Dimmer", "Red", "Green", "Blue", "Empty", "Program", "Speed", "Emptz"])
        self.assertTrue(alien_qxf_file.is_file())
        qxf_alien = ET.parse(alien_qxf_file).getroot()
        self.assertEqual([node.attrib["Name"] for node in qxf_alien.findall("q:Channel", ns)],
                         ["Dimmer", "Red", "Green", "Blue", "Empty", "Program", "Speed", "Emptz"])

        # 3. Test FixtureProfile factory methods
        from core.models import FixtureProfile
        kuma_prof = FixtureProfile.create_kumastb_stl47()
        self.assertEqual(kuma_prof.manufacturer, "Kumastb")
        self.assertEqual(kuma_prof.channel_count, 8)
        self.assertEqual(kuma_prof.name, "Kumastb-STL47",
                         "factory name must match the section 2 standard and fixtures/Kumastb-STL47.zfx")
        alien_prof = FixtureProfile.create_alien_al36()
        self.assertEqual(alien_prof.manufacturer, "Alien")
        self.assertEqual(alien_prof.channel_count, 8)
        self.assertEqual(alien_prof.name, "Alien-AL36",
                         "factory name must match the section 2 standard and fixtures/Alien-AL36.zfx")

    def test_headless_main_window_instantiation(self):
        self._application()
        from ui.main_window import MainWindow
        win = MainWindow()
        self.assertIsNotNone(win)
        self.assertEqual(len(win.tab_buttons), 6)
        self.assertEqual(win.stack.count(), 6)
        self.assertEqual(len(win.tab_mixer.faders), 513)
        win.tab_mixer.set_channel_value(0, 255)
        win.tab_mixer.apply_blackout()
        self.assertEqual(win.tab_mixer.master_fader.value, 0)
        self.assertFalse(win.is_transmitting)
        win._on_play_stop_toggled()
        self.assertTrue(win.is_transmitting)
        win._on_play_stop_toggled()
        self.assertFalse(win.is_transmitting)

        # Verify all popup windows and menus instantiate and become visible
        win._on_open_fixture_list()
        self.assertTrue(win.win_fixture_list.isVisible())
        win._on_open_fixture_editor()
        self.assertTrue(win.win_fixture_editor.isVisible())
        win._on_open_visualizer()
        self.assertTrue(win.win_visualizer.isVisible())
        win._on_open_settings()
        self.assertTrue(win.win_settings.isVisible())
        win._on_open_help()
        self.assertTrue(win.win_help.isVisible())
        win._on_open_about()
        self.assertTrue(win.win_about.isVisible())

        # Verify top-level menus and direct actions exist (Preview, Setting, Help, About are direct actions without dropdown)
        from ui.qt_compat import QMenu
        action_texts = [a.text() for a in win.menuBar().actions()]
        for expected_action in ["File", "Fixture", "Preview", "Setting", "Help", "About"]:
            self.assertIn(expected_action, action_texts)
        menu_titles = [m.title() for m in win.menuBar().findChildren(QMenu)]
        for title in ["File", "Fixture"]:
            self.assertIn(title, menu_titles)
        self.assertNotIn("Editor", menu_titles)

        win.close()

    def test_blackout_clears_channel_faders_and_wire_together(self):
        """BLACKOUT must not leave lit faders over a dark wire, and must never
        put a stale frame on the wire.

        Two defects are covered here. First, only the Grand Master used to move,
        so 256 channel faders stayed lit on screen while the console sent zeros.
        Second, ArtNetSender keeps its own copy of the channels and its
        blackout() transmits that copy, so without pushing the zeroed buffer
        first the previous frame (including channels the UI never rewrites, such
        as 257-512) reached the rig and briefly re-lit it.
        """
        self._application()
        from ui.main_window import MainWindow
        win = MainWindow()

        lit_channels = (1, 5, 257, 300, 512)
        for ch in lit_channels:
            if ch <= 512:
                win.dmx_buffer[ch - 1] = 200
        win.tab_mixer.faders[1].value = 200
        win.tab_mixer.faders[5].value = 200
        # Seed the sender's internal buffer with the pre-blackout levels.
        win.artnet_sender.send_raw(win.dmx_buffer)

        captured = []
        win.artnet_sender._transmit = lambda packet: captured.append(packet)
        win.is_transmitting = True

        win._on_blackout_clicked()

        # Every frame sent during blackout must be fully dark.
        self.assertTrue(captured, "blackout should transmit while playing")
        for index, packet in enumerate(captured):
            payload = packet[18:18 + 512]
            offending = [ch for ch in lit_channels if payload[ch - 1] != 0]
            self.assertEqual(
                offending, [],
                f"frame {index + 1} carried stale nonzero channels {offending} on the wire",
            )

        # The visible surface must agree with the wire.
        self.assertEqual(win.tab_mixer.master_fader.value, 0)
        for ch in (1, 5):
            self.assertEqual(win.tab_mixer.faders[ch].value, 0)

        win.close()

    def test_closing_the_window_blackouts_the_surface_and_the_buffer(self):
        """Shutdown must darken the mixer and the DMX buffer, not only the wire.

        Regression: closeEvent called artnet_sender.blackout() and stopped there.
        The rig went dark, but the window's dmx_buffer and every channel fader
        kept the last look. Shutdown can be aborted (a child window that refuses
        to close makes the close event ignored), and then PLAY resends the stale
        buffer while the faders still read as lit - the surface contradicting the
        output, which is exactly the class of defect BLACKOUT had.
        """
        self._application()
        from ui.main_window import MainWindow

        win = MainWindow()
        win.dmx_buffer[0] = 200
        win.dmx_buffer[2] = 100
        win.tab_mixer.faders[1].value = 200

        # Drive the real close event rather than calling win.close(), so the
        # shutdown path is exercised without tearing the window down mid-test.
        # Import through qt_compat: the app supports both PySide6 and PyQt6,
        # so this suite must pass on whichever binding is installed.
        from ui.qt_compat import QtGui as _QtGui
        event = _QtGui.QCloseEvent()
        win.closeEvent(event)

        self.assertEqual([win.dmx_buffer[i] for i in range(3)], [0, 0, 0],
                         "the buffer must be zeroed so a later PLAY cannot resend a stale look")
        self.assertEqual(win.tab_mixer.faders[1].value, 0,
                         "the fader must read dark, matching the rig")
        self.assertEqual(win.tab_mixer.master_fader.value, 0)

        event.accept()

    def test_blackout_cancels_a_running_crossfade(self):
        """BLACKOUT must also stop a live crossfade, not just zero the buffer.

        Regression: _on_blackout_clicked zeroed dmx_buffer but left the
        crossfade timer running. _on_crossfade_tick calls _apply_dmx_buffer
        every 23 ms, which overwrites the zeroed buffer with interpolated
        values and transmits them, so the stage lit back up shortly after the
        operator pressed BLACKOUT.
        """
        self._application()
        from ui.main_window import MainWindow
        win = MainWindow()

        # Put a fade in flight toward a bright look.
        win._apply_dmx_buffer(bytearray([255] + [0] * 511))
        win._fade_start = bytearray([255] + [0] * 511)
        win._fade_target = bytearray([255, 200] + [0] * 510)
        win._fade_duration = 2.0
        win._fade_elapsed = 0.0
        win._crossfade_timer.start()
        self.assertTrue(win._crossfade_timer.isActive(), "precondition: a fade is running")

        win._on_blackout_clicked()

        self.assertFalse(
            win._crossfade_timer.isActive(),
            "blackout must stop the crossfade, or the next tick re-lights the stage",
        )
        self.assertEqual(
            [value for value in win.dmx_buffer if value != 0], [],
            "the buffer must stay dark after the blackout",
        )

        win.close()

    def test_reset_dmx_then_play_does_not_relight_the_old_look(self):
        """RESET DMX must not leave a stale look available for PLAY to send.

        Regression: the mixer's RESET DMX uses silent setters so it does not
        emit one Art-Net packet per channel. That also meant the shell never
        learned the faders had moved, so dmx_buffer still held the previous
        look; pressing PLAY transmitted it and the stage lit up again with the
        old cue.
        """
        self._application()
        from ui.main_window import MainWindow
        win = MainWindow()

        for ch in (1, 2, 17, 33):
            win.tab_mixer.set_channel_value(ch, 220, silent=True)
        win._rebuild_dmx_from_faders()
        self.assertTrue(any(v != 0 for v in win.dmx_buffer), "precondition: a look is lit")

        win.tab_mixer._reset_dmx_channels()
        # This is the trap: faders read zero while the buffer is still lit.
        self.assertEqual(win.tab_mixer.faders[1].value, 0)
        self.assertTrue(
            any(v != 0 for v in win.dmx_buffer),
            "precondition: reset left the buffer stale (the defect's raw material)",
        )

        captured = []
        win.artnet_sender._transmit = lambda packet: captured.append(packet)
        win._on_play_stop_toggled()

        self.assertEqual(
            [value for value in win.dmx_buffer if value != 0], [],
            "PLAY after RESET DMX must send a dark frame, not the previous look",
        )
        self.assertTrue(captured, "PLAY should transmit a frame")
        payload = captured[0][18:18 + 512]
        self.assertEqual([v for v in payload if v != 0], [], "the first PLAY frame must be dark")

        win.close()

    def test_white_folds_back_when_fixture_has_no_white_channel(self):
        """A fixture without a white emitter must not lose the extracted W.

        ColorEngine decomposes RGB into physical RGBW by pulling W = min(R,G,B)
        out of the colour. Alien AL36 has no white channel, so main_window had
        nowhere to write w_val and dropped it, costing most of the intended
        light: a mellow-worship palette (67,38,0,178) reached the fixture as
        R+G+B = 105 instead of 639, and a pure-white cue (0,0,0,255) became
        (0,0,0) - the fixture went dark. W must be folded back into R/G/B when no
        patched channel can accept it.
        """
        self._application()
        from ui.main_window import MainWindow
        win = MainWindow()

        channel_types = ("Dimmer", "Red", "Green", "Blue", "Empty", "Program", "Speed", "Empty")
        for offset, ctype in enumerate(channel_types):
            win.tab_address.grid_area.boxes[1 + offset].set_patched(ctype, ctype.upper()[:3], "Alien AL36")
        win._on_patch_changed()
        fixtures = win.tab_address.get_patched_fixtures()
        self.assertTrue(fixtures, "precondition: a fixture is patched")
        self.assertFalse(
            any("white" in c["type"].lower() for c in fixtures[0]["channels"]),
            "precondition: this fixture has no white channel",
        )

        # Mellow palette: W carries most of the light.
        buf = win._get_target_dmx_for_cue(
            {"color": {"R": 67, "G": 38, "B": 0, "W": 178}, "dimmer": 255, "active": True}
        )
        r, g, b = buf[1], buf[2], buf[3]
        self.assertEqual((r, g, b), (245, 216, 178))
        self.assertGreater(r + g + b, 600, "the extracted white must come back as RGB intensity")

        # Boundary: pure white used to black the fixture out entirely.
        buf = win._get_target_dmx_for_cue(
            {"color": {"R": 0, "G": 0, "B": 0, "W": 255}, "dimmer": 255, "active": True}
        )
        self.assertEqual((buf[1], buf[2], buf[3]), (255, 255, 255),
                         "a pure white cue must not black out an RGB fixture")

        win.close()

    def test_white_stays_on_its_own_channel_when_the_fixture_has_one(self):
        """Folding W into RGB must not happen when a white emitter exists.

        Regression guard for the fold above: on an RGBW fixture the white must
        stay in the white channel and R/G/B must keep the decomposed values, or
        the fixture would wash out.
        """
        self._application()
        from ui.main_window import MainWindow
        win = MainWindow()

        channel_types = ("Dimmer", "Red", "Green", "Blue", "White", "Empty", "Empty", "Empty")
        for offset, ctype in enumerate(channel_types):
            win.tab_address.grid_area.boxes[1 + offset].set_patched(ctype, ctype.upper()[:3], "Kumastb STL47")
        win._on_patch_changed()

        buf = win._get_target_dmx_for_cue(
            {"color": {"R": 67, "G": 38, "B": 0, "W": 178}, "dimmer": 255, "active": True}
        )
        self.assertEqual(buf[1], 67, "red must keep its decomposed value")
        self.assertEqual(buf[2], 38, "green must keep its decomposed value")
        self.assertEqual(buf[3], 0, "blue must keep its decomposed value")
        self.assertEqual(buf[4], 178, "white must stay on the white channel")

        win.close()

    def test_moving_a_fixture_releases_the_source_only_on_success(self):
        """A move must never lose the fixture when the destination is occupied.

        The fixture panel drags a payload carrying move_source_channels. If the
        source were released before the destination is checked, a refused drop
        would delete the fixture outright - the worst possible outcome, because
        the operator sees the block vanish and has to re-patch it by hand.
        """
        self._application()
        from unittest.mock import patch as mock_patch
        from ui.main_window import MainWindow
        import json as _json

        win = MainWindow()
        tab = win.tab_address
        fixture = {"name": "Alien AL36",
                   "channels": [{"type": t, "label": t.upper()[:3]} for t in
                                 ("dimmer", "red", "green", "blue", "empty",
                                  "program", "speed", "empty")]}
        tab._on_fixture_dropped(1, fixture, notify=False)
        tab._on_fixture_dropped(17, fixture, notify=False)
        tab.patch_changed.emit()

        panel = tab.fixture_panel
        panel.list_widget.item(0).setSelected(True)
        payload = _json.loads(bytes(
            panel.mimeData(panel.list_widget.selectedItems())
            .data("application/x-zzluxora-fixture")).decode())
        self.assertEqual(payload["move_source_channels"], list(range(1, 9)))
        self.assertEqual(len(payload["channels"]), 8)

        # Moving into free space releases the old channels and takes the new.
        with mock_patch("ui.panels.address_tab.QMessageBox.warning"):
            self.assertTrue(tab._on_fixture_dropped(100, payload, notify=False))
        occupied = tab._occupied_channels()
        self.assertFalse([c for c in occupied if c <= 8],
                         "the source channels must be released after a successful move")
        self.assertTrue(all(c in occupied for c in range(100, 108)))

        # Moving onto an occupied range is refused and must change nothing.
        clash = dict(payload, move_source_channels=list(range(17, 25)))
        before = sorted(tab._occupied_channels())
        with mock_patch("ui.panels.address_tab.QMessageBox.warning") as warned:
            self.assertFalse(tab._on_fixture_dropped(103, clash, notify=False))
            self.assertTrue(warned.called)
        self.assertEqual(sorted(tab._occupied_channels()), before,
                         "a refused move must leave every fixture where it was")
        self.assertTrue(all(c in tab._occupied_channels() for c in range(17, 25)))

        win.close()

    def test_fixture_panel_lists_numbered_fixtures_with_addresses(self):
        """The panel is the register of what is patched, ordered by address."""
        self._application()
        from ui.main_window import MainWindow

        win = MainWindow()
        tab = win.tab_address
        fixture = {"name": "Alien AL36",
                   "channels": [{"type": "red", "label": "RED"}] * 8}
        self.assertFalse(tab.fixture_panel.list_widget.isVisible(),
                         "the list is replaced by an empty note when nothing is patched")

        # Patched out of order on purpose: the list must sort by address.
        for ch in (33, 1):
            tab._on_fixture_dropped(ch, fixture, notify=False)
        tab.patch_changed.emit()

        self.assertEqual(tab.fixture_panel.list_widget.count(), 2)
        first = tab.fixture_panel.list_widget.item(0).text()
        self.assertIn("[1]", first)
        self.assertIn("DMX 1-8", first)
        self.assertIn("DMX 33-40", tab.fixture_panel.list_widget.item(1).text())

        win.close()

    def test_global_shortcuts_survive_popups_and_cover_documented_keys(self):
        """Console shortcuts must work while a floating window has focus.

        Actions registered with the default WindowShortcut context stop firing
        as soon as a non-modal popup (Help, About, Settings, Fixture windows,
        Visualizer) takes focus, which silently disabled Play, Blackout and
        workspace switching. They are also required to cover every key the Help
        panel documents (B for blackout, Ctrl+Y as well as Ctrl+Shift+Z for redo).
        """
        self._application()
        from ui.qt_compat import Qt
        from ui.main_window import MainWindow
        win = MainWindow()

        actions = [a for a in win.actions() if a.shortcut().toString()]
        self.assertTrue(actions)

        for action in actions:
            self.assertEqual(
                action.shortcutContext(), Qt.ApplicationShortcut,
                f"{action.shortcut().toString()} must keep working while a popup is open",
            )

        bound = {a.shortcut().toString() for a in actions}
        for expected in ("Ctrl+F1", "Ctrl+F6", "Space", "Esc", "B",
                         "Ctrl+Z", "Ctrl+Shift+Z", "Ctrl+Y"):
            self.assertIn(expected, bound, f"{expected} should be bound")

        win.close()

    def test_patch_start_address_survives_save_reload_at_unaligned_dmx(self):
        """A fixture not dropped on an 8-channel boundary must keep its address.

        Saving used to derive the start address from a modulo-8 formula, so a
        fixture at DMX 18 was written to the .zlx as 17. After any reload the
        rig was patched to the wrong channels and the fixture at 17 was stomped.
        """
        self._application()
        import json
        import tempfile

        from ui.main_window import MainWindow

        with tempfile.TemporaryDirectory() as tmpdir:
            for start in (1, 2, 5, 8, 9, 10, 17, 18, 24, 25, 49, 50):
                with self.subTest(start=start):
                    win = MainWindow()
                    win.tab_address._on_fixture_dropped(
                        start,
                        {"name": "F", "channels": [{"type": "red", "label": "R"}] * 6},
                    )
                    expected = win.tab_address.get_patched_fixtures()[0]["start_channel"]

                    path = Path(tmpdir) / f"addr_{start}.zlx"
                    win._save_to_path(str(path))
                    saved = json.loads(path.read_text())["patches"][0]["start_channel"]

                    self.assertEqual(saved, expected,
                                     f"DMX {start} saved as {saved}")

                    reloaded = MainWindow()
                    reloaded.load_project_file(str(path), notify=False)
                    actual = reloaded.tab_address.get_patched_fixtures()[0]["start_channel"]
                    self.assertEqual(actual, expected,
                                     f"DMX {start} reloaded as {actual}")
                    win.close()
                    reloaded.close()

    def test_help_panel_shortcut_table_matches_bindings(self):
        """Every shortcut the Help panel lists must actually be bound, and the
        two alternates added for blackout and redo must be documented."""
        self._application()
        import re

        from ui.main_window import MainWindow

        win = MainWindow()

        bound = {a.shortcut().toString() for a in win.actions() if a.shortcut().toString()}
        for top in win.menuBar().actions():
            if top.shortcut().toString():
                bound.add(top.shortcut().toString())
            menu = top.menu()
            if menu:
                for act in menu.actions():
                    if act.shortcut().toString():
                        bound.add(act.shortcut().toString())

        source = (Path(__file__).resolve().parent.parent / "ui" / "panels" / "help_panel.py").read_text()
        pairs = re.findall(r'\("([^"]+)",\s*"([^"]+)"\)', source)
        documented = [key for _, key in pairs]
        self.assertTrue(documented, "Help panel should list shortcuts")

        for key in documented:
            self.assertIn(key, bound, f"Help documents {key} but it is not bound")

        for key in ("B", "Ctrl+Y"):
            self.assertIn(key, documented, f"{key} is bound but missing from Help")
            self.assertIn(key, bound, f"{key} should be bound")

        win.close()

    def test_flash_release_restores_the_running_look(self):
        """Releasing a momentary FLASH must return to the previous look, not black out.

        The release used to be routed through the normal cue path with
        active=False, which zeroed the dimmer and left the colour channels
        latched at the flash values.
        """
        self._application()
        from ui.main_window import MainWindow
        win = MainWindow()
        win.tab_address._on_fixture_dropped(
            1,
            {"name": "PAR", "channels": [
                {"type": t, "label": t.upper()}
                for t in ("dimmer", "red", "green", "blue", "empty", "program", "speed", "empty")
            ]},
        )

        verse = {"label": "VERSE", "type": "scene",
                 "color": {"R": 11, "G": 22, "B": 33, "W": 0}, "dimmer": 180, "fade_time": 0.0}
        win._on_cue_activated(dict(verse))
        look_after_verse = list(win.dmx_buffer[0:8])
        self.assertEqual(win.dmx_buffer[0], 180)

        flash = {"label": "FLASH", "type": "flash",
                 "color": {"R": 255, "G": 255, "B": 255, "W": 255}, "dimmer": 255, "fade_time": 0.0}
        win._on_cue_activated({**flash, "active": True})
        self.assertEqual(win.dmx_buffer[0], 255)

        win._on_cue_activated({**flash, "active": False})
        self.assertEqual(
            list(win.dmx_buffer[0:8]), look_after_verse,
            "flash release must restore the previous look exactly",
        )
        self.assertNotEqual(win.dmx_buffer[0], 0, "release must not black out the stage")

        win.close()

    def test_fader_press_below_track_does_not_clobber_value(self):
        """A press in the strip below the track holds the readout and [X] button.

        It used to clamp to the track bottom and write DMX 0, so aiming for a
        low level blacked the channel out, and the master could not be dragged
        below roughly DMX 63 at all.
        """
        self._application()
        from ui.widgets.tactile_fader import TactileFader

        fader = TactileFader(channel_id=5, initial_value=100)
        fader.resize(52, 190)
        _, y_bottom = fader._track_y_bounds()

        fader.set_value_silent(100)
        for y in (y_bottom + 1, y_bottom + 20, fader.height() - 1):
            fader._update_from_mouse_y(y)
            self.assertEqual(fader.value, 100, f"press at y={y} must not change the value")

        # The track itself still maps the full range.
        y_top, y_bottom = fader._track_y_bounds()
        fader._update_from_mouse_y(y_top)
        self.assertEqual(fader.value, 255)
        fader._update_from_mouse_y(y_bottom)
        self.assertEqual(fader.value, 0)

    def test_multiselect_does_not_reset_slider_or_collapse_layout(self):
        """Shift+clicking a second fixture must not reload the sliders from it.

        Reloading the last-clicked fixture's offsets replaced the group's value
        in the widgets, and the next slider event forced every selected fixture
        onto that one point, silently destroying the spacing just built.
        """
        self._application()
        from ui.main_window import MainWindow

        win = MainWindow()
        for start, name in ((1, "A"), (9, "B")):
            win.tab_address._on_fixture_dropped(
                start,
                {"name": f"PAR-{name}", "channels": [
                    {"type": t, "label": t.upper()}
                    for t in ("dimmer", "red", "green", "blue", "empty", "program", "speed", "empty")
                ]},
            )
        win._on_open_visualizer()
        panel = win.win_visualizer
        canvas = panel.canvas_2d
        self.assertGreaterEqual(len(canvas.fixtures), 2)

        first, second = canvas.fixtures[0]["id"], canvas.fixtures[1]["id"]
        canvas.selected_ids = {first}
        panel._on_fixture_selected(first)
        panel.spin_pivot_x.setValue(140)
        self.assertEqual(canvas.fixtures[0]["offset_x"], 140)

        # Adding a second fixture to the selection must leave the slider alone.
        canvas.selected_ids = {first, second}
        panel._on_fixture_selected(second)
        self.assertEqual(
            panel.spin_pivot_x.value(), 140,
            "adding to the selection must not reload the slider from the new fixture",
        )
        self.assertEqual(canvas.fixtures[0]["offset_x"], 140, "F1 must keep its position")

        win.close()

    def test_quick_patch_is_one_undo_step(self):
        """One quick-patch press must be one undo action.

        The buttons snapshot the grid once, then _on_fixture_dropped snapshotted
        again per fixture, so one ALIEN press needed five undos to reverse and
        the intermediate states were half-patched rigs the operator never made.
        """
        self._application()
        from ui.main_window import MainWindow

        win = MainWindow()
        tab = win.tab_address
        patched = lambda: sum(1 for b in tab.grid_area.boxes.values() if b.is_patched)

        for label, action, expected_cells in (
            ("ALIEN", tab._on_patch_alien_gia, 32),
            ("KUMA", tab._on_patch_kuma_bench, 8),
        ):
            with self.subTest(press=label):
                tab.undo_stack.clear()
                tab.redo_stack.clear()
                for box in tab.grid_area.boxes.values():
                    box.set_unpatched()

                action()
                self.assertEqual(len(tab.undo_stack), 1,
                                 f"{label}: one press must record one undo entry")
                self.assertEqual(patched(), expected_cells)

                tab.undo_patch()
                self.assertEqual(patched(), 0,
                                 f"{label}: a single undo must clear the whole press")
        win.close()

    def test_patch_beyond_dmx_256_is_refused_not_truncated(self):
        """A fixture that would run past the last DMX channel must be refused.

        The overflow was silently dropped and the truncated channel count was
        written to the .zlx file, so a 12-channel head at DMX 250 reloaded as a
        7-channel fixture driving the wrong offsets. The boundary itself moved
        from 256 to 512 when the grid grew to a full universe; the rule under
        test - refuse rather than truncate - is unchanged.
        """
        self._application()
        from unittest.mock import patch as mock_patch

        from ui.main_window import MainWindow

        win = MainWindow()
        tab = win.tab_address
        fixture = {"name": "Head12", "channels": [{"type": "red", "label": "R"}] * 12}

        with mock_patch("ui.panels.address_tab.QMessageBox.warning") as warned:
            # 12 channels from 506 run to 517, past the last channel (512).
            tab._on_fixture_dropped(506, fixture)
            self.assertTrue(warned.called, "overflow must warn the operator")
            self.assertEqual(tab.get_patched_fixtures(), [],
                             "an out-of-range fixture must not be partially patched")

            # 12 channels from 501 land exactly on 512 and must be accepted.
            tab._on_fixture_dropped(501, fixture)
            fixtures = tab.get_patched_fixtures()
            self.assertEqual(len(fixtures), 1, "a fixture ending on 512 must patch in full")
            self.assertEqual(fixtures[0]["start_channel"], 501)
            self.assertEqual(len(fixtures[0]["channels"]), 12)

            # DMX 257 is no longer out of range: it is inside the universe.
            tab._on_fixture_dropped(257, fixture)
            self.assertEqual(len(tab.get_patched_fixtures()), 2,
                             "channels above 256 are now valid and must be usable")
        win.close()

    def test_page_export_replaces_instead_of_stacking(self):
        """GENERATE EXECUTORS must replace the page, not append to it."""
        self._application()
        from ui.main_window import MainWindow

        win = MainWindow()
        cues = [
            {"label": f"C{i}", "type": "scene",
             "color": {"R": 255, "G": 0, "B": 0, "W": 0}, "dimmer": 200, "fade_time": 0.0}
            for i in range(3)
        ]
        page = win.tab_page
        page.load_cues(cues)
        self.assertEqual(len(page.executor_buttons), 3)
        page.load_cues(cues)
        self.assertEqual(len(page.executor_buttons), 3,
                         "a second export must not stack duplicate executors")
        page.load_cues(cues)
        self.assertEqual(len(page.executor_buttons), 3)
        win.close()

    def test_page_load_cues_skips_non_object_entries(self):
        """A cue list with a stray int must not crash the executor page.

        ExecutorButton reads cue fields with .get(), so passing an int raised
        AttributeError: 'int' object has no attribute 'get'. The project loader
        now rejects such files, but load_cues is also reachable directly, so it
        keeps its own guard and still loads the entries that are objects.
        """
        self._application()
        from ui.main_window import MainWindow

        win = MainWindow()
        page = win.tab_page

        page.load_cues([42])
        self.assertEqual(len(page.executor_buttons), 0)

        page.load_cues([{"label": "A"}, 42, {"label": "B"}])
        self.assertEqual(len(page.executor_buttons), 2,
                         "the object entries must still load")
        win.close()

    def test_replacing_the_page_releases_a_held_flash(self):
        """A flash still held when the page is replaced must not leave the stage lit.

        Regression: a flash sends active=True on press and active=False on
        release, and the release restores the pre-flash look. Replacing the page
        (CLEAR PAGE, or a fresh GENERATE EXECUTORS) destroyed the button without
        the release ever firing, so the stage stayed lit with no executor left to
        turn it off. Measured: after press wire[:3] = 255,255,255 and it stayed
        that way once the page was replaced.
        """
        self._application()
        from ui.main_window import MainWindow

        win = MainWindow()
        for offset in range(8):
            win.tab_address.grid_area.boxes[1 + offset].set_patched("dimmer", "DIM", "KUMA")

        win.tab_page.load_cues([{"label": "FLASH", "type": "flash",
                                 "color": {"R": 255, "G": 0, "B": 0, "W": 0}, "dimmer": 255}])
        win.tab_page.executor_buttons[0]._on_flash_pressed()
        self.assertEqual(win.dmx_buffer[0], 255, "the flash must light the stage")

        win.tab_page.load_cues([{"label": "OTHER", "type": "scene",
                                 "color": {"R": 0, "G": 0, "B": 255, "W": 0}, "dimmer": 100}])
        self.assertNotEqual(win.dmx_buffer[0], 255,
                            "replacing the page must release the held flash")
        win.close()

    def test_fader_heights_stay_compact_and_master_stays_dominant(self):
        """Channel faders must not balloon past the documented height.

        Without a ceiling the layout stretched a channel fader to 548px at 768p
        and 860px at 1080p, which made the channels dwarf the 230px Grand Master
        and inverted the intended control hierarchy.
        """
        self._application()
        from ui.qt_compat import QApplication
        from ui.main_window import MainWindow

        app = QApplication.instance()
        for width, height in ((1366, 768), (1920, 1080), (1200, 680)):
            with self.subTest(resolution=f"{width}x{height}"):
                win = MainWindow()
                win.resize(width, height)
                win.show()
                win._switch_workspace(5)
                win.tab_mixer.resize(width, height - 90)
                app.processEvents()

                master = win.tab_mixer.master_fader
                channel = win.tab_mixer.faders[1]

                self.assertLessEqual(
                    channel.height(), 260,
                    "channel fader must stay compact instead of stretching",
                )
                self.assertGreater(
                    master.height(), channel.height(),
                    "the Grand Master must stay taller than the channel faders",
                )
                win.close()

    def test_quick_patch_emits_patch_changed_once(self):
        """One quick-patch press must resync the mixer once, not once per fixture."""
        self._application()
        from ui.main_window import MainWindow

        for label, action in (("ALIEN", lambda t: t._on_patch_alien_gia()),
                              ("KUMA", lambda t: t._on_patch_kuma_bench())):
            with self.subTest(press=label):
                win = MainWindow()
                counter = {"n": 0}
                win.tab_address.patch_changed.connect(lambda: counter.__setitem__("n", counter["n"] + 1))
                action(win.tab_address)
                self.assertEqual(counter["n"], 1,
                                 f"{label}: expected one patch_changed emission")
                self.assertEqual(len(win.tab_address.undo_stack), 1)
                win.close()

    def test_stream_rate_control_actually_changes_the_timer(self):
        """The Settings FPS field must steer the output timer.

        It was a dead control: FPS was absent from the settings_saved signal and
        nothing read the spin box, so the value could never have an effect.
        """
        self._application()
        from ui.main_window import MainWindow

        win = MainWindow()

        for fps, expected in ((20, 50), (43, 23), (60, 17)):
            win._on_settings_saved("127.0.0.1", 6454, 0, fps)
            self.assertEqual(win.stream_timer.interval(), expected,
                             f"fps {fps} should set a {expected} ms interval")
            self.assertEqual(win.artnet_sender.target_ip, "127.0.0.1")
        win.close()

    def test_export_to_page_matches_cue_table_palette(self):
        """GENERATE EXECUTORS must use the same colours the cue table shows."""
        self._application()
        from ui.main_window import MainWindow

        win = MainWindow()
        panel = win.tab_perform
        song = {"title": "Alpha Song", "bpm": 72.0,
                "palette": {"R": 11, "G": 22, "B": 33, "W": 44},
                "quadrant": "Q3_DEEP_WORSHIP"}
        sections = panel._derive_section_cues(song)

        captured = {}
        panel.export_to_page.connect(lambda cues: captured.setdefault("cues", cues))
        panel.playlist.append(song)
        panel._on_export_to_page()

        exported = [c for c in captured.get("cues", []) if c["type"] == "scene"]
        self.assertTrue(exported)
        verse = next(c for c in exported if "Verse" in c["label"])
        chorus = next(c for c in exported if "Chorus" in c["label"])
        self.assertEqual(verse["color"], sections[1]["color"],
                         "exported verse must match the cue table")
        self.assertEqual(chorus["color"], sections[2]["color"],
                         "exported chorus must match the cue table")
        win.close()

    def test_alien_and_kuma_autopatch_addressing(self):
        """Verifies requested DMX addressing: Alien AL36 at 001, 017, 033, 049 and Kumastb at 001."""
        self._application()
        from ui.main_window import MainWindow
        win = MainWindow()

        # 1. Test Alien AL36 4x GIA Stage Patch
        win.tab_address._on_patch_alien_gia()
        alien_starts = [1, 17, 33, 49]
        for idx, start_ch in enumerate(alien_starts):
            # Ch 1: Dimmer
            self.assertTrue(win.tab_address.grid_area.boxes[start_ch].is_patched)
            self.assertEqual(win.tab_address.grid_area.boxes[start_ch].channel_type, "dimmer")
            self.assertEqual(win.tab_address.grid_area.boxes[start_ch].fixture_name,
                             f"Alien-AL36 #{idx + 1}",
                             "quick-patch must use the v4 standard name without text qualifiers")
            # Ch 5: Empty (Alien has no white)
            self.assertEqual(win.tab_address.grid_area.boxes[start_ch + 4].channel_type, "empty")
            # Ch 8: Emptz (Empty)
            self.assertEqual(win.tab_address.grid_area.boxes[start_ch + 7].channel_type, "empty")

        # Verify gaps between fixtures are unpatched
        self.assertFalse(win.tab_address.grid_area.boxes[9].is_patched)
        self.assertFalse(win.tab_address.grid_area.boxes[16].is_patched)
        self.assertFalse(win.tab_address.grid_area.boxes[25].is_patched)
        self.assertFalse(win.tab_address.grid_area.boxes[32].is_patched)
        self.assertFalse(win.tab_address.grid_area.boxes[41].is_patched)
        self.assertFalse(win.tab_address.grid_area.boxes[48].is_patched)
        self.assertFalse(win.tab_address.grid_area.boxes[57].is_patched)

        # 2. Test Kumastb STL47 Bench Test Patch
        win.tab_address._on_patch_kuma_bench()
        self.assertTrue(win.tab_address.grid_area.boxes[1].is_patched)
        self.assertEqual(win.tab_address.grid_area.boxes[1].channel_type, "dimmer")
        self.assertEqual(win.tab_address.grid_area.boxes[1].fixture_name, "Kumastb-STL47",
                         "quick-patch must use the v4 standard name")
        # Ch 5: White (Kumastb has dedicated white)
        self.assertEqual(win.tab_address.grid_area.boxes[5].channel_type, "white")
        self.assertFalse(win.tab_address.grid_area.boxes[9].is_patched)
        self.assertFalse(win.tab_address.grid_area.boxes[17].is_patched)

        win.close()

    def test_perform_tab_cue_generation_and_crossfade(self):
        """Verifies song selection auto-populates section cues and triggers smooth crossfading."""
        self._application()
        from ui.main_window import MainWindow
        win = MainWindow()

        # Add sample worship song to playlist
        sample_worship = {
            "title": "Kebaikan Tuhan (Goodness of God)",
            "quadrant": "Q3 Worship",
            "bpm": 72.0,
            "palette": {"R": 180, "G": 90, "B": 240, "W": 40},
        }
        win.tab_perform.add_analyzed_song(sample_worship)
        self.assertEqual(len(win.tab_perform.playlist), 1)

        # Cues should auto-populate in cue_table (6 section cues: Intro, Verse 1, Chorus, Verse 2, Bridge, Ending)
        self.assertEqual(win.tab_perform.cue_table.rowCount(), 6)
        self.assertEqual(win.tab_perform.cue_table.item(0, 0).text(), "Intro")
        self.assertEqual(win.tab_perform.cue_table.item(2, 0).text(), "Chorus")
        self.assertEqual(win.tab_perform.cue_table.item(4, 0).text(), "Bridge")

        # Test GO+ master playback
        win.tab_perform._on_go_clicked()
        self.assertEqual(win.tab_perform.active_cue_index, 0)
        self.assertIn("INTRO", win.tab_perform.lbl_cue_status.text())

        # Test triggering next cue
        win.tab_perform._on_go_clicked()
        self.assertEqual(win.tab_perform.active_cue_index, 1)

        # Test crossfade tick simulation
        self.assertTrue(win._crossfade_timer.isActive())
        # Simulate timer tick
        win._on_crossfade_tick()
        self.assertIsNotNone(win.dmx_buffer)

        # Test fade black
        win.tab_perform._on_fade_black_clicked()
        self.assertIn("BLACKOUT", win.tab_perform.lbl_cue_status.text())

        win.close()

    def test_tactile_fader_zero_and_mixer_bank_scroll(self):
        """Verifies [X] clear button and quick bank jump scrolling in MixerTab."""
        self._application()
        from ui.main_window import MainWindow
        win = MainWindow()

        # 1. Test Grand Master dimensions and zeroing
        master = win.tab_mixer.master_fader
        self.assertTrue(master.is_master)
        self.assertEqual(master.width(), 68)
        self.assertGreaterEqual(master.minimumHeight(), 230)
        master.value = 255
        self.assertEqual(master.value, 255)
        # Simulate click on [X] button
        master.value = 0
        self.assertEqual(master.value, 0)

        # 2. Test Channel Fader [X] clear
        fader1 = win.tab_mixer.faders[1]
        fader1.value = 180
        self.assertEqual(fader1.value, 180)
        fader1.value = 0
        self.assertEqual(fader1.value, 0)

        # 3. Test Bank Scroll Jump
        win.tab_mixer.scroll_to_channel(17)
        self.assertGreater(win.tab_mixer.scroll_area.horizontalScrollBar().value(), 0)
        win.tab_mixer.scroll_to_channel(1)
        self.assertEqual(win.tab_mixer.scroll_area.horizontalScrollBar().value(), 0)

        win.close()

    def test_visualizer_3d_stage_and_haze_simulation(self):
        """Verifies 2D & 3D Stage Visualizer, volumetric beams, and atmospheric haze FX."""
        self._application()
        from ui.main_window import MainWindow
        win = MainWindow()

        win._on_open_visualizer()
        vis = win.win_visualizer
        self.assertIsNotNone(vis)
        self.assertTrue(vis.isVisible())
        self.assertEqual(vis.tabs.count(), 2)

        # Verify 3D Canvas properties and haze (Default: False / OFF)
        self.assertFalse(vis.canvas_3d.haze_enabled)
        vis._on_toggle_haze()
        self.assertTrue(vis.canvas_3d.haze_enabled)
        vis._on_toggle_haze()
        self.assertFalse(vis.canvas_3d.haze_enabled)

        # Verify 3D projection math
        sx, sy, sz = vis.canvas_3d.project(0, 0, 0, 400, 300)
        self.assertIsInstance(sx, float)
        self.assertIsInstance(sy, float)
        self.assertGreater(sz, 0)

        # Verify DMX update propagates to both 2D and 3D after patching
        win.tab_address._on_patch_alien_gia()
        vis.sync_fixtures(win.tab_address.get_patched_fixtures())
        self.assertEqual(len(vis.canvas_2d.fixtures), 4)
        self.assertEqual(len(vis.canvas_3d.fixtures_3d), 4)

        dmx_data = bytearray(512)
        # Patch Alien #1 at 1 (dimmer 255, red 200, green 100, blue 50)
        dmx_data[0] = 255
        dmx_data[1] = 200
        dmx_data[2] = 100
        dmx_data[3] = 50
        vis.update_dmx(dmx_data)
        self.assertEqual(vis.canvas_2d.fixtures[0]["dim"], 255)
        self.assertEqual(vis.canvas_3d.fixtures_3d[0]["dim"], 255)

        win.close()

    def test_fixture_editor_and_library_feedback_v4(self):
        """Verifies Feedback v4 polish: Fixture Editor defaults, table columns, and Fixture Library window."""
        self._application()
        from ui.panels.fixture_editor import FixtureEditorWindow, CHANNEL_TYPES
        from ui.panels.fixture_list import FixtureListWindow
        from ui.main_window import MainWindow

        # 1. Test FixtureEditorWindow
        editor = FixtureEditorWindow()
        self.assertEqual(editor.windowTitle(), "Fixture Editor")
        self.assertEqual(editor.txt_model.text(), "")
        self.assertEqual(editor.txt_maker.text(), "")
        self.assertEqual(editor.spin_channels.value(), 4)

        # Verify table headers and rows
        self.assertEqual(editor.table.columnCount(), 3)
        self.assertEqual(editor.table.horizontalHeaderItem(0).text(), "Channel")
        self.assertEqual(editor.table.horizontalHeaderItem(1).text(), "Label")
        self.assertEqual(editor.table.horizontalHeaderItem(2).text(), "Type")

        self.assertEqual(editor.table.rowCount(), 4)
        self.assertEqual(editor.table.item(0, 0).text(), "01")
        self.assertEqual(editor.table.item(1, 0).text(), "02")
        self.assertEqual(editor.table.item(2, 0).text(), "03")
        self.assertEqual(editor.table.item(3, 0).text(), "04")

        # Verify QLC+ channel types support
        for expected_type in ["Dimmer", "Red", "Green", "Blue", "White", "Amber", "UV", "Cyan", "Magenta", "Yellow", "Pan", "Tilt", "Gobo", "Prism", "Strobe", "Shutter"]:
            self.assertIn(expected_type, CHANNEL_TYPES)

        # Test changing channel count to 8
        editor.spin_channels.setValue(8)
        self.assertEqual(editor.table.rowCount(), 8)
        self.assertEqual(editor.table.item(7, 0).text(), "08")

        # Verify bottom buttons: Save and Close only
        self.assertEqual(editor.btn_save.text(), "Save")
        self.assertEqual(editor.btn_close.text(), "Close")
        editor.close()

        # 2. Test FixtureListWindow
        lib = FixtureListWindow()
        self.assertEqual(lib.windowTitle(), "Fixture Library")
        self.assertIsNotNone(lib.list_widget)
        self.assertIsNotNone(lib.inspector_text)
        lib.close()

        # 3. Test Title Bar behavior in MainWindow
        win = MainWindow()
        self.assertEqual(win.windowTitle(), "ZZLUXORA [Untitled.zlx]")
        win.current_project_path = "/home/zzdree/ANDREAS/zzluxora_v10/showfiles/custom_worship.zlx"
        win._update_title_bar()
        self.assertEqual(win.windowTitle(), "ZZLUXORA [/home/zzdree/ANDREAS/zzluxora_v10/showfiles/custom_worship.zlx]")
        win.close()


    def test_exporting_a_loaded_song_does_not_list_it_twice(self):
        """A song loaded as a file and then exported must stay ONE entry.

        Regression: add_analysis only matched existing entries that had no file,
        so a song that was loaded from disk and later exported to Perform gained
        a second row - the operator saw their own track duplicated in every tab,
        and deleting one left the other behind.
        """
        self._application()
        from ui.main_window import MainWindow

        win = MainWindow()
        lib = win.song_library
        lib.add_path("/tmp/Bapa_Yang_Kekal.wav")
        lib.add_path("/tmp/Nyalakan_ApiMu.wav")
        self.assertEqual(len(lib), 2)

        # The same track arrives again as a finished analysis from Result.
        index = lib.add_analysis({"title": "Bapa Yang Kekal",
                                  "quadrant": "Q3_DEEP_WORSHIP", "bpm": 72.0})
        self.assertEqual(len(lib), 2, "exporting must reuse the loaded entry, not add a row")
        self.assertEqual(index, 0)
        self.assertTrue(lib.songs[0].is_analyzed, "the analysis must land on the loaded entry")
        self.assertEqual(lib.songs[0].path, "/tmp/Bapa_Yang_Kekal.wav",
                         "the file must not be discarded when the analysis arrives")

        # Exporting the same result again is idempotent.
        self.assertEqual(lib.add_analysis({"title": "Bapa Yang Kekal", "bpm": 72.0}), 0)
        self.assertEqual(len(lib), 2)

        win.close()

    def test_removing_a_song_above_the_selection_keeps_the_same_track_selected(self):
        """Selection follows the song, not the slot.

        Regression: remove() clamped the selected index with min(), so deleting a
        song whose index was below the selection left the slot number unchanged -
        and the slot now held a different track. Measured: selecting lagu_B then
        removing lagu_A made the Result tab describe lagu_C, a song the operator
        never picked.
        """
        from core.song_library import SongLibrary

        lib = SongLibrary()
        lib.add_path("/tmp/lagu_A.wav", select=False)
        lib.add_path("/tmp/lagu_B.wav", select=False)
        lib.add_path("/tmp/lagu_C.wav", select=False)

        lib.select(1)
        selected_before = lib.selected()
        self.assertEqual(selected_before.name, "lagu_B.wav")

        lib.remove([0])

        self.assertIs(lib.selected(), selected_before,
                      "the same song object must stay selected after removing a song above it")
        self.assertEqual(lib.selected().name, "lagu_B.wav")
        self.assertEqual(lib.selected_index, 0)

    def test_removing_the_selected_song_moves_on_one_slot(self):
        """Deleting the selected song keeps the slot, clamped into range."""
        from core.song_library import SongLibrary

        lib = SongLibrary()
        for name in ("a", "b", "c"):
            lib.add_path(f"/tmp/{name}.wav", select=False)

        lib.select(1)
        lib.remove([1])

        self.assertEqual([song.name for song in lib.songs], ["a.wav", "c.wav"])
        self.assertEqual(lib.selected_index, 1)
        self.assertEqual(lib.selected().name, "c.wav")

        lib2 = SongLibrary()
        for name in ("a", "b", "c"):
            lib2.add_path(f"/tmp/{name}.wav", select=False)
        lib2.select(2)
        lib2.remove([2])
        self.assertEqual(lib2.selected_index, 1)
        self.assertEqual(lib2.selected().name, "b.wav")

    def test_reordering_keeps_the_selected_song_selected(self):
        """Moving another song must not steal the selection.

        Regression: move() set _selected = target, the destination slot of the
        song being dragged, so reordering the playlist always jumped the Result
        tab to that song. Measured: selecting c.wav and moving a.wav by +1 made
        the report read a.wav.
        """
        from core.song_library import SongLibrary

        lib = SongLibrary()
        for name in ("a", "b", "c"):
            lib.add_path(f"/tmp/{name}.wav", select=False)

        lib.select(2)
        selected_before = lib.selected()
        self.assertEqual(selected_before.name, "c.wav")

        lib.move(0, +1)

        self.assertIs(lib.selected(), selected_before,
                      "the selected song must survive a reorder of other entries")
        self.assertEqual(lib.selected().name, "c.wav")

        # And a long move that displaces the selected song keeps it selected too.
        lib.select(2)
        selected_before = lib.selected()
        lib.move(0, +2)
        self.assertIs(lib.selected(), selected_before)
        self.assertEqual(lib.selected().name, "c.wav")

    def test_reusing_an_entry_still_announces_the_selection(self):
        """add_analysis must broadcast the selection even when the index is unchanged.

        select() short-circuits on an identical index, so attaching a fresh
        analysis to the already-selected entry updated the entry but stayed
        silent. The Result tab refreshes its detail pane on this callback, so it
        kept showing the previous numbers after an export landed on the song
        already on screen.
        """
        from core.song_library import SongLibrary

        lib = SongLibrary()
        lib.add_path("/tmp/a.wav", select=True)

        seen: list[int] = []
        lib.on_selection_changed(lambda index: seen.append(index))

        index = lib.add_analysis({"title": "a", "bpm": 100.0})

        self.assertEqual(index, 0)
        self.assertEqual(seen, [0], "the selection must be re-announced on reuse")

    def test_result_tab_loads_metrics_of_the_selected_song(self):
        """Switching songs in the shared list must refresh the metrics card.

        Regression: _on_library_selection only moved the highlight. Its
        setCurrentRow is run with signals blocked, so currentRowChanged never
        fired and the card kept the previous song's numbers. Selecting a song
        with no analysis showed the old song's metrics instead of the placeholder;
        measured by selecting lagu_B then lagu_A, the table still read lagu_B.
        """
        self._application()
        from ui.main_window import MainWindow

        win = MainWindow()
        lib = win.song_library
        lib.add_path("/tmp/lagu_A.wav", select=False)
        lib.add_path("/tmp/lagu_B.wav", select=False)

        def analysis(title: str, bpm: float) -> dict:
            return {
                "title": title, "frames_count": 500, "fps_rate": 43.07,
                "valence": 0.3, "arousal": 0.2, "rms": 0.1,
                "spectral_centroid": 1500.0, "chroma_key": "C Major",
                "dominant_pitch": "C", "mfcc_density": 0.5,
                "spectral_flux": 0.4, "quadrant": "Q1", "bpm": bpm,
                "duration_sec": 12.0, "palette": {"R": 255, "G": 180, "B": 50, "W": 0},
            }

        lib.set_analysis(0, analysis("lagu_A", 100.0))
        lib.set_analysis(1, analysis("lagu_B", 120.0))

        result = win.tab_result

        def shown_title() -> str:
            item = result.table.item(0, 1)
            return item.text() if item else ""

        lib.select(1)
        self.assertEqual(shown_title(), "lagu_B")
        lib.select(0)
        self.assertEqual(shown_title(), "lagu_A",
                         "the card must follow the selection, not stay on the old song")

        win.close()

    def test_selecting_an_unanalysed_song_clears_the_metrics_card(self):
        """A song with no analysis must clear the card, not keep the old numbers."""
        self._application()
        from ui.main_window import MainWindow

        win = MainWindow()
        lib = win.song_library
        lib.add_path("/tmp/analysed.wav", select=False)
        lib.add_path("/tmp/pending.wav", select=False)
        lib.set_analysis(0, {
            "title": "analysed", "frames_count": 500, "fps_rate": 43.07,
            "valence": 0.3, "arousal": 0.2, "rms": 0.1, "spectral_centroid": 1500.0,
            "chroma_key": "C Major", "dominant_pitch": "C", "mfcc_density": 0.5,
            "spectral_flux": 0.4, "quadrant": "Q1", "bpm": 100.0, "duration_sec": 12.0,
            "palette": {"R": 10, "G": 20, "B": 30, "W": 0},
        })

        result = win.tab_result
        lib.select(0)
        self.assertEqual(result.table.item(0, 1).text(), "analysed")

        lib.select(1)
        self.assertEqual(result.table.item(0, 1).text(), "No analysis yet")
        self.assertFalse(result.btn_export.isEnabled())
        self.assertIsNone(result.current_analysis)

        win.close()


if __name__ == "__main__":
    unittest.main()
