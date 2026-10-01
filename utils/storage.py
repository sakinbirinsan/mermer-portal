import json
import os

# app.py'nin 4. satırında çağrılan temel değişken
TEMPLATES_DIR = "templates"
EXPORTS_DIR = "exports"
STORAGE_FILE = "presets.json"
AUTO_RECOVERY_FILE = "auto_recovery.json"

# Temel Reçeteler
DEFAULT_PRESETS = {
    "30.5x61x1.2 cm Marble Tile": {
        "sales_unit": "M²",
        "length_cm": 61.0,
        "width_cm": 30.5,
        "thickness_cm": 1.2,
        "density": 2.7,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 4.0,
        "pcs_per_box": 6,
        "boxes_in_crate": 40,
        "crate_tare_kg": 40.0
    }
}

# app.py'nin çağırdığı 1. fonksiyon
def ensure_storage_dirs():
    """Gerekli klasörlerin varlığını garanti eder."""
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    os.makedirs(EXPORTS_DIR, exist_ok=True)

# app.py'nin çağırdığı 2. fonksiyon
def load_auto_recovery():
    """Otomatik kurtarma dosyasını okur."""
    if os.path.exists(AUTO_RECOVERY_FILE):
        try:
            with open(AUTO_RECOVERY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

# app.py'nin çağırdığı 3. fonksiyon
def clear_auto_recovery():
    """Otomatik kurtarma dosyasını temizler."""
    if os.path.exists(AUTO_RECOVERY_FILE):
        try:
            os.remove(AUTO_RECOVERY_FILE)
        except Exception:
            pass

def save_auto_recovery(data):
    """Otomatik kurtarmayı kaydeder."""
    try:
        with open(AUTO_RECOVERY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def load_presets():
    """Reçeteleri yükler."""
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                return {**DEFAULT_PRESETS, **saved}
        except Exception:
            return DEFAULT_PRESETS
    return DEFAULT_PRESETS

def save_presets(presets):
    """Reçeteleri kaydeder."""
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(presets, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False

def delete_preset(preset_name):
    """Reçeteyi siler."""
    presets = load_presets()
    if preset_name in presets:
        del presets[preset_name]
        return save_presets(presets)
    return False
