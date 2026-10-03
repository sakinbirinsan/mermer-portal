"""
Emre Doğaltaş Entegre Yönetim Portalı - Dinamik Reçete Ekle/Sil Destekli Sürüm
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import json
import os
import io
import base64
import requests
import hmac
import uuid
from datetime import date

st.set_page_config(
    page_title="Emre Doğaltaş Entegre Yönetim Portalı",
    page_icon="🗿",
    layout="wide"
)

# Klasör Yapılanması
TEMPLATES_DIR = "saved_templates"
PRESETS_DIR = "saved_presets"
DATA_DIR = "saved_data"
LOG_PHOTOS_DIR = os.path.join(DATA_DIR, "photos")
STOCK_FILE = os.path.join(DATA_DIR, "stock.json")
HISTORY_FILE = os.path.join(DATA_DIR, "order_history.json")
LOG_FILE = os.path.join(DATA_DIR, "daily_log.json")
KESIM_FILE = os.path.join(DATA_DIR, "cut_log.json")
ACTIVE_FILE = os.path.join(DATA_DIR, "active_cart.json")

for directory in [TEMPLATES_DIR, PRESETS_DIR, DATA_DIR, LOG_PHOTOS_DIR]:
    os.makedirs(directory, exist_ok=True)

# ------------------------------------------
# GÜVENLİK & YARDIMCI FONKSİYONLAR
# ------------------------------------------
def safe_name(text, default="adsiz"):
    """Dosya adından klasör atlatma (../) ve özel karakterleri temizler."""
    s_ = "".join(c for c in str(text) if c.isalnum() or c in (" ", "_", "-")).strip()
    return s_[:80] or default

# ---- Depolama katmanı: Supabase varsa veritabanı, yoksa yerel dosya ----
def _sb_conf():
    try:
        return str(st.secrets["SUPABASE_URL"]).rstrip("/"), str(st.secrets["SUPABASE_KEY"])
    except Exception:
        return None

SB = _sb_conf()
USE_DB = SB is not None

def _sb_call(method, params=None, body=None, extra=None):
    url, key = SB
    headers = {"apikey": key, "Content-Type": "application/json"}
    if not key.startswith("sb_"):
        headers["Authorization"] = f"Bearer {key}"
    if extra:
        headers.update(extra)
    r = requests.request(method, f"{url}/rest/v1/kv", headers=headers, params=params, json=body, timeout=20)
    r.raise_for_status()
    return r.json() if r.text else None

def _db_get_raw(key):
    rows = _sb_call("GET", {"key": f"eq.{key}", "select": "value"})
    return rows[0]["value"] if rows else None

def _db_list_raw(prefix, with_values):
    return _sb_call("GET", {"key": f"like.{prefix}*", "select": "key,value" if with_values else "key"})

_db_get = st.cache_data(ttl=60, show_spinner=False)(_db_get_raw)
_db_list = st.cache_data(ttl=60, show_spinner=False)(_db_list_raw)

def read_json(path, default, fresh=False):
    if USE_DB:
        v = _db_get_raw(path) if fresh else _db_get(path)
        return default if v is None else v
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def write_json(path, data, clear=True):
    if USE_DB:
        clean = json.loads(json.dumps(data, ensure_ascii=False, default=str))
        _sb_call("POST", {"on_conflict": "key"}, {"key": path, "value": clean},
                 {"Prefer": "resolution=merge-duplicates,return=minimal"})
        if clear:
            st.cache_data.clear()
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def delete_json(path, clear=True):
    if USE_DB:
        _sb_call("DELETE", {"key": f"eq.{path}"}, extra={"Prefer": "return=minimal"})
        if clear:
            st.cache_data.clear()
    elif os.path.exists(path):
        os.remove(path)

def exists_json(path):
    return (_db_get(path) is not None) if USE_DB else os.path.exists(path)

def list_names(dir_):
    if USE_DB:
        pre = dir_ + "/"
        return sorted(r["key"][len(pre):] for r in _db_list(pre, False))
    return sorted(f for f in os.listdir(dir_) if f.endswith(".json"))

def read_dir(dir_):
    if USE_DB:
        pre = dir_ + "/"
        return {r["key"][len(pre):]: r["value"] for r in _db_list(pre, True)}
    out = {}
    for f in os.listdir(dir_):
        if f.endswith(".json"):
            d = read_json(os.path.join(dir_, f), None)
            if d is not None:
                out[f] = d
    return out

def save_photo(name, raw):
    from PIL import Image
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    img.thumbnail((1280, 1280))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    data = buf.getvalue()
    if USE_DB:
        write_json(f"{LOG_PHOTOS_DIR}/{name}", {"b64": base64.b64encode(data).decode()})
    else:
        with open(os.path.join(LOG_PHOTOS_DIR, name), "wb") as pf:
            pf.write(data)

def load_photo(name):
    if USE_DB:
        d = read_json(f"{LOG_PHOTOS_DIR}/{name}", None)
        return base64.b64decode(d["b64"]) if d else None
    path = os.path.join(LOG_PHOTOS_DIR, name)
    if os.path.exists(path):
        with open(path, "rb") as pf:
            return pf.read()
    return None

def tg_on():
    try:
        return bool(st.secrets["TELEGRAM_TOKEN"] and st.secrets["TELEGRAM_CHAT_ID"])
    except Exception:
        return False

def notify(text):
    """Telegram grubuna mesaj gönderir. Bağlı değilse sessizce atlar."""
    if not tg_on():
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/sendMessage",
                          json={"chat_id": st.secrets["TELEGRAM_CHAT_ID"], "text": text}, timeout=10)
        return r.ok
    except Exception:
        return False

def log_history(project, cart):
    """Kaydedilen sipariş kalemlerini müşteri geçmişine yazar (aynı proje tekrar kaydedilirse günceller)."""
    hist = [h for h in read_json(HISTORY_FILE, []) if h.get("Proje") != project]
    for item in cart:
        rec = dict(item)
        rec["Tarih"] = str(date.today())
        rec["Proje"] = project
        hist.append(rec)
    write_json(HISTORY_FILE, hist)

def _get_app_password():
    try:
        pw = st.secrets.get("APP_PASSWORD")
    except Exception:
        pw = None
    return pw or os.environ.get("APP_PASSWORD")

APP_PASSWORD = _get_app_password()

def _get_users():
    try:
        return {str(k): str(v) for k, v in dict(st.secrets["users"]).items()}
    except Exception:
        return {}

USERS = _get_users()
if USERS:
    if not st.session_state.get("auth_ok"):
        st.title("🗿 Emre Doğaltaş Entegre Yönetim Portalı")
        u_in = st.selectbox("Kullanıcı", list(USERS.keys()))
        pw_in = st.text_input("Şifre", type="password")
        if st.button("Giriş"):
            if hmac.compare_digest(pw_in.encode(), USERS[u_in].encode()):
                st.session_state.auth_ok = True
                st.session_state.user_name = u_in
                st.rerun()
            else:
                st.error("Hatalı şifre.")
        st.stop()
    st.sidebar.markdown(f"👤 **{st.session_state.user_name}**")
    if st.sidebar.button("Çıkış yap"):
        for k in ("auth_ok", "user_name", "_active_sig", "_rec_sig"):
            st.session_state.pop(k, None)
        st.session_state.cart = []
        st.rerun()
else:
    if APP_PASSWORD and not st.session_state.get("auth_ok"):
        st.title("🗿 Emre Doğaltaş Entegre Yönetim Portalı")
        pw_in = st.text_input("Giriş şifresi", type="password")
        if st.button("Giriş"):
            if hmac.compare_digest(pw_in.encode(), str(APP_PASSWORD).encode()):
                st.session_state.auth_ok = True
                st.rerun()
            else:
                st.error("Hatalı şifre.")
        st.stop()
    if "user_name" not in st.session_state:
        st.session_state.user_name = "genel"
    st.sidebar.text_input("👤 Kullanıcı adınız", key="user_name", help="Her kullanıcının otomatik kurtarma sepeti ayrı tutulur.")
RECOVERY_FILE = os.path.join(TEMPLATES_DIR, f"_recovery_{safe_name(st.session_state.user_name, 'genel')}.json")
if USE_DB:
    st.sidebar.caption("☁️ Veritabanı bağlı: veriler kalıcı olarak saklanıyor.")
else:
    st.sidebar.caption("⚠️ Geçici yerel depolama: uygulama yeniden başlayınca veriler silinebilir.")

top_bar = st.container()
st.title("🗿 Emre Doğaltaş Üretim, Dizim, İhracat & Konteyner Portalı")
st.caption("Fabrika Müdürü, Dizim Şefi, İhracat Sorumlusu ve Yönetim İçin Ortak Operasyon Paneli")
st.markdown("---")

# ------------------------------------------
# REÇETE (PRESET) YÖNETİM FONKSİYONLARI
# ------------------------------------------
def load_all_presets():
    """Kayıtlı tüm ürün reçetelerini yükler."""
    presets = {}
    for fname, data in read_dir(PRESETS_DIR).items():
        if isinstance(data, dict):
            presets[data.get("preset_name", fname.replace(".json", ""))] = data
    return presets

if "cart" not in st.session_state:
    st.session_state.cart = []

if "draft_data" not in st.session_state:
    st.session_state.draft_data = {}

# Ortak aktif sepet (herkes aynı packing list havuzunu görür)
def _cart_sig(cart):
    return json.dumps(cart, ensure_ascii=False, sort_keys=True, default=str) if cart else ""

def push_active_cart():
    sig = _cart_sig(st.session_state.cart)
    if sig == st.session_state.get("_active_sig"):
        return
    write_json(ACTIVE_FILE, {"cart": st.session_state.cart, "sig": sig,
                             "by": st.session_state.user_name, "at": str(date.today())}, clear=False)
    st.session_state["_active_sig"] = sig

def sync_active_cart():
    db = read_json(ACTIVE_FILE, {}, fresh=True)
    db_sig = db.get("sig", "")
    mine = st.session_state.get("_active_sig")
    cur = _cart_sig(st.session_state.cart)
    if mine is None or (cur == mine and db_sig != mine):
        st.session_state.cart = db.get("cart", []) if db_sig else []
        st.session_state["_active_sig"] = db_sig
    elif cur != mine:
        push_active_cart()

sync_active_cart()

# Otomatik Kurtarma
rec_data = read_json(RECOVERY_FILE, {}, fresh=True) if not st.session_state.cart else {}
if rec_data.get("cart"):
    st.warning("⚠️ **Son Oturum Kurtarıldı:** Son çalışmanız arka plandan getirildi.")
    if st.button("🔄 Son Kurtarılan Verileri Sepete Yükle"):
        st.session_state.cart = rec_data.get("cart", [])
        st.rerun()

def save_auto_recovery():
    push_active_cart()
    payload = {"cart": st.session_state.cart, "draft_data": st.session_state.draft_data}
    sig = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    if st.session_state.get("_rec_sig") == sig:
        return
    st.session_state["_rec_sig"] = sig
    write_json(RECOVERY_FILE, payload, clear=False)

# ------------------------------------------
# YAN MENÜ (SIDEBAR): HIZLI TASLAK YÜKLEME & SİLME
# ------------------------------------------
st.sidebar.header("📁 Sunucudaki Kayıtlı Taslaklar")

saved_files = [f for f in list_names(TEMPLATES_DIR) if not f.startswith("_")]

if saved_files:
    selected_template = st.sidebar.selectbox("Hızlı Taslak Seçin:", ["Seçiniz..."] + saved_files)
    
    if selected_template != "Seçiniz...":
        template_path = os.path.join(TEMPLATES_DIR, selected_template)
        t_data = read_json(template_path, {})
            
        st.sidebar.success(f"📌 **Proje:** {t_data.get('proje_kodu', '')}")
        st.sidebar.info(f"🟢 **Durum:** {t_data.get('onay_durumu', '')}")
        if t_data.get("yonetici_notu"):
            st.sidebar.caption(f"📝 **Not:** {t_data.get('yonetici_notu')}")
            
        col_sb1, col_sb2 = st.columns([3, 1])
        with col_sb1:
            if st.button("⚡ Ekrana Yükle", width="stretch"):
                st.session_state.cart = t_data.get("sepet", [])
                save_auto_recovery()
                st.toast(f"{selected_template} başarıyla yüklendi!", icon="🚀")
                st.rerun()
        with col_sb2:
            if st.button("🗑️", help="Bu taslağı sunucudan kalıcı olarak sil", width="stretch"):
                delete_json(template_path)
                st.toast(f"{selected_template} silindi!", icon="🗑️")
                st.rerun()
else:
    st.sidebar.info("Henüz sunucuda kayıtlı taslak bulunmuyor.")

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Tüm Sepeti Temizle", width="stretch"):
    st.session_state.cart = []
    delete_json(RECOVERY_FILE, clear=False)
    st.session_state.pop("_rec_sig", None)
    write_json(ACTIVE_FILE, {"cart": [], "sig": "", "by": st.session_state.user_name, "at": str(date.today())}, clear=False)
    st.session_state["_active_sig"] = ""
    st.rerun()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📐 1. Ürün, Reçete & Stok Parametreleri", 
    "🧩 2. Dizim, Şinik & Kutu Planı",
    "🛒 3. Sipariş Havuzu & Packing List", 
    "🚢 4. İhracat & Konteyner Doluluk",
    "💾 5. Yönetici Şablon & Onay Yönetimi"
])

# ------------------------------------------
# TAB 1: DİNAMİK REÇETE, ÜRÜN & STOK HESABI
# ------------------------------------------
with tab1:
    st.header("1. Ürün Reçeteleri (Preset), Müşteri ve Kasa Spesifikasyonları")
    
    # REÇETE SEÇİM VE SİLME ALANI
    all_presets = load_all_presets()
    preset_options = ["Özel / Manuel Giriş"] + list(all_presets.keys())
    
    col_p1, col_p2 = st.columns([3, 1])
    with col_p1:
        selected_preset_name = st.selectbox(
            "⭐ Kayıtlı Standart Ürün Reçeteleri (Preset):",
            preset_options
        )
    
    preset_data = all_presets.get(selected_preset_name)
    
    with col_p2:
        st.write("") # Hizalama boşluğu
        if selected_preset_name != "Özel / Manuel Giriş" and preset_data:
            if st.button("🗑️ Seçili Reçeteyi Kütüphaneden Sil", width="stretch"):
                preset_file_name = preset_data.get("file_name")
                if preset_file_name:
                    file_to_del = os.path.join(PRESETS_DIR, os.path.basename(preset_file_name))
                    if exists_json(file_to_del):
                        delete_json(file_to_del)
                        st.toast(f"'{selected_preset_name}' reçetesi silindi!", icon="🗑️")
                        st.rerun()

    if preset_data:
        st.success(f"✅ **{selected_preset_name}** reçetesinin ambalaj ve ebat standartları yüklendi!")

    st.markdown("---")
    col_cust1, col_cust2 = st.columns(2)
    with col_cust1:
        default_cust = preset_data["customer_name"] if preset_data else st.session_state.draft_data.get("customer_name", "Floor & Decor Stone Corp.")
        customer_name = st.text_input("Müşteri / Şirket Adı", value=default_cust)
    with col_cust2:
        default_po = preset_data["po_number"] if preset_data else st.session_state.draft_data.get("po_number", "PO-2026-089")
        po_number = st.text_input("Müşteri PO / Sipariş No", value=default_po)

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📦 Ürün & Satış Tanımı")
        default_pname = preset_data["product_name"] if preset_data else st.session_state.draft_data.get("product_name", "bullnose / pencil")
        product_name = st.text_input("Ürün Adı / Kodu", value=default_pname)
        
        default_ptype_idx = ["Flute / Moulding", "Mozaik", "Ebatlı Mermer / Plaka"].index(preset_data["product_type"]) if preset_data and "product_type" in preset_data else 0
        product_type = st.selectbox("Ürün Tipi", ["Flute / Moulding", "Mozaik", "Ebatlı Mermer / Plaka"], index=default_ptype_idx)
        
        sales_unit = st.radio("Satış / Hesaplama Birimi", ["Adet (Pcs)", "m² Bazlı"], horizontal=True)
        unit_system = st.radio("Ölçü Birimi System", ["Metrik (cm / m²)", "Imperial (inch / sqft)"], horizontal=True)
        
        if "Metrik" in unit_system:
            def_l = preset_data["p_length"] if preset_data else st.session_state.draft_data.get("p_length", 30.5)
            def_w = preset_data["p_width"] if preset_data else st.session_state.draft_data.get("p_width", 2.0)
            def_t = preset_data["p_thickness"] if preset_data else st.session_state.draft_data.get("p_thickness", 2.0)
            
            p_length = st.number_input("Ürün / Parça Boyu (cm)", value=float(def_l), step=0.5)
            p_width = st.number_input("Ürün / Parça Eni (cm)", value=float(def_w), step=0.1)
            p_thickness = st.number_input("Kalınlık (cm)", value=float(def_t), step=0.1)
        else:
            p_length_in = st.number_input("Ürün Boyu (inch)", value=12.0, step=0.5)
            p_width_in = st.number_input("Ürün Eni (inch)", value=0.78, step=0.05)
            p_thickness_in = st.number_input("Kalınlık (inch)", value=0.78, step=0.05)
            
            p_length = p_length_in * 2.54
            p_width = p_width_in * 2.54
            p_thickness = p_thickness_in * 2.54
            
        def_density = preset_data["density"] if preset_data else 2.7
        density = st.number_input("Taş Yoğunluğu (gr/cm³)", value=float(def_density), step=0.1)
        piece_m2 = (p_length / 100) * (p_width / 100)

    with col2:
        st.subheader("🏬 Stok & İmalat Adımları")
        
        required_ops = st.multiselect(
            "Yapılacak Operasyonlar",
            ["Ebatlama / Kesim Gerekli", "Dizim / File / Şinik Gerekli", "Hazır Stok (Sadece Paketleme)"],
            default=["Ebatlama / Kesim Gerekli", "Dizim / File / Şinik Gerekli"]
        )

        def_tpcs = preset_data["target_pcs"] if preset_data else st.session_state.draft_data.get("target_pcs", 4000)
        
        if sales_unit == "Adet (Pcs)":
            target_pcs = st.number_input("Net Sipariş Miktarı (Adet)", value=int(def_tpcs), step=100)
            target_m2 = target_pcs * piece_m2
            stock_qty = st.number_input("Mevcut Hazır Stok (Adet)", value=0, step=100)
            needed_prod_pcs = max(0, target_pcs - stock_qty)
            needed_prod_m2 = needed_prod_pcs * piece_m2
            st.caption(f"İmal Edilecek Net Miktar: **{needed_prod_pcs:,} Adet** ({needed_prod_m2:.2f} m²)")
        else:
            target_m2 = st.number_input("Net Sipariş Miktarı (m²)", value=st.session_state.draft_data.get("target_m2", 150.0), step=10.0)
            target_pcs = math.ceil(target_m2 / piece_m2) if piece_m2 > 0 else 0
            stock_qty = st.number_input("Mevcut Hazır Stok (m²)", value=0.0, step=10.0)
            needed_prod_m2 = max(0.0, target_m2 - stock_qty)
            needed_prod_pcs = math.ceil(needed_prod_m2 / piece_m2) if piece_m2 > 0 else 0
            st.caption(f"İmal Edilecek Net Miktar: **{needed_prod_m2:.2f} m²** ({needed_prod_pcs:,} Adet)")

        saw_kerf = st.number_input("Testere Payı (mm)", value=1.0, step=0.5)
        edge_trim = st.number_input("Kenar Fire / Kalibre (%)", value=0.0, step=0.5)
        breakage_rate = st.number_input("Kırılma / Seleksiyon Fire (%)", value=15.0, step=0.5)
        
        total_fire_pct = edge_trim + breakage_rate + ((saw_kerf / 10) * 2)
        required_gross_m2 = needed_prod_m2 * (1 + (total_fire_pct / 100))
        required_gross_pcs = math.ceil(needed_prod_pcs * (1 + (total_fire_pct / 100)))
        
        st.info(f"**Toplam Üretim Firesi:** %{total_fire_pct:.2f}")
        if sales_unit == "Adet (Pcs)":
            st.warning(f"**Gerekli Brüt Taş (Depodan Çıkacak):** {required_gross_pcs:,} Adet ({required_gross_m2:.2f} m²)")
        else:
            st.warning(f"**Gerekli Brüt Taş (Depodan Çıkacak):** {required_gross_m2:.2f} m²")

    with col3:
        st.subheader("🪵 Ahşap Kasa Dış Ölçüleri")
        def_cl = preset_data["crate_length"] if preset_data else 101.0
        def_cw = preset_data["crate_width"] if preset_data else 101.0
        def_ch = preset_data["crate_height"] if preset_data else 40.0
        def_ctare = preset_data["crate_tare_kg"] if preset_data else 35.0

        crate_length = st.number_input("Kasa Dış Boy (cm)", value=float(def_cl), step=1.0)
        crate_width = st.number_input("Kasa Dış En (cm)", value=float(def_cw), step=1.0)
        crate_height = st.number_input("Kasa Dış Yükseklik (cm)", value=float(def_ch), step=1.0)
        crate_tare_kg = st.number_input("Boş Kasa Ağırlığı (kg)", value=float(def_ctare), step=5.0, key=f"ctare_{selected_preset_name}")
        is_stackable = st.checkbox("Üst Üste İstiflenebilir (Stackable)", value=True)

    # REÇETE KAYIT BÖLÜMÜ
    st.markdown("---")
    st.subheader("💾 Ekrandaki Parametreleri Yeni Reçete Olarak Kaydet")
    col_pr1, col_pr2 = st.columns([3, 1])
    with col_pr1:
        new_preset_title = st.text_input("Reçete Adı (Örn: [F&D] Marble Thin Black Flute)", value=(selected_preset_name if preset_data else f"[{customer_name}] {product_name} ({p_length}x{p_width} cm)"))
    with col_pr2:
        st.write("")
        if st.button("♻️ Bu Reçeteyi Güncelle" if new_preset_title in all_presets else "💾 Reçeteyi Kütüphaneye Ekle", width="stretch"):
            clean_filename = "".join([c for c in new_preset_title if c.isalnum() or c in (' ', '_', '-')]).rstrip() + ".json"
            _gv = lambda k, d: st.session_state.get(f"{k}_{selected_preset_name}", d)
            _pd = preset_data or {}
            save_preset_payload = {
                "preset_name": new_preset_title,
                "file_name": clean_filename,
                "customer_name": customer_name,
                "po_number": po_number,
                "product_name": product_name,
                "product_type": product_type,
                "sales_unit": sales_unit,
                "p_length": p_length,
                "p_width": p_width,
                "p_thickness": p_thickness,
                "density": density,
                "pcs_per_box": _gv("pcs_per_box", _pd.get("pcs_per_box", 24)),
                "boxes_in_crate": _gv("boxes_in_crate", _pd.get("boxes_in_crate", 36)),
                "thin_sinik_per_box": _gv("thin_s", _pd.get("thin_sinik_per_box", 1)),
                "thick_sinik_per_box": _gv("thick_s", _pd.get("thick_sinik_per_box", 0)),
                "net_kg_per_pc": float(_gv("netpc", _pd.get("net_kg_per_pc", 0.0))),
                "weight_src": (("katalog" if (_pd.get("weight_src") == "katalog" and abs(float(_gv("netpc", 0.0)) - float(_pd.get("net_kg_per_pc", 0.0))) < 1e-9) else "ölçülmüş") if float(_gv("netpc", _pd.get("net_kg_per_pc", 0.0))) > 0 else "tahmini"),
                "box_type": _gv("boxtype", _pd.get("box_type", "Karton Kutu")),
                "crate_length": crate_length,
                "crate_width": crate_width,
                "crate_height": crate_height,
                "crate_tare_kg": crate_tare_kg,
                "target_pcs": target_pcs
            }
            write_json(os.path.join(PRESETS_DIR, clean_filename), save_preset_payload)
            st.toast(f"'{new_preset_title}' reçetesi kaydedildi!", icon="✅")
            st.rerun()

# ------------------------------------------
# TAB 2: DİZİM, ŞİNİK & KUTULAMA PLANLAMA
# ------------------------------------------
with tab2:
    st.header("🧩 Dizim Şefi & Kutulama Operasyon Paneli")
    st.caption(f"Aktif Hesaplama Modu: **{sales_unit}**")
    
    col_d1, col_d2, col_d3 = st.columns(3)
    
    with col_d1:
        st.subheader("📦 Kutu & Kasalama Hesabı")
        
        def_pcs_box = preset_data["pcs_per_box"] if preset_data else 24
        def_boxes_crate = preset_data["boxes_in_crate"] if preset_data else 36

        pcs_per_box = st.number_input("1 Kutu İçi Taş / Parça Adedi", value=int(def_pcs_box), step=1, key=f"pcs_per_box_{selected_preset_name}")
        boxes_in_crate = st.number_input("1 Kasadaki Kutu Sayısı", value=int(def_boxes_crate), step=1, key=f"boxes_in_crate_{selected_preset_name}")
        _stock_now = read_json(STOCK_FILE, [])
        box_opts = list(dict.fromkeys(["Karton Kutu", "Strafor Kutu", "5'li Paket", "10'lu Paket"] + [r.get("Kalem") for r in _stock_now if r.get("Tür") == "Kutu" and r.get("Kalem")]))
        _def_bt = (preset_data or {}).get("box_type", "Karton Kutu")
        box_type = st.selectbox("Kutu / Paket Tipi", box_opts, index=box_opts.index(_def_bt) if _def_bt in box_opts else 0, key=f"boxtype_{selected_preset_name}")
        
        box_net_m2 = pcs_per_box * piece_m2
        if sales_unit == "Adet (Pcs)":
            st.text_input("1 Kutu İçi Net m² (Otomatik)", value=f"{box_net_m2:.3f} m²", disabled=True)
        else:
            box_net_m2 = st.number_input("1 Kutu İçi Net m²", value=float(f"{box_net_m2:.2f}"), step=0.01)
        
        crate_pcs_capacity = pcs_per_box * boxes_in_crate
        crate_m2_capacity = crate_pcs_capacity * piece_m2
        
        if sales_unit == "Adet (Pcs)":
            total_boxes = math.ceil(target_pcs / pcs_per_box) if pcs_per_box > 0 else 1
            needed_crates = math.ceil(target_pcs / crate_pcs_capacity) if crate_pcs_capacity > 0 else 1
        else:
            needed_crates = math.ceil(target_m2 / crate_m2_capacity) if crate_m2_capacity > 0 else 1
            total_boxes = needed_crates * boxes_in_crate

        calc_pc_kg = piece_m2 * (p_thickness / 100) * (density * 1000)
        def_netpc = float((preset_data or {}).get("net_kg_per_pc", 0.0))
        real_net_pc = st.number_input("Gerçek parça ağırlığı (kg/adet), 0 = formülle hesapla", value=def_netpc, step=0.01, format="%.3f", key=f"netpc_{selected_preset_name}")
        net_pc_used = real_net_pc if real_net_pc > 0 else calc_pc_kg
        _pd_src = (preset_data or {}).get("weight_src", "")
        weight_src = ("katalog" if (_pd_src == "katalog" and abs(real_net_pc - def_netpc) < 1e-9) else "ölçülmüş") if real_net_pc > 0 else "tahmini"
        stone_weight = crate_pcs_capacity * net_pc_used
        crate_gross_weight = stone_weight + crate_tare_kg
        with st.expander("⚖️ Gerçek tartıdan ayarla"):
            m_net = st.number_input("Tartılan 1 dolu kasa NET (kg)", value=0.0, step=5.0, key=f"mnet_{selected_preset_name}")
            m_gross = st.number_input("Tartılan 1 dolu kasa BRÜT (kg)", value=0.0, step=5.0, key=f"mgross_{selected_preset_name}")
            if m_net > 0 and crate_pcs_capacity > 0:
                st.caption(f"→ parça başı net: {m_net / crate_pcs_capacity:.3f} kg" + (f" | kasa darası: {m_gross - m_net:.0f} kg" if m_gross > m_net else ""))
                def _apply_weights(n=m_net, g=m_gross, cap=crate_pcs_capacity, k=selected_preset_name):
                    st.session_state[f"netpc_{k}"] = round(n / cap, 4)
                    if g > n:
                        st.session_state[f"ctare_{k}"] = float(g - n)
                st.button("Bu değerleri uygula", on_click=_apply_weights, key=f"apply_w_{selected_preset_name}")
        
        if sales_unit == "Adet (Pcs)":
            st.info(f"**1 Kasa Kapasitesi:** {crate_pcs_capacity} Adet ({crate_m2_capacity:.2f} m²)")
        else:
            st.info(f"**1 Kasa Kapasitesi:** {crate_m2_capacity:.2f} m²")
            
        st.success(f"**1 Kasa Net:** {stone_weight:.0f} kg  |  **Brüt:** {crate_gross_weight:.1f} kg  ({weight_src})")

    with col_d2:
        st.subheader("📐 Kutu İçi Kalıp & Şinik/Şilte")
        def_thick_s = preset_data["thick_sinik_per_box"] if preset_data else 0
        def_thin_s = preset_data["thin_sinik_per_box"] if preset_data else 1

        thick_sinik_per_box = st.number_input("1 Kutu İçi Kalın Şinik Adedi", value=int(def_thick_s), step=1, key=f"thick_s_{selected_preset_name}")
        thin_sinik_per_box = st.number_input("1 Kutu İçi İnce Şinik Adedi", value=int(def_thin_s), step=1, key=f"thin_s_{selected_preset_name}")
        
        total_thick_sinik = total_boxes * thick_sinik_per_box
        total_thin_sinik = total_boxes * thin_sinik_per_box
        
        st.caption(f"Toplam Gerekli Kutu: **{total_boxes:,} Adet**")
        st.warning(f"**Kalın Şinik İhtiyacı:** {total_thick_sinik:,.0f} Adet")
        st.warning(f"**İnce Şinik İhtiyacı:** {total_thin_sinik:,.0f} Adet")

    with col_d3:
        st.subheader("👥 Esnek Vardiya & Ürün Dizim Hızı")
        
        is_dizim_needed = "Dizim / File / Şinik Gerekli" in required_ops
        
        if not is_dizim_needed or needed_prod_pcs == 0:
            st.success("🎉 **Dizim İşçiliği Gerekmiyor!** (Ürün stokta hazır veya dizimsiz sevk edilecek)")
            needed_days = 0
            daily_total_sheets = 0
            daily_crates = 0
        else:
            workers_count = st.number_input("Tezgahtaki İşçi Sayısı", value=2, step=1)
            daily_total_sheets = st.number_input("Bu Ürün İçin Ekip Günlük Toplam Üretim (Adet/Parça)", value=4000, step=100)
            
            daily_total_m2 = daily_total_sheets * piece_m2
            daily_crates = daily_total_sheets / crate_pcs_capacity if crate_pcs_capacity > 0 else 0
            
            if sales_unit == "Adet (Pcs)":
                needed_days = math.ceil(needed_prod_pcs / daily_total_sheets) if daily_total_sheets > 0 else 1
                st.metric(
                    "Günlük Ekip Dizim Kapasitesi", 
                    f"{daily_total_sheets:,.0f} Adet / Gün / {daily_crates:.2f} Kasa", 
                    f"~{daily_total_m2:.2f} m² / Gün"
                )
            else:
                needed_days = math.ceil(needed_prod_m2 / daily_total_m2) if daily_total_m2 > 0 else 1
                st.metric(
                    "Günlük Ekip Dizim Kapasitesi", 
                    f"{daily_total_m2:.2f} m² / Gün / {daily_crates:.2f} Kasa", 
                    f"{daily_total_sheets:,.0f} Adet"
                )
                
        st.metric("Tahmini İmalat Süresi", f"{needed_days} İş Günü")

    st.markdown("---")
    col_add1, col_add2 = st.columns([3, 1])
    with col_add1:
        if st.button("➕ Bu Ürün & Müşteri Siparişini Sepete Ekle", width="stretch"):
            st.session_state.cart.append({
                "Müşteri": customer_name,
                "PO / Sipariş No": po_number,
                "Ürün Adı": product_name,
                "Tip": product_type,
                "Satış Birimi": sales_unit,
                "Ebat (cm)": f"{p_length:.1f}x{p_width:.1f}x{p_thickness:.1f}",
                "Stok Durumu": f"{stock_qty} ({sales_unit}) Stokta",
                "İmal Edilecek": f"{needed_prod_pcs:,} Adet" if sales_unit == "Adet (Pcs)" else f"{needed_prod_m2:.2f} m²",
                "İmalat Süresi": f"{needed_days} Gün",
                "Kutu İçi Adet": pcs_per_box,
                "Kutu İçi m²": round(box_net_m2, 3),
                "Kasadaki Kutu": boxes_in_crate,
                "1 Kasa Kapasite (Adet)": crate_pcs_capacity,
                "1 Kasa Kapasite (m²)": crate_m2_capacity,
                "1 Kasa Ağırlık (kg)": crate_gross_weight,
                "1 Kasa Net (kg)": round(stone_weight, 1),
                "Ağırlık Kaynağı": weight_src,
                "Kutu Tipi": box_type,
                "Kalın Şinik / Kutu": thick_sinik_per_box,
                "İnce Şinik / Kutu": thin_sinik_per_box,
                "Kasa Sayısı": int(needed_crates),
                "Kasa L": crate_length,
                "Kasa W": crate_width,
                "Kasa H": crate_height,
                "Stackable": "Evet" if is_stackable else "Hayır"
            })
            save_auto_recovery()
            st.toast(f"{customer_name} - {product_name} sepete eklendi ve yedeklendi!", icon="✅")

# ------------------------------------------
# TAB 3: SIPARIS HAVUZU & PACKING LIST
# ------------------------------------------
with tab3:
    st.header("🛒 Sipariş Havuzu & Çeki Listesi (Packing List)")
    
    if not st.session_state.cart:
        st.info("Sepet henüz boş. 1. ve 2. sekmelerden ürün ekleyebilirsiniz.")
    else:
        st.caption("💡 **Düzenleme & Silme:** Konteynere göre kasa sayısını değiştirebilir veya silmek istediğiniz ürünü tekil olarak listeden çıkarabilirsiniz.")
        
        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            item_labels = [f"{i+1}. {item['Müşteri']} - {item['PO / Sipariş No']} | {item['Ürün Adı']} ({item['Ebat (cm)']})" for i, item in enumerate(st.session_state.cart)]
            selected_item_to_delete = st.selectbox("Silinecek Kalemi Seçin:", item_labels)
        with col_del2:
            st.write("") 
            if st.button("🗑 Seçili Siparişi Sil", width="stretch"):
                delete_index = item_labels.index(selected_item_to_delete)
                deleted_item = st.session_state.cart.pop(delete_index)
                save_auto_recovery()
                st.toast(f"'{deleted_item['Ürün Adı']}' siparişten silindi!", icon="🗑️")
                st.rerun()

        st.markdown("---")
        df_cart = pd.DataFrame(st.session_state.cart)

        edited_df = st.data_editor(
            df_cart,
            num_rows="dynamic",
            column_config={
                "Kasa Sayısı": st.column_config.NumberColumn(
                    "Kasa Sayısı",
                    help="Kasa sayısını artırıp azaltabilirsiniz.",
                    min_value=1, max_value=100, step=1, format="%d 📦"
                ),
                "Kutu İçi Adet": st.column_config.NumberColumn("1 Kutu İçi Adet", format="%d Pcs"),
                "Kutu İçi m²": st.column_config.NumberColumn("1 Kutu İçi m²", format="%.3f m²"),
                "Kasadaki Kutu": st.column_config.NumberColumn("1 Kasadaki Kutu", format="%d Kutu"),
            },
            disabled=[col for col in df_cart.columns if col != "Kasa Sayısı"],
            width="stretch",
            hide_index=True
        )

        updated_cart = []
        for index, row in edited_df.iterrows():
            crates = row["Kasa Sayısı"]
            crate_pcs_cap = row["1 Kasa Kapasite (Adet)"]
            crate_m2_cap = row["1 Kasa Kapasite (m²)"]
            crate_wt = row["1 Kasa Ağırlık (kg)"]
            boxes_per_crate = row["Kasadaki Kutu"]

            tot_pcs = crates * crate_pcs_cap
            tot_m2 = crates * crate_m2_cap
            tot_boxes = crates * boxes_per_crate
            tot_wt = crates * crate_wt
            _n = row.get("1 Kasa Net (kg)")
            tot_net = round(crates * _n, 1) if _n is not None and pd.notna(_n) else None

            row_copy = dict(row)
            row_copy["Toplam Adet"] = tot_pcs
            row_copy["Toplam m²"] = round(tot_m2, 2)
            row_copy["Toplam Kutu"] = tot_boxes
            row_copy["Toplam Ağırlık (kg)"] = round(tot_wt, 1)
            row_copy["Toplam Net Ağırlık (kg)"] = tot_net
            row_copy["Sipariş Miktarı"] = f"{tot_pcs:,} Adet" if row["Satış Birimi"] == "Adet (Pcs)" else f"{tot_m2:.2f} m²"

            updated_cart.append(row_copy)

        st.session_state.cart = updated_cart
        save_auto_recovery()
        df_updated = pd.DataFrame(updated_cart)

        st.subheader("📊 Genel Konteyner Özeti")
        c_p1, c_p2, c_p3, c_p4 = st.columns(4)
        tot_crates = df_updated["Kasa Sayısı"].sum()
        tot_m2 = df_updated["Toplam m²"].sum()
        tot_pcs = df_updated["Toplam Adet"].sum()
        tot_kg = df_updated["Toplam Ağırlık (kg)"].sum()
        tot_boxes = df_updated["Toplam Kutu"].sum()
        
        c_p1.metric("TOPLAM KASA", f"{tot_crates} Kasa")
        c_p2.metric("TOPLAM METRAJ & ADET", f"{tot_pcs:,.0f} Pcs", f"{tot_m2:.2f} m²")
        c_p3.metric("TOPLAM BRÜT AĞIRLIK", f"{tot_kg:,.0f} kg", f"Net: {df_updated['Toplam Net Ağırlık (kg)'].sum():,.0f} kg | {tot_kg * 2.20462:,.0f} lbs")
        c_p4.metric("TOPLAM KUTU", f"{tot_boxes:,.0f} Kutu")

        st.markdown("---")
        st.subheader("🏢 Müşteri / Firma Bazlı Ayrıştırılmış Packing List")
        
        unique_customers = df_updated["Müşteri"].unique()
        
        for cust in unique_customers:
            cust_df = df_updated[df_updated["Müşteri"] == cust]
            
            with st.expander(f"📌 Müşteri: **{cust}** (Sipariş Detayı İçin Tıklayın)", expanded=True):
                st.dataframe(
                    cust_df[["PO / Sipariş No", "Ürün Adı", "Ebat (cm)", "Stok Durumu", "İmalat Süresi", "Kasa Sayısı", "Toplam Kutu", "Sipariş Miktarı", "Toplam m²", "Toplam Net Ağırlık (kg)", "Toplam Ağırlık (kg)"]],
                    width="stretch",
                    hide_index=True
                )
                
                c_c1, c_c2, c_c3, c_c4 = st.columns(4)
                c_c1.markdown(f"**Müşteri Kasa:** {cust_df['Kasa Sayısı'].sum()} Kasa")
                c_c2.markdown(f"**Müşteri Kutu:** {cust_df['Toplam Kutu'].sum():,.0f} Kutu")
                c_c3.markdown(f"**Müşteri Miktar:** {cust_df['Toplam Adet'].sum():,.0f} Adet / {cust_df['Toplam m²'].sum():.2f} m²")
                c_c4.markdown(f"**Müşteri Ağırlık:** {cust_df['Toplam Ağırlık (kg)'].sum():,.0f} kg")

        st.markdown("---")
        def build_packing_xlsx(df):
            buf = io.BytesIO()
            drop_cols = ["Kasa L", "Kasa W", "Kasa H"]
            with pd.ExcelWriter(buf, engine="openpyxl") as xw:
                df.drop(columns=drop_cols, errors="ignore").to_excel(xw, sheet_name="Genel", index=False)
                for i, cust in enumerate(df["Müşteri"].unique()):
                    nm = "".join(c for c in str(cust) if c not in "[]:*?/\\")
                    df[df["Müşteri"] == cust].drop(columns=drop_cols, errors="ignore").to_excel(xw, sheet_name=f"{i+1}-{nm}"[:31], index=False)
            return buf.getvalue()

        st.download_button("📊 Packing List'i Excel Olarak İndir", data=build_packing_xlsx(df_updated),
                           file_name=f"packing_list_{date.today()}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           width="stretch")

# ------------------------------------------
# TAB 4: İHRACAT & KONTEYNER DOLULUK
# ------------------------------------------
with tab4:
    st.header("🚢 İhracat, Liman Bazlı Min/Max Tonaj Limitleri & 3D Visualizer")
    
    col_ex1, col_ex2 = st.columns(2)
    
    with col_ex1:
        container_type = st.selectbox("Konteyner Tipi", [
            "20'lik Standart (20' DC) - Max Vol: 33.2 m³",
            "40'lık Standart (40' DC) - Max Vol: 67.7 m³",
            "40'lık High Cube (40' HC) - Max Vol: 76.2 m³"
        ])
    
    with col_ex2:
        port_preset = st.selectbox("ABD Varış Limanı / Tonaj Şablonu (Weight Limits)", [
            "Savannah 20' & 40' (Min: 24,040 kg / Max: 27,215 kg)",
            "Houston 20' & 40' (Min: 24,040 kg / Max: 27,215 kg)",
            "LA/Long Beach - 20' & 40' MORENO (Min: 18,143 kg / Max: 20,865 kg)",
            "Baltimore - 20' (Min: 24,040 kg / Max: 27,216 kg)",
            "Baltimore - 40' (Min: 19,505 kg / Max: 27,216 kg)",
            "LA Transload - 20' & 40' CARSON (Min: 20,865 kg / Max: 26,762 kg)",
            "Özel Manuel Limit Gir"
        ])

    if "Savannah" in port_preset or "Houston" in port_preset:
        min_allowed_kg, max_allowed_kg = 24040, 27215
    elif "MORENO" in port_preset:
        min_allowed_kg, max_allowed_kg = 18143, 20865
    elif "Baltimore - 20'" in port_preset:
        min_allowed_kg, max_allowed_kg = 24040, 27216
    elif "Baltimore - 40'" in port_preset:
        min_allowed_kg, max_allowed_kg = 19505, 27216
    elif "CARSON" in port_preset:
        min_allowed_kg, max_allowed_kg = 20865, 26762
    else:
        col_m_in1, col_m_in2 = st.columns(2)
        min_allowed_kg = col_m_in1.number_input("Özel Min Limit (kg)", value=18000)
        max_allowed_kg = col_m_in2.number_input("Özel Max Limit (kg)", value=24000)

    if "20'" in container_type:
        c_l, c_w, c_h = 589.8, 235.2, 239.3
    elif "40' HC" in container_type:
        c_l, c_w, c_h = 1203.2, 235.2, 269.8
    else:
        c_l, c_w, c_h = 1203.2, 235.2, 239.3

    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        total_weight_kg = df_cart["Toplam Ağırlık (kg)"].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Ağırlık Limiti Aralığı (Min - Max)", f"{min_allowed_kg:,.0f} kg - {max_allowed_kg:,.0f} kg", f"{min_allowed_kg*2.20462:,.0f} - {max_allowed_kg*2.20462:,.0f} lbs")
        m2.metric("Mevcut Konteyner Brüt Ağırlığı", f"{total_weight_kg:,.0f} kg", f"{total_weight_kg*2.20462:,.0f} lbs")
        
        if total_weight_kg < min_allowed_kg:
            status_text = "🟡 EKSİK YÜKLEME! (Min Limit Altında)"
            delta_msg = f"{min_allowed_kg - total_weight_kg:,.0f} kg daha yüklenmeli"
            st.warning(f"**Liman Kuralı Uyarısı:** Yüklenen ağırlık minimum limitin ({min_allowed_kg:,.0f} kg) altındadır. Konteyner bu şekilde sevk edilemez.")
        elif total_weight_kg > max_allowed_kg:
            status_text = "🔴 AĞIR TONAJ UYARISI! (Max Limit Üstünde)"
            delta_msg = f"{total_weight_kg - max_allowed_kg:,.0f} kg fazla yükleme yapıldı"
            st.error(f"**Aşırı Yükleme Uyarısı:** Yüklenen ağırlık maksimum yasal limiti ({max_allowed_kg:,.0f} kg) aşmaktadır!")
        else:
            status_text = "🟢 UYGUN ✅ (İdeal Tonaj Aralığında)"
            delta_msg = "Liman standartlarına tam uygun"
            st.success("Konteyner ağırlığı seçilen varış limanı için yasal Min - Max aralığındadır.")
            
        m3.metric("İhracat Sevkiyat Onayı", status_text, delta_msg)

        # 3D Visualizer
        st.subheader("📦 3D Konteyner Yükleme Simülasyonu")
        fig = go.Figure()

        fig.add_trace(go.Scatter3d(
            x=[0, c_l, c_l, 0, 0, 0, c_l, c_l, 0, 0, 0, 0, c_l, c_l, c_l, c_l],
            y=[0, 0, c_w, c_w, 0, 0, 0, c_w, c_w, 0, c_w, c_w, c_w, c_w, 0, 0],
            z=[0, 0, 0, 0, 0, c_h, c_h, c_h, c_h, c_h, c_h, 0, 0, c_h, c_h, 0],
            mode='lines', line=dict(color='blue', width=3), name='Konteyner'
        ))

        curr_x, curr_y, curr_z = 0, 0, 0
        max_row_w = 0

        for item in st.session_state.cart:
            cL, cW, cH = item["Kasa L"], item["Kasa W"], item["Kasa H"]
            label_text = f"{item['Müşteri']} - {item['Ürün Adı']}"
            for count in range(item["Kasa Sayısı"]):
                if curr_y + cW > c_w:
                    curr_y = 0
                    curr_x += max_row_w
                    max_row_w = 0
                if curr_x + cL > c_l:
                    curr_x = 0
                    curr_y = 0
                    curr_z += cH

                max_row_w = max(max_row_w, cL)

                fig.add_trace(go.Mesh3d(
                    x=[curr_x, curr_x+cL, curr_x+cL, curr_x, curr_x, curr_x+cL, curr_x+cL, curr_x],
                    y=[curr_y, curr_y, curr_y+cW, curr_y+cW, curr_y, curr_y, curr_y+cW, curr_y+cW],
                    z=[curr_z, curr_z, curr_z, curr_z, curr_z+cH, curr_z+cH, curr_z+cH, curr_z+cH],
                    i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
                    j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
                    k=[0, 7, 5, 3, 6, 7, 1, 1, 5, 5, 7, 6],
                    opacity=0.6, name=label_text
                ))
                curr_y += cW

        fig.update_layout(scene=dict(xaxis=dict(range=[0, c_l]), yaxis=dict(range=[0, c_w]), zaxis=dict(range=[0, c_h]), aspectmode='data'))
        st.plotly_chart(fig, width="stretch")

# ------------------------------------------
# TAB 5: YÖNETİCİ ŞABLON & ONAY YÖNETİMİ
# ------------------------------------------
with tab5:
    st.header("💾 Sunucu Taslak Kayıt & Yükleme Yönetimi")
    
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        st.subheader("📝 Taslağı Doğrudan Sunucuya Kaydet")
        order_no = st.text_input("Konteyner / Proje Dosya Adı", value="KONTEYNER-2026-01")
        approval_status = st.selectbox("Yönetici Onay Durumu", ["Taslak / İncelemede", "Dizim Onayladı", "İhracat Onayladı", "YÖNETİM ONAYLADI (Üretime Verilsin)"])
        exec_notes = st.text_area("Fabrika & Paketleme Özel Talimatları", value="Kasalar fumigasyonlu ve alt kısmı forklift girişine uygun takozlu hazırlanacak. Nem alıcı jel konulacak.")

        if st.session_state.cart:
            if st.button("☁️️ Taslağı Portala / Sunucuya Kaydet", width="stretch"):
                payload = {
                    "proje_kodu": order_no,
                    "onay_durumu": approval_status,
                    "yonetici_notu": exec_notes,
                    "sepet": st.session_state.cart
                }
                save_path = os.path.join(TEMPLATES_DIR, f"{safe_name(order_no)}.json")
                log_history(order_no, st.session_state.cart)
                write_json(save_path, payload)
                notify(f"📝 {st.session_state.user_name} taslağı kaydetti: {order_no}")
                
                st.success(f"✅ '{order_no}' isimli taslak sunucuya başarıyla kaydedildi! Sol yan menüden herkes erişebilir.")
                st.rerun()
                
            st.markdown("---")
            payload_json = json.dumps({"proje_kodu": order_no, "onay_durumu": approval_status, "yonetici_notu": exec_notes, "sepet": st.session_state.cart}, ensure_ascii=False, indent=4)
            st.download_button("💾 Bilgisayara .json Olarak İndir (Yedek)", data=payload_json, file_name=f"{order_no}_recete.json", mime="application/json", width="stretch")

    with col_m2:
        st.subheader("📂 Dışarıdan (.json) Taslak Yükle")
        up_file = st.file_uploader("Bilgisayarınızdaki bir .json dosyasını yükleyin", type=["json"])
        if up_file is not None:
            data = json.load(up_file)
            st.success(f"Yüklenen Proje: **{data.get('proje_kodu')}** | Durum: **{data.get('onay_durumu')}**")
            st.info(f"Yönetici Notu: {data.get('yonetici_notu')}")
            
            if st.button("📥 Yüklenen Dosyayı Ekrana Aktar", width="stretch"):
                st.session_state.cart = data.get("sepet", [])
                save_auto_recovery()
                st.toast("Dış dosya başarıyla aktarıldı!", icon="🚀")
                st.rerun()


# ------------------------------------------
# TAB 6: KASA & KUTU STOKU
# ------------------------------------------
def panel_stok():
    st.header("📦 Kasa, Kutu ve Ambalaj Malzeme Stoku")
    stock = read_json(STOCK_FILE, None)
    if stock is None:
        stock = [
            {"Tür": "Kasa", "Kalem": "Ahşap Kasa 101x101x40", "Adet": 0, "Minimum": 10},
            {"Tür": "Kutu", "Kalem": "Karton Kutu", "Adet": 0, "Minimum": 200},
            {"Tür": "Kutu", "Kalem": "Strafor Kutu", "Adet": 0, "Minimum": 100},
            {"Tür": "Kutu", "Kalem": "5'li Paket", "Adet": 0, "Minimum": 100},
            {"Tür": "Kutu", "Kalem": "10'lu Paket", "Adet": 0, "Minimum": 100},
            {"Tür": "Diğer", "Kalem": "Nem Alıcı Jel", "Adet": 0, "Minimum": 50},
        ]
    edited_stock = st.data_editor(
        pd.DataFrame(stock), num_rows="dynamic", width="stretch", hide_index=True, key="stock_editor",
        column_config={"Tür": st.column_config.SelectboxColumn("Tür", options=["Kasa", "Kutu", "Diğer"], required=True)}
    ).fillna({"Tür": "Diğer", "Kalem": "", "Adet": 0, "Minimum": 0})

    if st.button("💾 Stoğu Kaydet", width="stretch"):
        write_json(STOCK_FILE, edited_stock.to_dict("records"))
        st.toast("Stok kaydedildi!", icon="✅")
        _low = edited_stock[edited_stock["Adet"] < edited_stock["Minimum"]]
        if len(_low):
            notify("⚠️ Stok minimumun altında: " + ", ".join(f"{r.Kalem} ({r.Adet:g}/{r.Minimum:g})" for r in _low.itertuples()))

    low = edited_stock[edited_stock["Adet"] < edited_stock["Minimum"]]
    for _, r in low.iterrows():
        st.warning(f"⚠️ **{r['Kalem']}** minimumun altında: {r['Adet']} / {r['Minimum']}")

    need_crates = sum(int(i.get("Kasa Sayısı", 0)) for i in st.session_state.cart)
    need_by_type = {}
    for i in st.session_state.cart:
        t = i.get("Kutu Tipi") or ""
        need_by_type[t] = need_by_type.get(t, 0) + int(i.get("Kasa Sayısı", 0)) * int(i.get("Kasadaki Kutu", 0))
    kutu_rows = edited_stock[edited_stock["Tür"] == "Kutu"]

    def _match(t):
        m = kutu_rows[kutu_rows["Kalem"] == t]
        if len(m):
            return m.index[0]
        return kutu_rows.index[0] if (not t and len(kutu_rows)) else None

    have_crates = edited_stock[edited_stock["Tür"] == "Kasa"]["Adet"].sum()
    st.subheader("🛒 Sepetteki Siparişin Ambalaj İhtiyacı")
    st.metric("Gereken Kasa", f"{need_crates:,}", f"Stok farkı: {have_crates - need_crates:,.0f}")
    lack = need_crates > have_crates
    if need_by_type:
        need_rows = []
        for t, need in need_by_type.items():
            idx = _match(t)
            have = float(edited_stock.loc[idx, "Adet"]) if idx is not None else None
            need_rows.append({"Kutu / Paket Tipi": t or "(belirtilmemiş)", "Gereken": f"{need:,}",
                              "Stokta": f"{have:,.0f}" if have is not None else "stokta kalem yok",
                              "Fark": f"{have - need:,.0f}" if have is not None else "-"})
            if have is None or have < need:
                lack = True
        st.dataframe(pd.DataFrame(need_rows), width="stretch", hide_index=True)
    if lack and st.session_state.cart:
        st.error("Stok bu sipariş için yetersiz ya da bir kutu tipi stok listesinde yok.")

    if st.session_state.cart and st.button("📉 Sepetteki Siparişi Stoktan Düş"):
        cur = edited_stock.copy()
        kidx = cur.index[cur["Tür"] == "Kasa"]
        if len(kidx):
            cur.loc[kidx[0], "Adet"] -= need_crates
        for t, need in need_by_type.items():
            idx = _match(t)
            if idx is not None:
                cur.loc[idx, "Adet"] -= need
        write_json(STOCK_FILE, cur.to_dict("records"))
        st.rerun(scope="fragment")

# ------------------------------------------
# TAB 7: MÜŞTERİ GEÇMİŞİ
# ------------------------------------------
def panel_gecmis():
    st.header("👥 Müşteri Sipariş Geçmişi")
    st.caption("5. sekmeden kaydedilen her proje buraya otomatik işlenir. Aynı malzeme tekrar gelirse tek tıkla sepete ekleyin.")
    hist = read_json(HISTORY_FILE, [])
    if not hist:
        st.info("Henüz geçmiş yok. Bir taslağı sunucuya kaydedince burada görünür.")
    else:
        pick = st.selectbox("Müşteri", sorted({h.get("Müşteri", "?") for h in hist}))
        cust_items = [h for h in hist if h.get("Müşteri") == pick]
        show_cols = ["Tarih", "Proje", "PO / Sipariş No", "Ürün Adı", "Ebat (cm)", "Kasa Sayısı", "Toplam Kutu", "Toplam Adet", "Toplam m²", "Toplam Ağırlık (kg)"]
        cdf = pd.DataFrame(cust_items)
        st.dataframe(cdf[[c for c in show_cols if c in cdf.columns]], width="stretch", hide_index=True)

        labels = [f"{h.get('Tarih','')} | {h.get('Proje','')} | {h.get('Ürün Adı','')} ({h.get('Ebat (cm)','')})" for h in cust_items]
        sel = st.selectbox("Tekrar sipariş verilecek kalem:", labels)
        r1, r2, r3 = st.columns(3)
        new_po = r1.text_input("Yeni PO / Sipariş No", value="")
        new_crates = r2.number_input("Kasa Sayısı", min_value=1, value=int(cust_items[labels.index(sel)].get("Kasa Sayısı", 1)), step=1)
        r3.write("")
        if r3.button("➕ Sepete Tekrar Ekle", width="stretch"):
            row = {k: v for k, v in cust_items[labels.index(sel)].items() if k not in ("Tarih", "Proje")}
            row["Kasa Sayısı"] = int(new_crates)
            if new_po:
                row["PO / Sipariş No"] = new_po
            st.session_state.cart.append(row)
            save_auto_recovery()
            st.toast("Önceki sipariş sepete eklendi!", icon="✅")
            st.rerun()

# ------------------------------------------
# TAB 8: GÜNLÜK DİZİM DEFTERİ
# ------------------------------------------
def panel_dizim():
    st.header("📒 Günlük Dizim Defteri")
    st.caption("Defterdeki günlük kayıtlar ve fotoğraflar burada tutulur; telefondan da girilebilir.")
    log = read_json(LOG_FILE, [])

    with st.form("log_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        l_date = f1.date_input("Tarih", value=date.today())
        l_place = f2.text_input("Dizim Yeri / Tezgah / Şinik")
        l_cust = f3.text_input("Müşteri")
        f4, f5, f6, f7 = st.columns(4)
        l_prod = f4.text_input("Ürün")
        l_qty = f5.number_input("Dizilen Adet", min_value=0, step=100)
        l_crate = f6.number_input("Biten Kasa", min_value=0.0, step=0.5)
        l_workers = f7.number_input("İşçi Sayısı", min_value=0, step=1)
        l_note = st.text_area("Not")
        l_photo = st.file_uploader("Defter / Dizim Fotoğrafı (isteğe bağlı)", type=["jpg", "jpeg", "png"])
        if st.form_submit_button("➕ Kaydı Ekle", width="stretch"):
            photo_name = ""
            if l_photo is not None:
                photo_name = f"{l_date}_{uuid.uuid4().hex[:8]}.jpg"
                save_photo(photo_name, l_photo.getvalue())
            log.append({"id": uuid.uuid4().hex[:8], "Tarih": str(l_date), "Yer": l_place, "Müşteri": l_cust, "Ürün": l_prod,
                        "Adet": int(l_qty), "Kasa": float(l_crate), "İşçi": int(l_workers), "Not": l_note,
                        "Foto": photo_name, "Kaydeden": st.session_state.user_name})
            write_json(LOG_FILE, log)
            notify(f"📒 Dizim: {l_place} | {l_cust} {l_prod} | {int(l_qty)} adet, {l_crate:g} kasa ({st.session_state.user_name})")
            st.rerun(scope="fragment")

    if log:
        days = sorted({e["Tarih"] for e in log}, reverse=True)
        day = st.selectbox("Gün", days)
        day_items = [e for e in log if e["Tarih"] == day]
        d1, d2 = st.columns(2)
        d1.metric("Günlük Toplam Adet", f"{sum(e['Adet'] for e in day_items):,}")
        d2.metric("Günlük Biten Kasa", f"{sum(e['Kasa'] for e in day_items):.1f}")
        st.dataframe(pd.DataFrame(day_items).drop(columns=["id", "Foto"]), width="stretch", hide_index=True)
        for e in day_items:
            img_bytes = load_photo(e["Foto"]) if e.get("Foto") else None
            if img_bytes:
                with st.expander(f"📷 {e['Yer']} - {e['Ürün']}"):
                    st.image(img_bytes)
        del_sel = st.selectbox("Silinecek kayıt:", [f"{e['id']} | {e['Yer']} - {e['Ürün']} ({e['Adet']})" for e in day_items])
        if st.button("🗑️ Seçili Kaydı Sil"):
            did = del_sel.split(" | ")[0]
            write_json(LOG_FILE, [e for e in log if e["id"] != did])
            st.rerun(scope="fragment")


# ------------------------------------------
# BAŞLANGIÇ REÇETELERİ (Excel tablolarından hazırlandı, hepsi 1 kasa)
# ------------------------------------------
# (müşteri, model, taş cinsi, ebat etiketi, boy, en, kalınlık, tip F/M/E, kasadaki kutu, kutu içi adet, not)
FD = "Floor & Decor (FD)"
SEED_ROWS = [
    (FD, "MAR VAN ICE THIN FLUT", "BEIGE MINI BULLNOSE FLUT", "15x61 cm", 61, 15, 1.0, "F", 60, 5, ""),
    (FD, "MAR CALA VERDE BAMBOO", "CALACATA ERMER BAMBOO FLUT", "15x61 cm", 61, 15, 1.0, "F", 60, 5, ""),
    (FD, "MAR CREMA ROYAL PETRA", "DIANA ROYAL KIRMA FLUT", "15x61 cm", 61, 15, 1.0, "F", 52, 5, ""),
    (FD, "MAR CAR CHATEAU PETRA", "MUGLA KIRMA", "15x61 cm", 61, 15, 1.0, "F", 52, 5, ""),
    (FD, "MAR FELIX DOLOMITE GREEN HON", "YILDIZLI MODEL DOLOMITE + YESIL", "30.5x30.5 cm", 30.5, 30.5, 1.0, "M", 72, 5, "ebat?"),
    (FD, "LIM LINEN IVY HON MOS", "LEAF LIMRA", "30.5x30.5 cm", 30.5, 30.5, 1.0, "M", 72, 5, "ebat?"),
    (FD, "MAR BLACK THIN FLUT", "SIYAH MINI BULLNOSE FLUT", "15x61 cm", 61, 15, 1.0, "F", 68, 4, ""),
    (FD, "MAR LUNA CREMA THIN FLUTE", "BOTTOCINO MINI BULLNOSE FLUT", "15x61 cm", 61, 15, 1.0, "F", 68, 4, ""),
    (FD, "MAR BOTTOCINO PENCIL", "HONLU PENCIL", "30.5x1.9x1.2 cm", 30.5, 1.9, 1.2, "F", 100, 20, ""),
    (FD, "MAR CREMA ROYAL PENCIL", "POLISHED PENCIL", "30.5x1.9x1.2 cm", 30.5, 1.9, 1.2, "F", 100, 20, ""),
    (FD, "MAR VAN ICE PENCIL", "HONLU PENCIL", "30.5x1.9x1.2 cm", 30.5, 1.9, 1.2, "F", 100, 20, ""),
    (FD, "MAR FLUTED BLACK", "6X24 FLUTED", "15x61 cm", 61, 15, 1.0, "F", 52, 4, ""),
    (FD, "LIM LINEN LIMESTONE", "6X24 DIM", "15x61 cm", 61, 15, 1.0, "E", 60, 5, ""),
    ("Mozaikçi", "COASTAL LIMESTONE", "HONLU FAYANS", "30.5x61x1.2 cm", 61, 30.5, 1.2, "E", 40, 4, ""),
    ("Mozaikçi", "COASTAL LIMESTONE", "HONLU FAYANS", "15.2x30.5x1 cm", 30.5, 15.2, 1.0, "E", 36, 20, ""),
    ("Mozaikçi", "COASTAL LIMESTONE", "HONLU FAYANS", "7.5x22.5x1 cm", 22.5, 7.5, 1.0, "E", 42, 60, ""),
    ("Mozaikçi", "MONTAUK MRB.", "HONLU FAYANS", "7.5x22.5x1 cm", 22.5, 7.5, 1.0, "E", 42, 60, ""),
    ("Mozaikçi", "KOMBASAN WHITE", "HONLU FAYANS", "7.5x15x1 cm", 15, 7.5, 1.0, "E", 42, 88, ""),
    ("Mozaikçi", "KEMALPAŞA WHITE", "FAYANS HONLU", "30.5x61x1.2 cm", 61, 30.5, 1.2, "E", 40, 4, ""),
    ("Mozaikçi", "KEMALPAŞA WHITE", "HEXAGON HONLU", "5.5 cm hexagon", 30.5, 30.5, 1.0, "M", 45, 10, ""),
    ("Mozaikçi", "KOMBASAN WHITE", "HEXAGON HONED", "5.5 cm hexagon", 30.5, 30.5, 1.0, "M", 45, 10, ""),
    ("Mozaikçi", "KOMBASAN WHITE + DOT AFYON GRI", "SMALL IDA HONLU", "2.3x4.8x1 cm", 30.5, 30.5, 1.0, "M", 45, 10, ""),
    ("Mozaikçi", "KEMALPAŞA + DOT KUTAHYA SIYAH (KINGBLUE)", "BIG IDA CILALI", "8.6x6.2x1 cm", 30.5, 30.5, 1.0, "M", 45, 10, ""),
    ("İonic", "CARRARA + ASH BLUE MRB", "HONLU SCALLOP SHELL", "balik pulu", 30.5, 30.5, 1.0, "M", 36, 10, ""),
    ("İonic", "CARRARA WHITE MRB.", "HONLU SCALLOP SHELL", "balik pulu", 30.5, 30.5, 1.0, "M", 36, 10, ""),
    ("İonic", "CARRARA MRB.", "HONLU PAHLI", "metro 4.8x10x1 cm", 30.5, 30.5, 1.0, "M", 36, 10, ""),
    ("İonic", "CARRARA MRB.", "HONLU", "tear drop (lemon)", 30.5, 30.5, 1.0, "M", 36, 10, ""),
    ("İonic", "CARRARA WHITE MRB", "HONLU SKIRTING BASEBOARD", "12.5x61x2 cm", 61, 12.5, 2.0, "E", 50, 5, "kutu?"),
    ("İonic", "CARRARA MRB.", "HONLU", "arabesque", 30.5, 30.5, 1.0, "M", 36, 10, ""),
    ("İonic", "CARRARA MRB", "HONED BRICK", "2.3x7.5x1 cm", 30.5, 30.5, 1.0, "M", 36, 10, ""),
    ("İonic", "CARRARA WHITE MRB.", "HONLU HEXAGON", "2 inch hexagon", 30.5, 30.5, 1.0, "M", 36, 10, ""),
    ("İonic", "CARRARA MRB", "CILALI FAYANS", "10x30.5x1 cm", 30.5, 10, 1.0, "E", 36, 30, ""),
    ("İonic", "TEOS GREEN MRB.", "HONLU FAYANS", "30.5x30.5x1 cm", 30.5, 30.5, 1.0, "E", 36, 10, ""),
    ("İonic", "ROSSO LEVANTO", "HONLU FAYANS", "30.5x30.5x1 cm", 30.5, 30.5, 1.0, "E", 36, 10, ""),
    ("İonic", "TAURUS NERO (TOROS SIYAH) MRB.", "ESKITME", "2.3x2.3x1 cm", 30.5, 30.5, 1.0, "M", 36, 10, ""),
    ("İonic", "CREMA MARFIL MARBLE", "SPLIT FACE PATLATMA", "4.8x10 cm", 30.5, 30.5, 1.0, "M", 45, 5, ""),
]

# İVA: tabloda sadece kasa başına toplam adet var (kutu dağılımı yok, kutu içi 5 varsayıldı)
# (model, taş cinsi, ebat etiketi, boy, en, kalınlık, kasa başına toplam adet)
SEED_IVA = [
    ("BOTTOCINO MRB.", "HONLU CHAIRRAIL F5", "5x15x2.8 cm", 15, 5, 2.8, 300),
    ("BOTTOCINO MRB.", "CILALI CHAIRRAIL F5", "5x15x2.8 cm", 15, 5, 2.8, 300),
    ("BOTTOCINO MRB.", "HONLU BULLNOSE", "1.9x15x1.9 cm", 15, 1.9, 1.9, 300),
    ("BOTTOCINO MRB.", "CILALI BULLNOSE", "1.9x15x1.9 cm", 15, 1.9, 1.9, 300),
    ("SILVER TRAVERTINE", "OGEE1 HONED", "4.8x15x2.5 cm", 15, 4.8, 2.5, 200),
    ("SILVER TRAVERTINE", "HONED BULLNOSE", "1.9x15x1.9 cm", 15, 1.9, 1.9, 200),
    ("SILVER TRAVERTINE", "HONLU PENCIL", "1.2x15x1.5 cm", 15, 1.2, 1.5, 300),
    ("LIGHT TRAVERTINE", "HONLU OGEE1 F1", "4.8x15x2.5 cm", 15, 4.8, 2.5, 200),
    ("LIGHT TRAVERTINE", "BULLNOSE HONLU", "1.9x15x1.9 cm", 15, 1.9, 1.9, 200),
    ("IVORY TRAVERTINE", "HONED PENCIL", "1.2x15x1.5 cm", 15, 1.2, 1.5, 300),
    ("NOCE TRAVERTINE", "HONLU OGEE1", "4.8x15x2.5 cm", 15, 4.8, 2.5, 200),
    ("NOCE TRAVERTINE", "BULLNOSE HONED", "1.9x15x1.9 cm", 15, 1.9, 1.9, 200),
    ("NOCE TRAVERTINE", "HONLU PENCIL", "1.2x15x1.5 cm", 15, 1.2, 1.5, 300),
    ("WALLNUT TRV", "HONED OGEE1 F1", "4.8x15x2.5 cm", 15, 4.8, 2.5, 200),
    ("WALLNUT TRV", "HONLU BULLNOSE", "1.9x15x1.9 cm", 15, 1.9, 1.9, 200),
    ("WALLNUT TRV", "HONED PENCIL", "1.2x15x1.5 cm", 15, 1.2, 1.5, 300),
    ("LYMRA LIMESTONE", "HONLU MINIMAL MODERN CHAIRRAIL", "5x15x2 cm", 15, 5, 2.0, 300),
]
for _m, _t, _lab, _l, _w, _th, _tot in SEED_IVA:
    SEED_ROWS.append(("İVA", _m, _t, _lab, _l, _w, _th, "F", _tot // 5, 5, "kutu?"))

# Gerçek tartılar (iso.xlsx): (1 kasa NET kg, 1 kasa BRÜT kg), anahtar (model, taş cinsi) ya da (model, taş cinsi, ebat)
SEED_WEIGHTS = {
    ("MAR VAN ICE THIN FLUT", "BEIGE MINI BULLNOSE FLUT"): (702.4, 741.0),
    ("MAR CALA VERDE BAMBOO", "CALACATA ERMER BAMBOO FLUT"): (718.6, 758.6),
    ("MAR CREMA ROYAL PETRA", "DIANA ROYAL KIRMA FLUT"): (750.8, 789.2),
    ("MAR CAR CHATEAU PETRA", "MUGLA KIRMA"): (743.8, 782.4),
    ("MAR FELIX DOLOMITE GREEN HON", "YILDIZLI MODEL DOLOMITE + YESIL"): (890, 930),
    ("LIM LINEN IVY HON MOS", "LEAF LIMRA"): (640, 680),
    ("MAR BLACK THIN FLUT", "SIYAH MINI BULLNOSE FLUT"): (715, 750),
    ("MAR LUNA CREMA THIN FLUTE", "BOTTOCINO MINI BULLNOSE FLUT"): (720.5, 755.5),
    ("MAR BOTTOCINO PENCIL", "HONLU PENCIL"): (370, 400),
    ("MAR CREMA ROYAL PENCIL", "POLISHED PENCIL"): (370, 400),
    ("MAR VAN ICE PENCIL", "HONLU PENCIL"): (370, 400),
    ("MAR FLUTED BLACK", "6X24 FLUTED"): (810, 850),
    ("LIM LINEN LIMESTONE", "6X24 DIM"): (790, 830),
    ("TEOS GREEN MRB.", "HONLU FAYANS"): (880, 920),
    ("ROSSO LEVANTO", "HONLU FAYANS"): (880, 920),
    ("CARRARA MRB", "CILALI FAYANS"): (880, 920),
    ("TAURUS NERO (TOROS SIYAH) MRB.", "ESKITME"): (740, 770),
    ("CARRARA + ASH BLUE MRB", "HONLU SCALLOP SHELL"): (710, 750),
    ("CARRARA WHITE MRB.", "HONLU SCALLOP SHELL"): (710, 750),
    ("CARRARA WHITE MRB.", "HONLU HEXAGON"): (690, 730),
    ("CARRARA MRB.", "HONLU PAHLI"): (790, 830),
    ("CARRARA MRB.", "HONLU", "tear drop (lemon)"): (690, 730),
    ("CARRARA MRB", "HONED BRICK"): (840, 880),
}


# F&D "New Products" listesi: (VSN, açıklama, taş, tür, boy cm, en cm, kalınlık cm, parça ağırlığı lb, kutu içi adet, palet/kasa adedi)
SEED_FD_CATALOG = [
    ('M0519', 'Vanilla Marble with white dolomite', 'Marble', 'Mosaic', 28.1, 27.2, 0.95, 3.8755854701123207, 5, 360),
    ('M0519', 'Dolomite with Teos Green', 'Dolomite', 'Mosaic', 28.1, 27.2, 0.95, 3.8755854701123207, 5, 360),
    ('M0515', 'Dolomite with Teos Green', 'Dolomite', 'Mosaic', 30.0, 25.8, 0.95, 3.9246691881239997, 5, 360),
    ('M0515', 'Calacatta Verde with Dolomite', 'Marble', 'Mosaic', 30.0, 25.8, 0.95, 3.9246691881239997, 5, 360),
    ('M0512', 'Dolomit with Iceber + Kombassan M (Grey) + Vanilla', 'Dolomite', 'Mosaic', 30.5, 30.5, 0.95, 4.716955442186499, 5, 360),
    ('M0513', 'Dolomit with Diana Royal', 'Dolomite', 'Mosaic', 29.0, 29.0, 0.95, 4.264401533866, 5, 360),
    ('M0513', 'Dolomit with Teos Green', 'Dolomite', 'Mosaic', 29.0, 29.0, 0.95, 4.264401533866, 5, 360),
    ('M0513', 'Dolomit with Kombassan M (Grey)', 'Dolomite', 'Mosaic', 29.0, 29.0, 0.95, 4.264401533866, 5, 360),
    ('M0525', 'Dolomit with Kombassan M (Grey)', 'Dolomite', 'Mosaic', 26.7, 23.1, 0.95, 3.1274137146760204, 5, 360),
    ('M0526', 'Dolomit with Vanilla', 'Dolomite', 'Mosaic', 30.5, 30.5, 0.95, 4.716955442186499, 5, 360),
    ('M0526', 'Dolomit with Teos Green', 'Dolomite', 'Mosaic', 30.5, 30.5, 0.95, 4.716955442186499, 5, 360),
    ('M0502', 'Dolomit with Vanilla Dark', 'Dolomite', 'Mosaic', 30.5, 30.5, 0.95, 4.716955442186499, 5, 360),
    ('M0509', 'Dolomit with Equator', 'Dolomite', 'Mosaic', 31.5, 30.0, 0.95, 4.7917472645700006, 5, 360),
    ('M0507', 'DN Limra Vein Cut', 'Limestone', 'Mosaic', 31.5, 26.5, 0.95, 4.2327100837035, 5, 360),
    ('M0504', 'Dolomit with Vanilla Dark', 'Dolomite', 'Mosaic', 30.5, 30.5, 0.95, 4.716955442186499, 5, 360),
    ('M0527', 'DN Limra Vein Cut', 'Limestone', 'Mosaic', 40.6, 40.6, 0.95, 7.4975, 4, 288),
    ('EMR 10', 'DN Limra Vein Cut', 'Limestone', 'Tile', 61.0, 15.2, 1.91, 7.6654728497399995, 4, 208),
    ('G0409', 'Calacatta Verde', 'Marble', 'Tile', 30.5, 10.0, 3.0, 3.3620494954999995, 6, 384),
    ('G0407', 'Kombassan', 'Marble', 'Tile', 20.0, 20.0, 3.0, 3.9683207160000005, 6, 384),
    ('-', 'DN Limra Vein Cut', 'Limestone', 'Tile', 40.6, 10.0, 0.95, 1.9993333333333332, 15, 630),
    ('G0408', 'Calacatta Verde', 'Marble', 'Tile', 30.5, 20.0, 3.0, 3.7037660015999996, 4, 160),
]

def _catalog_presets():
    out = {}
    for vsn, desc, body, kind, L, W, T, lb, bq, pal in SEED_FD_CATALOG:
        lab = f"{L:g}x{W:g} cm"
        name = f"[{FD}] {vsn} {desc} ({lab}) [katalog]"
        fn = "".join(ch for ch in name if ch.isalnum() or ch in (" ", "_", "-")).rstrip() + ".json"
        out[fn] = {
            "preset_name": name, "file_name": fn, "customer_name": FD, "po_number": "",
            "product_name": f"{vsn} {desc}", "product_type": "Mozaik" if kind == "Mosaic" else "Ebatlı Mermer / Plaka",
            "sales_unit": "Adet (Pcs)", "p_length": L, "p_width": W, "p_thickness": T,
            "density": 2.6 if body == "Limestone" else 2.7,
            "pcs_per_box": bq, "boxes_in_crate": pal // bq, "thin_sinik_per_box": 0, "thick_sinik_per_box": 0,
            "crate_length": 101.0, "crate_width": 101.0, "crate_height": 40.0, "crate_tare_kg": 40.0,
            "target_pcs": pal, "net_kg_per_pc": round(lb * 0.45359237, 4), "weight_src": "katalog", "box_type": "Karton Kutu",
        }
    return out

def build_seed_presets():
    types = {"F": "Flute / Moulding", "M": "Mozaik", "E": "Ebatlı Mermer / Plaka"}
    out = {}
    for c, m, t, lab, L, W, T, ty, nb, pp, note in SEED_ROWS:
        name = f"[{c}] {m} - {t} ({lab})" + (f" [{note}]" if note else "")
        fn = "".join(ch for ch in name if ch.isalnum() or ch in (" ", "_", "-")).rstrip() + ".json"
        up = m.upper()
        dens = 2.5 if ("TRAV" in up or "TRV" in up) else 2.6 if "LIMESTONE" in up else 2.7
        out[fn] = {
            "preset_name": name, "file_name": fn, "customer_name": c, "po_number": "",
            "product_name": f"{m} {t}", "product_type": types[ty], "sales_unit": "Adet (Pcs)",
            "p_length": L, "p_width": W, "p_thickness": T, "density": dens,
            "pcs_per_box": pp, "boxes_in_crate": nb,
            "thin_sinik_per_box": 1 if ty == "F" else 0, "thick_sinik_per_box": 0,
            "crate_length": 101.0, "crate_width": 101.0, "crate_height": 40.0, "crate_tare_kg": 35.0,
            "target_pcs": nb * pp,
        }
        out[fn].update({"net_kg_per_pc": 0.0, "weight_src": "tahmini", "box_type": "Karton Kutu"})
        w = SEED_WEIGHTS.get((m, t, lab)) or SEED_WEIGHTS.get((m, t))
        if w:
            out[fn]["net_kg_per_pc"] = round(w[0] / (nb * pp), 4)
            out[fn]["crate_tare_kg"] = float(round(w[1] - w[0], 1))
            out[fn]["weight_src"] = "ölçülmüş"
    out.update(_catalog_presets())
    return out

def write_many(items):
    """Birden fazla kaydı tek seferde yazar."""
    if USE_DB:
        rows = [{"key": k, "value": json.loads(json.dumps(v, ensure_ascii=False, default=str))} for k, v in items.items()]
        _sb_call("POST", {"on_conflict": "key"}, rows, {"Prefer": "resolution=merge-duplicates,return=minimal"})
        st.cache_data.clear()
    else:
        for k, v in items.items():
            write_json(k, v)

with st.sidebar.expander("📥 Başlangıç Reçeteleri"):
    st.caption("Floor & Decor, İVA, Mozaikçi ve İonic siparişlerinden hazırlanan 1 kasalık reçeteler. Kayıtlı reçetelerin sadece ağırlık bilgisi gerçek tartılarla güncellenir, diğer ayarların korunur.")
    if st.session_state.get("seed_msg"):
        st.success(st.session_state.pop("seed_msg"))
    if st.button("Hazır reçeteleri yükle", key="seed_btn"):
        have = read_dir(PRESETS_DIR)
        seeds = build_seed_presets()
        new_items, upd = {}, 0
        for fn, d in seeds.items():
            if fn not in have:
                new_items[os.path.join(PRESETS_DIR, fn)] = d
            elif d["weight_src"] == "ölçülmüş" and have[fn].get("weight_src") != "ölçülmüş":
                merged = dict(have[fn])
                merged.update({k: d[k] for k in ("net_kg_per_pc", "crate_tare_kg", "weight_src")})
                new_items[os.path.join(PRESETS_DIR, fn)] = merged
                upd += 1
        if new_items:
            write_many(new_items)
        st.session_state["seed_msg"] = f"{len(new_items) - upd} yeni reçete eklendi, {upd} reçetenin ağırlığı gerçek tartıya göre güncellendi."
        st.rerun()


# ------------------------------------------
# KESİM DEFTERİ
# ------------------------------------------
def panel_kesim():
    st.caption("Nerede, ne kadar mal kesildi, kaç parça kırıldı/fire verdi buradan girilir.")
    cuts = read_json(KESIM_FILE, [])

    with st.form("kesim_form", clear_on_submit=True):
        k1, k2, k3 = st.columns(3)
        k_date = k1.date_input("Tarih", value=date.today())
        k_place = k2.text_input("Kesim Yeri / Makine / Tezgah")
        k_worker = k3.text_input("Kesen Usta")
        k4, k5, k6 = st.columns(3)
        k_cust = k4.text_input("Müşteri")
        k_mat = k5.text_input("Malzeme (Taş Cinsi)")
        k_prod = k6.text_input("Kesilen Ürün / Ebat")
        k7, k8, k9, k10 = st.columns(4)
        k_qty = k7.number_input("Kesilen Adet", min_value=0, step=10)
        k_m2 = k8.number_input("Kesilen m²", min_value=0.0, step=1.0)
        k_fire = k9.number_input("Kırık / Fire Adet", min_value=0, step=1)
        k_plate = k10.number_input("Plaka / Blok Sayısı", min_value=0, step=1)
        k_note = st.text_area("Not")
        k_photo = st.file_uploader("Fotoğraf (isteğe bağlı)", type=["jpg", "jpeg", "png"], key="kesim_photo")
        if st.form_submit_button("➕ Kesim Kaydı Ekle", width="stretch"):
            photo_name = ""
            if k_photo is not None:
                photo_name = f"kesim_{k_date}_{uuid.uuid4().hex[:8]}.jpg"
                save_photo(photo_name, k_photo.getvalue())
            cuts.append({"id": uuid.uuid4().hex[:8], "Tarih": str(k_date), "Yer": k_place, "Usta": k_worker,
                         "Müşteri": k_cust, "Malzeme": k_mat, "Ürün": k_prod, "Adet": int(k_qty), "m²": float(k_m2),
                         "Fire": int(k_fire), "Plaka": int(k_plate), "Not": k_note, "Foto": photo_name,
                         "Kaydeden": st.session_state.user_name})
            write_json(KESIM_FILE, cuts)
            notify(f"✂️ Kesim: {k_place} | {k_mat} {k_prod} | {int(k_qty)} adet, fire {int(k_fire)} ({st.session_state.user_name})")
            st.rerun(scope="fragment")

    if cuts:
        days = sorted({e["Tarih"] for e in cuts}, reverse=True)
        day = st.selectbox("Gün", days, key="kesim_day")
        items = [e for e in cuts if e["Tarih"] == day]
        m1, m2, m3 = st.columns(3)
        m1.metric("Kesilen Adet", f"{sum(e['Adet'] for e in items):,}")
        m2.metric("Kesilen m²", f"{sum(e['m²'] for e in items):,.1f}")
        m3.metric("Fire / Kırık", f"{sum(e['Fire'] for e in items):,}")
        df = pd.DataFrame(items)
        st.markdown("**Yere göre toplam**")
        by_place = df.assign(Yer=df["Yer"].replace("", "—")).groupby("Yer")[["Adet", "m²", "Fire"]].sum().reset_index()
        st.dataframe(by_place, width="stretch", hide_index=True)
        st.markdown("**Günün kayıtları**")
        st.dataframe(df.drop(columns=["id", "Foto"]), width="stretch", hide_index=True)
        for e in items:
            img_bytes = load_photo(e["Foto"]) if e.get("Foto") else None
            if img_bytes:
                with st.expander(f"📷 {e['Yer']} - {e['Ürün']}"):
                    st.image(img_bytes)
        del_sel = st.selectbox("Silinecek kayıt:", [f"{e['id']} | {e['Yer']} - {e['Ürün']} ({e['Adet']})" for e in items], key="kesim_del")
        if st.button("🗑️ Seçili Kaydı Sil", key="kesim_del_btn"):
            did = del_sel.split(" | ")[0]
            write_json(KESIM_FILE, [e for e in cuts if e["id"] != did])
            st.rerun(scope="fragment")

# ------------------------------------------
# SAĞ ÜST KÖŞE: DEFTERLER & STOK EKLENTİSİ
# ------------------------------------------
@st.dialog("📒 Günlük Dizim Defteri", width="large")
def dlg_dizim():
    panel_dizim()

@st.dialog("✂️ Kesim Defteri", width="large")
def dlg_kesim():
    panel_kesim()

@st.dialog("📦 Kasa, Kutu ve Ambalaj Stoku", width="large")
def dlg_stok():
    panel_stok()

@st.dialog("👥 Müşteri Sipariş Geçmişi", width="large")
def dlg_gecmis():
    panel_gecmis()

@st.dialog("📣 Duyuru Gönder", width="large")
def dlg_duyuru():
    if not tg_on():
        st.info("Telegram bağlı değil. Streamlit Secrets'a TELEGRAM_TOKEN ve TELEGRAM_CHAT_ID eklenince çalışır.")
    msg = st.text_area("Mesaj", key="duyuru_msg")
    if st.button("Gönder", key="duyuru_send") and msg.strip():
        if notify(f"📣 {st.session_state.user_name}: {msg.strip()}"):
            st.success("Gönderildi.")
        else:
            st.error("Gönderilemedi. Ayarları kontrol edin.")

with top_bar:
    st.markdown("<style>div[data-testid='stPopover']{display:flex;justify-content:flex-end;}</style>", unsafe_allow_html=True)
    _sp, _pp = st.columns([2, 1])
    with _pp:
        with st.popover("📒 Defterler & Stok"):
            if st.button("📒 Dizim Defteri", key="open_dizim", width="stretch"):
                dlg_dizim()
            if st.button("✂️ Kesim Defteri", key="open_kesim", width="stretch"):
                dlg_kesim()
            if st.button("📦 Kasa & Kutu Stoku", key="open_stok", width="stretch"):
                dlg_stok()
            if st.button("👥 Müşteri Geçmişi", key="open_gecmis", width="stretch"):
                dlg_gecmis()
            if tg_on() and st.button("📣 Duyuru Gönder", key="open_duyuru", width="stretch"):
                dlg_duyuru()
