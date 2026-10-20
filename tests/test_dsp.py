import copy
import unittest

from yeti_voice.dsp import build_filter_chain, db_to_linear
from yeti_voice.model import BUILTIN_PROFILES, DEFAULTS, apply_preset


class DspTests(unittest.TestCase):
    def test_default_chain_has_broadcast_processors(self):
        chain = build_filter_chain(copy.deepcopy(DEFAULTS))
        for expected in ("highpass=", "afftdn=", "agate=", "equalizer=", "deesser=", "acompressor=", "alimiter="):
            self.assertIn(expected, chain)
        self.assertGreaterEqual(chain.count("equalizer="), 4)

    def test_optional_effects(self):
        settings = copy.deepcopy(DEFAULTS)
        for name in ("pitch", "flanger", "chorus", "reverb", "ring_mod", "delay"):
            settings[name]["enabled"] = True
        settings["pitch"]["semitones"] = 4
        chain = build_filter_chain(settings)
        for expected in ("rubberband=", "flanger=", "chorus=", "aecho=", "tremolo="):
            self.assertIn(expected, chain)

    def test_preset_keeps_hardware_levels(self):
        current = copy.deepcopy(DEFAULTS)
        current["hardware_gain"] = 73
        result = apply_preset("Broadcast", current)
        self.assertEqual(result["hardware_gain"], 73)
        self.assertEqual(result["compressor"]["ratio"], 3.5)

    def test_every_builtin_profile_builds_a_chain(self):
        current = copy.deepcopy(DEFAULTS)
        for name in BUILTIN_PROFILES:
            chain = build_filter_chain(apply_preset(name, current))
            self.assertIn("volume=", chain, name)

    def test_db_conversion(self):
        self.assertAlmostEqual(db_to_linear(0), 1)
        self.assertAlmostEqual(db_to_linear(-20), 0.1)


if __name__ == "__main__":
    unittest.main()
