import json
import os

STORAGE_FILE = "presets.json"
AUTO_RECOVERY_FILE = "auto_recovery.json"
TEMPLATES_DIR = "templates"
PRESETS_DIR = "presets"
EXPORTS_DIR = "exports"

# Temel varsayılan reçeteler
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
    },
    "15x30.5x1 cm Travertine Tile": {
        "sales_unit": "M²",
        "length_cm": 30.5,
        "width_cm": 15.0,
        "thickness_cm": 1.0,
        "density": 2.4,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 4.0,
        "pcs_per_box": 10,
        "boxes_in_crate": 50,
        "crate_tare_kg": 35.0
    }
}

def ensure_storage_dirs():
    """Gerekli klasörleri oluşturur."""
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    os.makedirs(PRESETS_DIR, exist_ok=True)
    os.makedirs(EXPORTS_DIR, exist_ok=True)

def load_presets():
    """Kayıtlı reçeteleri yükler."""
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                return {**DEFAULT_PRESETS, **saved}
        except Exception:
            return DEFAULT_PRESETS
    return DEFAULT_PRESETS

# tab1_product_specs.py'nin çağırdığı takma isim (alias)
def load_all_presets():
    return load_presets()

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

def save_auto_recovery(data):
    """Otomatik kurtarma verisini kaydeder."""
    try:
        with open(AUTO_RECOVERY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def load_auto_recovery():
    """Otomatik kurtarma verisini yükler."""
    if os.path.exists(AUTO_RECOVERY_FILE):
        try:
            with open(AUTO_RECOVERY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def clear_auto_recovery():
    """Otomatik kurtarma dosyasını siler."""
    if os.path.exists(AUTO_RECOVERY_FILE):
        try:
            os.remove(AUTO_RECOVERY_FILE)
        except Exception:
            pass

def list_templates():
    if not os.path.exists(TEMPLATES_DIR):
        return []
    return [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".xlsx") or f.endswith(".json")]

def list_exports():
    if not os.path.exists(EXPORTS_DIR):
        return []
    return [f for f in os.listdir(EXPORTS_DIR)]
