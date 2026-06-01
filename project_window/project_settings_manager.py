import json
import os

from settings.settings_manager import WWSettingsManager

PROJECT_SETTINGS_FILE = "project_settings.json"

def load_project_settings(project_name):
    """Load settings for the given project."""
    settings = {}
    filepath = WWSettingsManager.get_project_path(file=PROJECT_SETTINGS_FILE)
    if not os.path.exists(filepath): # backward compatibility
        oldpath = os.path.join(os.getcwd(), PROJECT_SETTINGS_FILE)
        if os.path.exists(oldpath):
            os.rename(oldpath, filepath)

    if os.path.exists(filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                all_settings = json.load(f)
            settings = all_settings.get(project_name, {})
        except Exception as e:
            print("Error loading project settings:", e)
    return settings

def save_project_settings(project_name, project_settings, projects=None):
    """Save the given settings for the project."""
    settings = {}
    filepath = WWSettingsManager.get_project_path(file=PROJECT_SETTINGS_FILE)
    if os.path.exists(filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                settings = json.load(f)
        except Exception as e:
            print("Error loading project settings:", e)
    if projects:
        settings_to_delete = []
        for setting_name in settings:
            if setting_name not in [p["name"] for p in projects]:
                settings_to_delete.append(setting_name)
        for setting_name in settings_to_delete:
            del settings[setting_name]
    settings[project_name] = project_settings
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print("Error saving project settings:", e)
