import unittest
from unittest.mock import Mock, patch

from yeti_voice.system import set_hardware_percent


class HardwareControlTests(unittest.TestCase):
    @patch("yeti_voice.system.run")
    @patch("yeti_voice.system.alsa_controls", return_value=["PCM", "Mic"])
    @patch("yeti_voice.system.alsa_card", return_value="Nano")
    def test_yeti_simple_control_names_are_mapped(self, _card, _controls, run):
        run.return_value = Mock(returncode=0, stderr="")
        ok_gain, gain_control = set_hardware_percent("gain", 55)
        ok_headphone, headphone_control = set_hardware_percent("headphone", 60)
        self.assertTrue(ok_gain)
        self.assertTrue(ok_headphone)
        self.assertEqual(gain_control, "Mic")
        self.assertEqual(headphone_control, "PCM")
        self.assertEqual(run.call_args_list[0].args[0], ["amixer", "-c", "Nano", "sset", "Mic", "55%"])
        self.assertEqual(run.call_args_list[1].args[0], ["amixer", "-c", "Nano", "sset", "PCM", "60%"])


if __name__ == "__main__":
    unittest.main()
