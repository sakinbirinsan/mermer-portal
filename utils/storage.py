import json

import os

TEMPLATES_DIR = "saved_templates"

RECOVERY_FILE = os.path.join(TEMPLATES_DIR, "_auto_recovery.json")

def ensure_storage_dirs():

    if not os.path.exists(TEMPLATES_DIR):

        os.makedirs(TEMPLATES_DIR)

def save_auto_recovery(cart, draft_data):

    ensure_storage_dirs()

    payload = {

        "cart": cart,

        "draft_data": draft_data

    }

    with open(RECOVERY_FILE, "w", encoding="utf-8") as f:

        json.dump(payload, f, ensure_ascii=False, indent=4)

def load_auto_recovery():

    if os.path.exists(RECOVERY_FILE):

        try:

            with open(RECOVERY_FILE, "r", encoding="utf-8") as f:

                return json.load(f)

        except Exception:

            return None

    return None

def clear_auto_recovery():

    if os.path.exists(RECOVERY_FILE):

        os.remove(RECOVERY_FILE)
