import json
import os

STORAGE_FILE = "presets.json"
AUTO_RECOVERY_FILE = "auto_recovery.json"
TEMPLATES_DIR = "templates"
PRESETS_DIR = "presets"
EXPORTS_DIR = "exports"

# Tab 1-5 sekmelerinin isteyebileceği tüm temel parametreler
DEFAULT_PRESET_FIELDS = {
    "customer_name": "Floor & Decor Stone Corp.",
    "po_number": "PO-2026-089",
    "product_name": "bullnose / pencil",
    "product_code": "FD-MAR-3061",
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
    "box_tare_kg": 0.5,
    "crate_tare_kg": 40.0
}

DEFAULT_PRESETS = {
    "30.5x61x1.2 cm Marble Tile": {
        **DEFAULT_PRESET_FIELDS,
        "product_name": "30.5x61x1.2 cm Marble Tile",
        "product_code": "FD-MAR-3061"
    },
    "15x30.5x1 cm Travertine Tile": {
        **DEFAULT_PRESET_FIELDS,
        "customer_name": "Ionic Stone Ltd.",
        "po_number": "PO-2026-104",
        "product_name": "15x30.5x1 cm Travertine Tile",
        "product_code": "ION-TRV-1530",
        "thickness_cm": 1.0,
        "density": 2.4,
        "pcs_per_box": 10,
        "boxes_in_crate": 50,
        "box_tare_kg": 0.4,
        "crate_tare_kg": 35.0
    }
}

def ensure_storage_dirs():
    """Gerekli klasörleri oluşturur."""
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    os.makedirs(PRESETS_DIR, exist_ok=True)
    os.makedirs(EXPORTS_DIR, exist_ok=True)

def load_presets():
    """
    Kayıtlı reçeteleri yükler. Eksik olan HERHANGİ bir alan varsa
    varsayılan sözlükten otomatik tamamlar (KeyError engelleme).
    """
    presets = {}
    
    # 1. Varsayılanları yükle
    for k, v in DEFAULT_PRESETS.items():
        base = DEFAULT_PRESET_FIELDS.copy()
        base.update(v)
        presets[k] = base

    # 2. Varsa kayıtlı presets.json dosyasını yükle ve eksik alanları yama yap
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                for k, v in saved.items():
                    if isinstance(v, dict):
                        base = DEFAULT_PRESET_FIELDS.copy()
                        base.update(v)
                        presets[k] = base
                    else:
                        presets[k] = v
        except Exception:
            pass
            
    return presets

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

def save_auto_recovery(cart_or_data, draft_data=None):
    """Hem tekli hem ikili parametre çağrılarını destekler."""
    try:
        if draft_data is not None:
            data = {"cart": cart_or_data, "draft_data": draft_data}
        elif isinstance(cart_or_data, dict):
            data = cart_or_data
        else:
            data = {"cart": cart_or_data, "draft_data": {}}

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
