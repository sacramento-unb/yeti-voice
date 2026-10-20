import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yeti_voice.model import (
    BUILTIN_PROFILES,
    DEFAULTS,
    apply_profile,
    delete_profile,
    list_profiles,
    load_config,
    load_user_profiles,
    mark_profile_modified,
    profile_settings,
    save_config,
    save_profile,
)


class ProfileTests(unittest.TestCase):
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

    def test_factory_profiles_are_available(self):
        profiles = list_profiles(copy.deepcopy(DEFAULTS))
        self.assertEqual(len(profiles), 8)
        self.assertTrue(all(item["builtin"] for item in profiles))
        self.assertIn("Podcast", {item["name"] for item in profiles})
        self.assertIn("ASMR", {item["name"] for item in profiles})

    def test_factory_profile_preserves_hardware_levels(self):
        current = copy.deepcopy(DEFAULTS)
        current["hardware_gain"] = 71
        current["headphone_volume"] = 42
        result = profile_settings("broadcast", current)
        self.assertEqual(result["active_profile"], "Broadcast")
        self.assertFalse(result["profile_modified"])
        self.assertEqual(result["hardware_gain"], 71)
        self.assertEqual(result["headphone_volume"], 42)

    def test_custom_profile_round_trip_includes_hardware(self):
        settings = copy.deepcopy(DEFAULTS)
        settings["hardware_gain"] = 77
        settings["eq"]["mid"]["gain_db"] = 4.5
        name = save_profile("Minha Voz", settings, "Ajuste do escritório")
        self.assertEqual(name, "Minha Voz")
        self.assertIn("Minha Voz", load_user_profiles())
        loaded = profile_settings("minha voz", DEFAULTS)
        self.assertEqual(loaded["hardware_gain"], 77)
        self.assertEqual(loaded["eq"]["mid"]["gain_db"], 4.5)

    def test_apply_profile_persists_active_state(self):
        save_config(copy.deepcopy(DEFAULTS))
        applied = apply_profile("Podcast")
        self.assertEqual(applied["active_profile"], "Podcast")
        self.assertEqual(load_config()["active_profile"], "Podcast")

    def test_modified_marker(self):
        settings = copy.deepcopy(DEFAULTS)
        mark_profile_modified(settings)
        self.assertTrue(settings["profile_modified"])

    def test_delete_custom_and_protect_factory(self):
        current = copy.deepcopy(DEFAULTS)
        save_profile("Temporário", current)
        current["active_profile"] = "Temporário"
        save_config(current)
        self.assertEqual(delete_profile("temporário"), "Temporário")
        self.assertNotIn("Temporário", load_user_profiles())
        self.assertEqual(load_config()["active_profile"], "Natural")
        with self.assertRaises(ValueError):
            delete_profile("Natural")
        with self.assertRaises(ValueError):
            save_profile("ASMR", copy.deepcopy(DEFAULTS))

    def test_profiles_file_has_versioned_schema(self):
        save_profile("Teste", copy.deepcopy(DEFAULTS))
        document = json.loads((Path(self.temp.name) / "profiles.json").read_text())
        self.assertEqual(document["version"], 1)
        self.assertIn("Teste", document["profiles"])


if __name__ == "__main__":
    unittest.main()
