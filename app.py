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

for directory in [TEMPLATES_DIR, PRESETS_DIR, DATA_DIR, LOG_PHOTOS_DIR]:
    os.makedirs(directory, exist_ok=True)

# ------------------------------------------
# GÜVENLİK & YARDIMCI FONKSİYONLAR
# ------------------------------------------
def safe_name(text, default="adsiz"):
    """Dosya adından klasör atlatma (../) ve özel karakterleri temizler."""
    s_ = "".join(c for c in str(text) if c.isalnum() or c in (" ", "_", "-")).strip()
    return s_[:80] or default

def read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

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

st.title("🗿 Emre Doğaltaş Üretim, Dizim, İhracat & Konteyner Portalı")
st.caption("Fabrika Müdürü, Dizim Şefi, İhracat Sorumlusu ve Yönetim İçin Ortak Operasyon Paneli")
st.markdown("---")

# ------------------------------------------
# REÇETE (PRESET) YÖNETİM FONKSİYONLARI
# ------------------------------------------
def load_all_presets():
    """Sunucudaki tüm kayıtlı ürün reçetelerini yükler."""
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

if "cart" not in st.session_state:
    st.session_state.cart = []

if "draft_data" not in st.session_state:
    st.session_state.draft_data = {}

# Otomatik Kurtarma
if os.path.exists(RECOVERY_FILE) and not st.session_state.cart:
    try:
        with open(RECOVERY_FILE, "r", encoding="utf-8") as rf:
            rec_data = json.load(rf)
            if rec_data.get("cart"):
                st.warning("⚠️ **Son Oturum Kurtarıldı:** Son çalışmanız arka plandan getirildi.")
                if st.button("🔄 Son Kurtarılan Verileri Sepete Yükle"):
                    st.session_state.cart = rec_data.get("cart", [])
                    st.rerun()
    except Exception:
        pass

def save_auto_recovery():
    payload = {
        "cart": st.session_state.cart,
        "draft_data": st.session_state.draft_data
    }
    with open(RECOVERY_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)

# ------------------------------------------
# YAN MENÜ (SIDEBAR): HIZLI TASLAK YÜKLEME & SİLME
# ------------------------------------------
st.sidebar.header("📁 Sunucudaki Kayıtlı Taslaklar")

saved_files = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".json") and not f.startswith("_")]

if saved_files:
    selected_template = st.sidebar.selectbox("Hızlı Taslak Seçin:", ["Seçiniz..."] + saved_files)
    
    if selected_template != "Seçiniz...":
        template_path = os.path.join(TEMPLATES_DIR, selected_template)
        with open(template_path, "r", encoding="utf-8") as f:
            t_data = json.load(f)
            
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
                os.remove(template_path)
                st.toast(f"{selected_template} silindi!", icon="🗑️")
                st.rerun()
else:
    st.sidebar.info("Henüz sunucuda kayıtlı taslak bulunmuyor.")

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Tüm Sepeti Temizle", width="stretch"):
    st.session_state.cart = []
    if os.path.exists(RECOVERY_FILE):
        os.remove(RECOVERY_FILE)
    st.rerun()

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📐 1. Ürün, Reçete & Stok Parametreleri", 
    "🧩 2. Dizim, Şinik & Kutu Planı",
    "🛒 3. Sipariş Havuzu & Packing List", 
    "🚢 4. İhracat & Konteyner Doluluk",
    "💾 5. Yönetici Şablon & Onay Yönetimi",
    "📦 6. Kasa & Kutu Stoku",
    "👥 7. Müşteri Geçmişi",
    "📒 8. Günlük Dizim Defteri"
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
                    if os.path.exists(file_to_del):
                        os.remove(file_to_del)
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
        crate_tare_kg = st.number_input("Boş Kasa Ağırlığı (kg)", value=float(def_ctare), step=5.0)
        is_stackable = st.checkbox("Üst Üste İstiflenebilir (Stackable)", value=True)

    # REÇETE KAYIT BÖLÜMÜ
    st.markdown("---")
    st.subheader("💾 Ekrandaki Parametreleri Yeni Reçete Olarak Kaydet")
    col_pr1, col_pr2 = st.columns([3, 1])
    with col_pr1:
        new_preset_title = st.text_input("Reçete Adı (Örn: [F&D] Marble Thin Black Flute)", value=f"[{customer_name}] {product_name} ({p_length}x{p_width} cm)")
    with col_pr2:
        st.write("")
        if st.button("💾 Reçeteyi Kütüphaneye Ekle", width="stretch"):
            clean_filename = "".join([c for c in new_preset_title if c.isalnum() or c in (' ', '_', '-')]).rstrip() + ".json"
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
                "pcs_per_box": preset_data.get("pcs_per_box", 24) if preset_data else 24,
                "boxes_in_crate": preset_data.get("boxes_in_crate", 36) if preset_data else 36,
                "thin_sinik_per_box": preset_data.get("thin_sinik_per_box", 1) if preset_data else 1,
                "thick_sinik_per_box": preset_data.get("thick_sinik_per_box", 0) if preset_data else 0,
                "crate_length": crate_length,
                "crate_width": crate_width,
                "crate_height": crate_height,
                "crate_tare_kg": crate_tare_kg,
                "target_pcs": target_pcs
            }
            with open(os.path.join(PRESETS_DIR, clean_filename), "w", encoding="utf-8") as pf:
                json.dump(save_preset_payload, pf, ensure_ascii=False, indent=4)
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

        pcs_per_box = st.number_input("1 Kutu İçi Taş / Parça Adedi", value=int(def_pcs_box), step=1)
        boxes_in_crate = st.number_input("1 Kasadaki Kutu Sayısı", value=int(def_boxes_crate), step=1)
        
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

        stone_weight = (crate_pcs_capacity * piece_m2) * (p_thickness / 100) * (density * 1000)
        crate_gross_weight = stone_weight + crate_tare_kg
        
        if sales_unit == "Adet (Pcs)":
            st.info(f"**1 Kasa Kapasitesi:** {crate_pcs_capacity} Adet ({crate_m2_capacity:.2f} m²)")
        else:
            st.info(f"**1 Kasa Kapasitesi:** {crate_m2_capacity:.2f} m²")
            
        st.success(f"**1 Kasa Brüt Ağırlık:** {crate_gross_weight:.1f} kg")

    with col_d2:
        st.subheader("📐 Kutu İçi Kalıp & Şinik/Şilte")
        def_thick_s = preset_data["thick_sinik_per_box"] if preset_data else 0
        def_thin_s = preset_data["thin_sinik_per_box"] if preset_data else 1

        thick_sinik_per_box = st.number_input("1 Kutu İçi Kalın Şinik Adedi", value=int(def_thick_s), step=1)
        thin_sinik_per_box = st.number_input("1 Kutu İçi İnce Şinik Adedi", value=int(def_thin_s), step=1)
        
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

            row_copy = dict(row)
            row_copy["Toplam Adet"] = tot_pcs
            row_copy["Toplam m²"] = round(tot_m2, 2)
            row_copy["Toplam Kutu"] = tot_boxes
            row_copy["Toplam Ağırlık (kg)"] = round(tot_wt, 1)
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
        c_p3.metric("TOPLAM BRÜT AĞIRLIK", f"{tot_kg:,.0f} kg", f"{tot_kg * 2.20462:,.0f} lbs")
        c_p4.metric("TOPLAM KUTU", f"{tot_boxes:,.0f} Kutu")

        st.markdown("---")
        st.subheader("🏢 Müşteri / Firma Bazlı Ayrıştırılmış Packing List")
        
        unique_customers = df_updated["Müşteri"].unique()
        
        for cust in unique_customers:
            cust_df = df_updated[df_updated["Müşteri"] == cust]
            
            with st.expander(f"📌 Müşteri: **{cust}** (Sipariş Detayı İçin Tıklayın)", expanded=True):
                st.dataframe(
                    cust_df[["PO / Sipariş No", "Ürün Adı", "Ebat (cm)", "Stok Durumu", "İmalat Süresi", "Kasa Sayısı", "Toplam Kutu", "Sipariş Miktarı", "Toplam m²", "Toplam Ağırlık (kg)"]],
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
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=4)
                
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
with tab6:
    st.header("📦 Kasa, Kutu ve Ambalaj Malzeme Stoku")
    stock = read_json(STOCK_FILE, None)
    if stock is None:
        stock = [
            {"Tür": "Kasa", "Kalem": "Ahşap Kasa 101x101x40", "Adet": 0, "Minimum": 10},
            {"Tür": "Kutu", "Kalem": "Karton Kutu (standart)", "Adet": 0, "Minimum": 200},
            {"Tür": "Diğer", "Kalem": "Nem Alıcı Jel", "Adet": 0, "Minimum": 50},
        ]
    edited_stock = st.data_editor(
        pd.DataFrame(stock), num_rows="dynamic", width="stretch", hide_index=True, key="stock_editor",
        column_config={"Tür": st.column_config.SelectboxColumn("Tür", options=["Kasa", "Kutu", "Diğer"], required=True)}
    ).fillna({"Tür": "Diğer", "Kalem": "", "Adet": 0, "Minimum": 0})

    if st.button("💾 Stoğu Kaydet", width="stretch"):
        write_json(STOCK_FILE, edited_stock.to_dict("records"))
        st.toast("Stok kaydedildi!", icon="✅")

    low = edited_stock[edited_stock["Adet"] < edited_stock["Minimum"]]
    for _, r in low.iterrows():
        st.warning(f"⚠️ **{r['Kalem']}** minimumun altında: {r['Adet']} / {r['Minimum']}")

    need_crates = sum(int(i.get("Kasa Sayısı", 0)) for i in st.session_state.cart)
    need_boxes = sum(int(i.get("Kasa Sayısı", 0)) * int(i.get("Kasadaki Kutu", 0)) for i in st.session_state.cart)
    have_crates = edited_stock[edited_stock["Tür"] == "Kasa"]["Adet"].sum()
    have_boxes = edited_stock[edited_stock["Tür"] == "Kutu"]["Adet"].sum()

    st.subheader("🛒 Sepetteki Siparişin Ambalaj İhtiyacı")
    n1, n2 = st.columns(2)
    n1.metric("Gereken Kasa", f"{need_crates:,}", f"Stok farkı: {have_crates - need_crates:,.0f}")
    n2.metric("Gereken Kutu", f"{need_boxes:,}", f"Stok farkı: {have_boxes - need_boxes:,.0f}")
    if (have_crates < need_crates or have_boxes < need_boxes) and st.session_state.cart:
        st.error("Stok bu sipariş için yetersiz, tedarik gerekli.")

    if st.session_state.cart and st.button("📉 Sepetteki Siparişi Stoktan Düş (her türün ilk kalemi)"):
        cur = edited_stock.copy()
        for tur, need in (("Kasa", need_crates), ("Kutu", need_boxes)):
            idx = cur.index[cur["Tür"] == tur]
            if len(idx):
                cur.loc[idx[0], "Adet"] -= need
        write_json(STOCK_FILE, cur.to_dict("records"))
        st.rerun()

# ------------------------------------------
# TAB 7: MÜŞTERİ GEÇMİŞİ
# ------------------------------------------
with tab7:
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

# ------------------------------------------
# TAB 8: GÜNLÜK DİZİM DEFTERİ
# ------------------------------------------
with tab8:
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
                ext = os.path.splitext(l_photo.name)[1].lower()
                photo_name = f"{l_date}_{uuid.uuid4().hex[:8]}{ext}"
                with open(os.path.join(LOG_PHOTOS_DIR, photo_name), "wb") as pf:
                    pf.write(l_photo.getbuffer())
            log.append({"id": uuid.uuid4().hex[:8], "Tarih": str(l_date), "Yer": l_place, "Müşteri": l_cust, "Ürün": l_prod,
                        "Adet": int(l_qty), "Kasa": float(l_crate), "İşçi": int(l_workers), "Not": l_note,
                        "Foto": photo_name, "Kaydeden": st.session_state.user_name})
            write_json(LOG_FILE, log)
            st.rerun()

    if log:
        days = sorted({e["Tarih"] for e in log}, reverse=True)
        day = st.selectbox("Gün", days)
        day_items = [e for e in log if e["Tarih"] == day]
        d1, d2 = st.columns(2)
        d1.metric("Günlük Toplam Adet", f"{sum(e['Adet'] for e in day_items):,}")
        d2.metric("Günlük Biten Kasa", f"{sum(e['Kasa'] for e in day_items):.1f}")
        st.dataframe(pd.DataFrame(day_items).drop(columns=["id", "Foto"]), width="stretch", hide_index=True)
        for e in day_items:
            if e.get("Foto") and os.path.exists(os.path.join(LOG_PHOTOS_DIR, e["Foto"])):
                with st.expander(f"📷 {e['Yer']} - {e['Ürün']}"):
                    st.image(os.path.join(LOG_PHOTOS_DIR, e["Foto"]))
        del_sel = st.selectbox("Silinecek kayıt:", [f"{e['id']} | {e['Yer']} - {e['Ürün']} ({e['Adet']})" for e in day_items])
        if st.button("🗑️ Seçili Kaydı Sil"):
            did = del_sel.split(" | ")[0]
            write_json(LOG_FILE, [e for e in log if e["id"] != did])
            st.rerun()
