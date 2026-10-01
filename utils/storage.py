import json
import os

STORAGE_FILE = "presets.json"
AUTO_RECOVERY_FILE = "auto_recovery.json"

# Görsellerdeki siparişlerden derlenen hazır varsayılan reçeteler
DEFAULT_PRESETS = {
    "FD - MAR VAN ICE THIN FLUT": {
        "sales_unit": "M²",
        "length_cm": 61.0,
        "width_cm": 15.0,
        "thickness_cm": 1.9,
        "density": 2.7,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 5.0,
        "pcs_per_box": 5,
        "boxes_in_crate": 60,
        "crate_tare_kg": 40.0
    },
    "FD - MAR CALA VERDE BAMBOO": {
        "sales_unit": "M²",
        "length_cm": 61.0,
        "width_cm": 15.0,
        "thickness_cm": 1.9,
        "density": 2.7,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 5.0,
        "pcs_per_box": 5,
        "boxes_in_crate": 60,
        "crate_tare_kg": 40.0
    },
    "FD - MAR CREMA ROYAL PETRA": {
        "sales_unit": "M²",
        "length_cm": 61.0,
        "width_cm": 15.0,
        "thickness_cm": 1.9,
        "density": 2.7,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 5.0,
        "pcs_per_box": 5,
        "boxes_in_crate": 52,
        "crate_tare_kg": 40.0
    },
    "FD - MAR FELIX DOLOMITE GREEN": {
        "sales_unit": "M²",
        "length_cm": 61.0,
        "width_cm": 15.0,
        "thickness_cm": 1.9,
        "density": 2.7,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 5.0,
        "pcs_per_box": 5,
        "boxes_in_crate": 72,
        "crate_tare_kg": 40.0
    },
    "FD - LIM LINEN IVY HON MOS": {
        "sales_unit": "M²",
        "length_cm": 61.0,
        "width_cm": 15.0,
        "thickness_cm": 1.9,
        "density": 2.5,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 5.0,
        "pcs_per_box": 5,
        "boxes_in_crate": 72,
        "crate_tare_kg": 40.0
    },
    "FD - MAR BLACK THIN FLUT": {
        "sales_unit": "M²",
        "length_cm": 61.0,
        "width_cm": 15.0,
        "thickness_cm": 1.9,
        "density": 2.7,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 5.0,
        "pcs_per_box": 4,
        "boxes_in_crate": 68,
        "crate_tare_kg": 40.0
    },
    "FD - MAR LUNA CREMA THIN FLUTE": {
        "sales_unit": "M²",
        "length_cm": 61.0,
        "width_cm": 15.0,
        "thickness_cm": 1.9,
        "density": 2.7,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 5.0,
        "pcs_per_box": 4,
        "boxes_in_crate": 68,
        "crate_tare_kg": 40.0
    },
    "FD - MAR BOTTOCINO PENCIL": {
        "sales_unit": "Adet",
        "length_cm": 30.5,
        "width_cm": 1.2,
        "thickness_cm": 1.9,
        "density": 2.7,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 3.0,
        "pcs_per_box": 20,
        "boxes_in_crate": 100,
        "crate_tare_kg": 35.0
    },
    "DN MERMER - TOROS BLACK EMR10/32": {
        "sales_unit": "M²",
        "length_cm": 91.5,
        "width_cm": 30.5,
        "thickness_cm": 1.9,
        "density": 2.7,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 5.0,
        "pcs_per_box": 2,
        "boxes_in_crate": 25,
        "crate_tare_kg": 45.0
    },
    "MOZAİKÇİ - COASTAL LIMESTONE 30.5x61": {
        "sales_unit": "M²",
        "length_cm": 61.0,
        "width_cm": 30.5,
        "thickness_cm": 1.2,
        "density": 2.5,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 4.0,
        "pcs_per_box": 4,
        "boxes_in_crate": 40,
        "crate_tare_kg": 40.0
    },
    "MOZAİKÇİ - COASTAL LIMESTONE 15.2x30.5": {
        "sales_unit": "M²",
        "length_cm": 30.5,
        "width_cm": 15.2,
        "thickness_cm": 1.0,
        "density": 2.5,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 4.0,
        "pcs_per_box": 20,
        "boxes_in_crate": 36,
        "crate_tare_kg": 40.0
    },
    "MOZAİKÇİ - KOMBASAN WHITE 7.5x15": {
        "sales_unit": "M²",
        "length_cm": 15.0,
        "width_cm": 7.5,
        "thickness_cm": 1.0,
        "density": 2.7,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 3.0,
        "pcs_per_box": 88,
        "boxes_in_crate": 42,
        "crate_tare_kg": 35.0
    },
    "IONIC - CARRARA BALIK PULU": {
        "sales_unit": "M²",
        "length_cm": 10.0,
        "width_cm": 10.0,
        "thickness_cm": 1.0,
        "density": 2.7,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 3.0,
        "pcs_per_box": 10,
        "boxes_in_crate": 36,
        "crate_tare_kg": 35.0
    },
    "IONIC - CARRARA 10x30.5 FAYANS": {
        "sales_unit": "M²",
        "length_cm": 30.5,
        "width_cm": 10.0,
        "thickness_cm": 1.0,
        "density": 2.7,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 3.0,
        "pcs_per_box": 30,
        "boxes_in_crate": 36,
        "crate_tare_kg": 40.0
    },
    "İVA - BOTTOCINO CHAIRRAIL 5x15": {
        "sales_unit": "Adet",
        "length_cm": 15.0,
        "width_cm": 5.0,
        "thickness_cm": 2.8,
        "density": 2.7,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 5.0,
        "pcs_per_box": 300,
        "boxes_in_crate": 1,
        "crate_tare_kg": 30.0
    },
    "İVA - SILVER TRAVERTINE BULLNOSE": {
        "sales_unit": "Adet",
        "length_cm": 15.0,
        "width_cm": 1.9,
        "thickness_cm": 1.9,
        "density": 2.4,
        "edge_trim": 2.0,
        "breakage_rate": 3.0,
        "saw_kerf_mm": 3.0,
        "pcs_per_box": 200,
        "boxes_in_crate": 1,
        "crate_tare_kg": 30.0
    }
}

def ensure_storage_dirs():
    """Gerekli klasörlerin varlığını kontrol eder."""
    pass

def load_presets():
    """Kayıtlı reçeteleri yükler. Varsayılanları her zaman üzerine ekler."""
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                return {**DEFAULT_PRESETS, **saved}
        except Exception:
            return DEFAULT_PRESETS
    return DEFAULT_PRESETS

def save_presets(presets):
    """Reçeteleri JSON dosyasına kaydeder."""
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(presets, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
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
