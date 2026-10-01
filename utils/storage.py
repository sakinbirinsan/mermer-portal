import json
import os

STORAGE_FILE = "presets.json"
AUTO_RECOVERY_FILE = "auto_recovery.json"
TEMPLATES_DIR = "templates"
PRESETS_DIR = "presets"
EXPORTS_DIR = "exports"

class SafePresetDict(dict):
    """
    Koddaki herhangi bir sekme (Tab) sözlükte olmayan BİLİNMEYEN bir anahtar
    çağırsa bile KeyError vermesini engelleyen akıllı koruma sınıfı.
    """
    def __getitem__(self, key):
        if key in self:
            return super().__getitem__(key)
        # Eğer istenen anahtar sayısal bir ölçü/adet ise varsayılan float/int döndür
        if any(x in key for x in ["length", "width", "thick", "m2", "kg", "density", "rate", "trim", "kerf", "size", "tare"]):
            return 1.0
        if any(x in key for x in ["pcs", "box", "crate", "count", "num"]):
            return 1
        # Metin alanları için varsayılan string
        return ""

# Bilinen tüm değişken eşleşmeleri
DEFAULT_PRESET_FIELDS = {
    # Müşteri ve Ürün Bilgileri
    "customer_name": "Floor & Decor Stone Corp.",
    "customer": "Floor & Decor Stone Corp.",
    "po_number": "PO-2026-089",
    "po": "PO-2026-089",
    "product_name": "30.5x61x1.2 cm Marble Tile",
    "product_code": "FD-MAR-3061",
    "sales_unit": "M²",
    "unit": "M²",
    
    # Ebat ve Ölçüler (Tüm Varyasyonlar)
    "p_length": 61.0,
    "p_width": 30.5,
    "p_thick": 1.2,
    "p_thickness": 1.2,
    "length_cm": 61.0,
    "width_cm": 30.5,
    "thickness_cm": 1.2,
    "p_density": 2.7,
    "density": 2.7,
    "c_length": 61.0,
    "c_width": 30.5,
    
    # Paylar ve Toleranslar
    "edge_trim": 2.0,
    "breakage_rate": 3.0,
    "saw_kerf_mm": 4.0,
    "fire_orani": 3.0,
    "tester_payi": 4.0,
    
    # Ambalaj ve Paketleme
    "pcs_box": 6,
    "pcs_per_box": 6,
    "box_crate": 40,
    "boxes_in_crate": 40,
    "box_tare": 0.5,
    "box_tare_kg": 0.5,
    "crate_tare": 40.0,
    "crate_tare_kg": 40.0,
    "target_m2": 500.0,
    "target_sqft": 5381.95,
    "target_crates": 10
}

def ensure_storage_dirs():
    """Gerekli klasörleri oluşturur."""
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    os.makedirs(PRESETS_DIR, exist_ok=True)
    os.makedirs(EXPORTS_DIR, exist_ok=True)

def load_presets():
    """
    Kayıtlı reçeteleri yükler. SafePresetDict sayesinde hiçbir KeyError yaşanmaz.
    """
    raw_presets = {}
    
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                raw_presets = json.load(f)
        except Exception:
            pass

    # Varsayılan iki reçeteyi tanımla
    defaults = {
        "30.5x61x1.2 cm Marble Tile": {**DEFAULT_PRESET_FIELDS},
        "15x30.5x1 cm Travertine Tile": {
            **DEFAULT_PRESET_FIELDS,
            "customer_name": "Ionic Stone Ltd.",
            "po_number": "PO-2026-104",
            "product_name": "15x30.5x1 cm Travertine Tile",
            "product_code": "ION-TRV-1530",
            "p_length": 30.5,
            "p_width": 15.0,
            "p_thick": 1.0,
            "p_thickness": 1.0,
            "pcs_box": 10,
            "box_crate": 50
        }
    }

    # Birleştir
    combined = {**defaults, **raw_presets}
    
    # Her bir reçeteyi SafePresetDict ile zırhla
    final_presets = {}
    for name, data in combined.items():
        if isinstance(data, dict):
            safe_data = SafePresetDict(DEFAULT_PRESET_FIELDS)
            safe_data.update(data)
            final_presets[name] = safe_data
        else:
            final_presets[name] = data

    return final_presets

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
    """Esnek otomatik kurtarma kaydı."""
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
