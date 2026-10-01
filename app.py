import streamlit as st
import os
import json
from utils.storage import ensure_storage_dirs, load_auto_recovery, clear_auto_recovery, TEMPLATES_DIR
from tabs.tab1_product_specs import render_tab1
from tabs.tab2_packing_plan import render_tab2
from tabs.tab3_packing_list import render_tab3
from tabs.tab4_export_limits import render_tab4
from tabs.tab5_template_mgmt import render_tab5

st.set_page_config(
    page_title="Emre Doğaltaş Entegre Yönetim Portalı",
    page_icon="🗿",
    layout="wide"
)

ensure_storage_dirs()

st.title("🗿 Emre Doğaltaş Üretim, Dizim, İhracat & Konteyner Portalı")
st.caption("Fabrika Müdürü, Dizim Şefi, İhracat Sorumlusu ve Yönetim İçin Ortak Operasyon Paneli")
st.markdown("---")

if "cart" not in st.session_state:
    st.session_state.cart = []
if "draft_data" not in st.session_state:
    st.session_state.draft_data = {}

# Arka Planda Kurtarma Verisi Kontrolü
rec_data = load_auto_recovery()
if rec_data and not st.session_state.cart and rec_data.get("cart"):
    st.warning("⚠️ **Son Oturum Kurtarıldı:** Son çalışmanız arka plandan getirildi.")
    if st.button("🔄 Son Kurtarılan Verileri Sepete Yükle"):
        st.session_state.cart = rec_data.get("cart", [])
        st.session_state.draft_data = rec_data.get("draft_data", {})
        st.rerun()

# Sidebar Taslak Yönetimi
st.sidebar.header("📁 Sunucudaki Kayıtlı Taslaklar")
saved_files = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".json") and not f.startswith("_")]

if saved_files:
    selected_template = st.sidebar.selectbox("Hızlı Taslak Seçin:", ["Seçiniz..."] + saved_files)
    if selected_template != "Seçiniz...":
        template_path = os.path.join(TEMPLATES_DIR, selected_template)
        with open(template_path, "r", encoding="utf-8") as f:
            t_data = json.load(f)
            
        col_sb1, col_sb2 = st.columns([3, 1])
        with col_sb1:
            if st.button("⚡ Ekrana Yükle", use_container_width=True):
                st.session_state.cart = t_data.get("sepet", [])
                st.toast(f"{selected_template} yüklendi!", icon="🚀")
                st.rerun()
        with col_sb2:
            if st.button("🗑️", help="Bu taslağı sunucudan sil", use_container_width=True):
                os.remove(template_path)
                st.toast(f"{selected_template} silindi!", icon="🗑️")
                st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Tüm Sepeti Temizle", use_container_width=True):
    st.session_state.cart = []
    clear_auto_recovery()
    st.rerun()

# Sekme Yönlendirmeleri
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📐 1. Ürün, Reçete & Stok Parametreleri", 
    "🧩 2. Dizim, Şinik & Kutu Planı",
    "🛒 3. Sipariş Havuzu & Packing List", 
    "🚢 4. İhracat & Konteyner Doluluk",
    "💾 5. Yönetici Şablon & Onay Yönetimi"
])

with tab1:
    render_tab1()
with tab2:
    render_tab2()
with tab3:
    render_tab3()
with tab4:
    render_tab4()
with tab5:
    render_tab5()
