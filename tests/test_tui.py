import copy
import curses
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from yeti_voice.model import DEFAULTS
from yeti_voice.tui import (
    TABS,
    App,
    Control,
    format_value,
    get_path,
    set_path,
)


class TuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.env = patch.dict(
            os.environ,
            {
                "YETI_VOICE_CONFIG": str(root / "config.json"),
                "YETI_VOICE_PROFILES": str(root / "profiles.json"),
            },
        )
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def _mock_screen(self, height=24, width=80):
        screen = MagicMock()
        screen.getmaxyx.return_value = (height, width)
        return screen

    def test_tabs_structure(self):
        self.assertEqual(len(TABS), 5)
        tab_names = [name for name, _ in TABS]
        self.assertIn("Principal", tab_names)
        self.assertIn("Limpeza", tab_names)
        self.assertIn("EQ", tab_names)
        self.assertIn("Dinâmica", tab_names)
        self.assertIn("Efeitos", tab_names)

    def test_format_value(self):
        c_bool = Control("Test Bool", "enabled", kind="bool")
        self.assertEqual(format_value(True, c_bool), "ON")
        self.assertEqual(format_value(False, c_bool), "OFF")

        c_num = Control("Test Gain", "gain", 0, 100, 1, "%")
        self.assertEqual(format_value(50.0, c_num), "50%")
        self.assertEqual(format_value(4.5, c_num), "4.5%")

    def test_app_init_and_draw(self):
        screen = self._mock_screen(24, 80)
        with patch("yeti_voice.tui.curses.has_colors", return_value=True):
            app = App(screen)
            app.draw()
            screen.erase.assert_called()
            screen.refresh.assert_called()

    def test_app_draw_small_terminal(self):
        screen = self._mock_screen(12, 40)
        with patch("yeti_voice.tui.curses.has_colors", return_value=False):
            app = App(screen)
            app.draw()
            screen.refresh.assert_called()

    def test_app_draw_large_terminal(self):
        screen = self._mock_screen(40, 120)
        with patch("yeti_voice.tui.curses.has_colors", return_value=True):
            app = App(screen)
            app.draw()
            screen.refresh.assert_called()

    def test_draw_meter(self):
        screen = self._mock_screen(24, 80)
        app = App(screen)
        # 50%
        app.draw_meter(5, 10, 50, 0, 100, length=14)
        # Verify safe_add was called to add brackets and blocks
        calls = [c.args for c in screen.addnstr.call_args_list]
        added_texts = "".join(str(c[2]) for c in calls)
        self.assertIn("[", added_texts)
        self.assertIn("]", added_texts)
        self.assertIn("█", added_texts)
        self.assertIn("░", added_texts)

    def test_adjust_values(self):
        screen = self._mock_screen(24, 80)
        app = App(screen)
        # Select first control: "Blue VO!CE" (bool)
        app.selected = 0
        initial_val = app.settings["enabled"]
        app.adjust(1)
        self.assertEqual(app.settings["enabled"], not initial_val)

        # Select tab 0, control 3: "Ganho do Nano" (hardware_gain)
        app.selected = 3
        with patch("yeti_voice.tui.set_hardware_percent", return_value=(True, "Mic")):
            app.settings["hardware_gain"] = 50
            app.adjust(1)
            self.assertEqual(app.settings["hardware_gain"], 52)
            app.adjust(-1)
            self.assertEqual(app.settings["hardware_gain"], 50)

    def test_choose_builtin_profile(self):
        screen = self._mock_screen(24, 80)
        app = App(screen)
        with patch("yeti_voice.tui.set_hardware_percent", return_value=(True, "Mic")):
            app.choose_builtin_profile(1)  # Broadcast
            self.assertEqual(app.settings["active_profile"], "Broadcast")

    def test_profile_menu_renders_and_quits(self):
        screen = self._mock_screen(24, 80)
        screen.getch.return_value = ord("q")
        app = App(screen)
        app.profile_menu()
        screen.erase.assert_called()
        screen.refresh.assert_called()

    def test_diag_modal_renders_and_quits(self):
        screen = self._mock_screen(24, 80)
        screen.getch.return_value = 27  # ESC
        app = App(screen)
        with patch("yeti_voice.tui.diagnostics", return_value={
            "usb": {"connected": True, "path": "1-2", "product": "Yeti Nano"},
            "alsa_card": "Nano",
            "alsa_controls": ["PCM", "Mic"],
            "pulse_source": "alsa_input.usb-Blue",
            "pulse_error": "",
            "healthy": True,
            "recommendation": "pronto",
        }):
            app.diag_modal()
            screen.erase.assert_called()
            screen.refresh.assert_called()


if __name__ == "__main__":
    unittest.main()

