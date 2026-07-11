"""Settings persistence for the GUI."""
import json
import os
from datetime import datetime

from config import SETTINGS_FILE


class SettingsStore:
    """Load and save application settings to disk."""

    def __init__(self, path=SETTINGS_FILE):
        self.path = path

    def load(self):
        if not os.path.exists(self.path):
            return None
        with open(self.path, 'r', encoding='utf-8') as handle:
            return json.load(handle)

    def save(self, settings):
        with open(self.path, 'w', encoding='utf-8') as handle:
            json.dump(settings, handle, indent=2, ensure_ascii=False)

    def collect(self, settings_tabs):
        """Gather all panel settings into one dict."""
        settings = {}
        settings.update(settings_tabs.basic.get_settings())
        settings.update(settings_tabs.vad.get_settings())
        settings.update(settings_tabs.voice.get_settings())
        settings.update(settings_tabs.subtitle.get_settings())
        settings.update(settings_tabs.diarization.get_settings())
        settings['last_saved'] = datetime.now().isoformat()
        return settings

    def apply(self, settings, settings_tabs):
        """Apply a settings dict to all panels."""
        settings_tabs.basic.apply_settings(settings)
        settings_tabs.vad.apply_settings(settings)
        settings_tabs.voice.apply_settings(settings)
        settings_tabs.subtitle.apply_settings(settings)
        settings_tabs.diarization.apply_settings(settings)
