import os
import json
import tempfile
import unittest
from core.project_io import ProjectIO


class TestProjectIO(unittest.TestCase):
    def test_default_project_creation(self):
        proj = ProjectIO.create_default_project("My Service Sunday")
        self.assertEqual(proj["app"], "ZZLUXORA")
        self.assertEqual(proj["version"], ProjectIO.VERSION)
        self.assertEqual(proj["project_name"], "My Service Sunday")
        self.assertEqual(len(proj["patches"]), 2)

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test_proj.zlx")
            original_data = ProjectIO.create_default_project("Test Church Event")
            original_data["target_ip"] = "192.168.4.1"

            save_ok = ProjectIO.save_project(original_data, file_path)
            self.assertTrue(save_ok)
            self.assertTrue(os.path.exists(file_path))

            loaded_data = ProjectIO.load_project(file_path)
            self.assertIsNotNone(loaded_data)
            self.assertEqual(loaded_data["project_name"], "Test Church Event")
            self.assertEqual(loaded_data["target_ip"], "192.168.4.1")

    def test_default_project_uses_runtime_output_defaults(self):
        project = ProjectIO.create_default_project()

        self.assertEqual(project["universe"], 0)
        self.assertEqual(project["master_dimmer"], 255)
        self.assertEqual(project["port"], 6454)
        self.assertEqual(project["cues"], [])

    def test_main_window_project_roundtrip_preserves_cues_port_and_dmx_scale(self):
        from types import SimpleNamespace
        from unittest.mock import Mock, patch

        from ui.main_window import MainWindow

        cue = {
            "label": "PRAISE",
            "type": "scene",
            "color": {"R": 255, "G": 200, "B": 80, "W": 40},
            "dimmer": 220,
            "fade_time": 1.5,
        }
        song = {"title": "Sunday Service", "bpm": 72.0}

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "roundtrip.zlx")
            save_faders = {channel: SimpleNamespace(value=0) for channel in range(513)}
            save_faders[0].value = 192
            save_faders[1].value = 200
            save_window = SimpleNamespace(
                tab_address=SimpleNamespace(
                    grid_area=SimpleNamespace(boxes={}),
                    # Save now takes patches from the address grid's real
                    # contiguous runs rather than a modulo-8 derivation.
                    get_patched_fixtures=lambda: [
                        {
                            "name": "Alien-AL36 #1",
                            "start_channel": 1,
                            "channels": [
                                {"channel": 1 + i, "type": "red", "label": "RED"}
                                for i in range(8)
                            ],
                        }
                    ],
                ),
                tab_mixer=SimpleNamespace(
                    faders=save_faders,
                    master_fader=save_faders[0],
                ),
                tab_perform=SimpleNamespace(playlist=[song]),
                tab_page=SimpleNamespace(
                    executor_buttons=[SimpleNamespace(cue_data=cue)],
                ),
                target_ip="192.168.4.1",
                target_port=7777,
                target_universe=2,
                _update_title_bar=Mock(),
            )

            with patch("ui.main_window.QMessageBox.information"):
                MainWindow._save_to_path(save_window, file_path)

            saved_project = ProjectIO.load_project(file_path)
            self.assertEqual(saved_project["cues"], [cue])
            self.assertEqual(saved_project["port"], 7777)

            load_faders = {channel: SimpleNamespace(value=0) for channel in range(513)}
            load_window = SimpleNamespace(
                current_project_path="",
                target_port=6454,
                artnet_sender=SimpleNamespace(close=Mock()),
                tab_address=SimpleNamespace(
                    record_undo=Mock(),
                    grid_area=SimpleNamespace(boxes={}),
                    patch_changed=SimpleNamespace(emit=Mock()),
                ),
                tab_perform=SimpleNamespace(
                    playlist=[],
                    playlist_widget=SimpleNamespace(clear=Mock()),
                    add_analyzed_song=Mock(),
                ),
                tab_page=SimpleNamespace(
                    _clear_executors=Mock(),
                    load_cues=Mock(),
                ),
                tab_mixer=SimpleNamespace(
                    faders=load_faders,
                    master_fader=load_faders[0],
                    set_channel_value=lambda channel, value, silent=False: setattr(
                        load_faders[channel], "value", value
                    ),
                ),
                dmx_buffer=bytearray(512),
                _update_title_bar=Mock(),
            )

            with patch("ui.main_window.ArtNetSender") as sender_factory:
                MainWindow.load_project_file(load_window, file_path, notify=False)

            self.assertEqual(load_window.target_port, 7777)
            sender_factory.assert_called_once_with(
                target_ip="192.168.4.1", universe=2, port=7777
            )
            load_window.tab_page.load_cues.assert_called_once_with([cue])
            self.assertEqual(load_window.dmx_buffer[0], 151)


class TestProjectSaveIsAtomic(unittest.TestCase):
    """A failed save must leave the previous showfile intact.

    Regression: save_project opened the destination with mode "w", which
    truncates before the first byte is written, then let json.dump write in
    stages (measured: 1945 separate write() calls). When serialization failed
    part way through, the operator's saved showfile was replaced by a truncated
    fragment - a healthy 1973-byte project became 51 unusable bytes.
    """

    class _Unserializable:
        def __repr__(self):
            return "<unserializable>"

    def test_failed_save_preserves_previous_file_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "show.zlx")
            self.assertTrue(ProjectIO.save_project(ProjectIO.create_default_project(), target))
            with open(target, "rb") as handle:
                before = handle.read()
            self.assertGreater(len(before), 0)

            broken = ProjectIO.create_default_project()
            broken["patches"] = [{"bad": self._Unserializable()}]

            self.assertFalse(ProjectIO.save_project(broken, target))
            with open(target, "rb") as handle:
                self.assertEqual(handle.read(), before, "the previous showfile must survive a failed save")
            self.assertIsNotNone(ProjectIO.load_project(target))

    def test_failed_save_leaves_no_temporary_behind(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "show.zlx")
            broken = ProjectIO.create_default_project()
            broken["patches"] = [{"bad": self._Unserializable()}]
            ProjectIO.save_project(broken, target)

            leftovers = [name for name in os.listdir(tmpdir) if name.endswith(".tmp")]
            self.assertEqual(leftovers, [], f"temporary files were left behind: {leftovers}")

    def test_successful_save_leaves_no_temporary_behind(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "show.zlx")
            self.assertTrue(ProjectIO.save_project(ProjectIO.create_default_project(), target))
            leftovers = [name for name in os.listdir(tmpdir) if name.endswith(".tmp")]
            self.assertEqual(leftovers, [])


class TestProjectPayloadGate(unittest.TestCase):
    """A .zlx file must be validated before the console adopts it.

    Regression: main_window called json.load and used the result directly, so
    any JSON at all was accepted - a QLC+ file, or one whose target_ip was the
    string "not-an-ip" - and the console then sent Art-Net to that address.
    """

    def test_accepts_a_valid_project(self):
        self.assertIsNone(ProjectIO.validate_payload(ProjectIO.create_default_project()))

    def test_rejects_non_object_payload(self):
        self.assertIsNotNone(ProjectIO.validate_payload([1, 2, 3]))
        self.assertIsNotNone(ProjectIO.validate_payload("a string"))

    def test_rejects_foreign_app_marker(self):
        self.assertIsNotNone(ProjectIO.validate_payload({"app": "QLC+", "target_ip": "127.0.0.1"}))

    def test_rejects_missing_app_marker(self):
        self.assertIsNotNone(ProjectIO.validate_payload({"target_ip": "127.0.0.1"}))

    def test_rejects_hostile_or_malformed_target_ip(self):
        for bad in ("not-an-ip", "192.168.4.999", "192.168.4", "1.2.3.4.5", "", "12.34.56.78x"):
            with self.subTest(target_ip=bad):
                data = ProjectIO.create_default_project()
                data["target_ip"] = bad
                self.assertIsNotNone(ProjectIO.validate_payload(data), bad)

    def test_accepts_valid_ipv4_addresses(self):
        for good in ("127.0.0.1", "192.168.4.1", "192.168.1.255", "0.0.0.0"):
            with self.subTest(target_ip=good):
                data = ProjectIO.create_default_project()
                data["target_ip"] = good
                self.assertIsNone(ProjectIO.validate_payload(data), good)

    def test_rejects_wrong_container_types(self):
        cases = {"patches": {}, "songs": {}, "cues": {}, "faders": []}
        for key, value in cases.items():
            with self.subTest(field=key):
                data = ProjectIO.create_default_project()
                data[key] = value
                self.assertIsNotNone(ProjectIO.validate_payload(data), key)

    def test_rejects_cues_holding_non_object_items(self):
        """A cue list of ints must be refused, not loaded into the UI.

        PageTab.load_cues dereferences each entry with .get(), so an entry that
        is not an object raised AttributeError ('int' object has no attribute
        'get') on load. The gate only checked that 'cues' was a list, not what it
        held, so a hand-edited showfile crashed the console.
        """
        for bad in ([42], ["a cue"], [None], [{"label": "ok"}, 42]):
            with self.subTest(cues=bad):
                data = ProjectIO.create_default_project()
                data["cues"] = bad
                self.assertIsNotNone(ProjectIO.validate_payload(data), bad)

        for good in ([], [{}], [{"label": "L"}], [{"label": "L", "type": "flash"}]):
            with self.subTest(cues=good):
                data = ProjectIO.create_default_project()
                data["cues"] = good
                self.assertIsNone(ProjectIO.validate_payload(data), good)

    def test_load_project_rejects_a_foreign_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "foreign.zlx")
            with open(target, "w", encoding="utf-8") as handle:
                json.dump({"app": "QLC+", "target_ip": "not-an-ip"}, handle)
            self.assertIsNone(ProjectIO.load_project(target))


if __name__ == "__main__":
    unittest.main()
