import json
import os

TEMPLATES_DIR = "saved_templates"
PRESETS_DIR = "saved_presets"
RECOVERY_FILE = os.path.join(TEMPLATES_DIR, "_auto_recovery.json")

def ensure_storage_dirs():
    """Gerekli klasör yapılarını kontrol eder ve yoksa oluşturur."""
    for directory in [TEMPLATES_DIR, PRESETS_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)

def save_auto_recovery(cart, draft_data):
    """Anlık oturumu kurtarma dosyasına kaydeder."""
    ensure_storage_dirs()
    payload = {"cart": cart, "draft_data": draft_data}
    with open(RECOVERY_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)

def load_auto_recovery():
    """Arka plandaki son otomatik kurtarma verisini getirir."""
    if os.path.exists(RECOVERY_FILE):
        try:
            with open(RECOVERY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def clear_auto_recovery():
    """Kurtarma verisini siler."""
    if os.path.exists(RECOVERY_FILE):
        os.remove(RECOVERY_FILE)

def load_all_presets():
    """Sunucudaki tüm dinamik ürün reçetelerini (presets) yükler."""
    ensure_storage_dirs()
    presets = {}
    if os.path.exists(PRESETS_DIR):
        for fname in os.listdir(PRESETS_DIR):
            if fname.endswith(".json"):
                fpath = os.path.join(PRESETS_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        preset_key = data.get("preset_name", fname.replace(".json", ""))
                        presets[preset_key] = data
                except Exception:
                    pass
    return presets