import streamlit as st
import math
import json
import os
from utils.calculations import calculate_piece_m2, calculate_fire_and_gross
from utils.storage import save_auto_recovery, load_all_presets, PRESETS_DIR

def render_tab1():
    st.header("1. Ürün Reçeteleri (Preset), Müşteri ve Kasa Spesifikasyonları")
    
    # Presets klasörünün varlığını garanti edelim
    os.makedirs(PRESETS_DIR, exist_ok=True)

    all_presets = load_all_presets()
    preset_options = ["Özel / Manuel Giriş"] + list(all_presets.keys())

    # Session State Başlatma Kontrolleri
    if "draft_data" not in st.session_state:
        st.session_state.draft_data = {}

    col_p1, col_p2 = st.columns([3, 1])
    with col_p1:
        selected_preset_name = st.selectbox(
            "⭐ Kayıtlı Standart Ürün Reçeteleri (Preset):", 
            preset_options,
            key="preset_selector"
        )
    
    preset_data = all_presets.get(selected_preset_name)

    with col_p2:
        st.write("")
        st.write("") # Hizalama için boşluk
        if selected_preset_name != "Özel / Manuel Giriş" and preset_data:
            if st.button("🗑️ Seçili Reçeteyi Kütüphaneden Sil", use_container_width=True, key="btn_delete_preset"):
                preset_file_name = preset_data.get("file_name")
                if preset_file_name:
                    file_to_del = os.path.join(PRESETS_DIR, preset_file_name)
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
        customer_name = st.text_input("Müşteri / Şirket Adı", value=default_cust, key="input_cust_name")
    with col_cust2:
        default_po = preset_data["po_number"] if preset_data else st.session_state.draft_data.get("po_number", "PO-2026-089")
        po_number = st.text_input("Müşteri PO / Sipariş No", value=default_po, key="input_po_num")

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📦 Ürün & Satış Tanımı")
        default_pname = preset_data["product_name"] if preset_data else st.session_state.draft_data.get("product_name", "bullnose / pencil")
        product_name = st.text_input("Ürün Adı / Kodu", value=default_pname, key="input_prod_name")
        
        product_types = ["Flute / Moulding", "Mozaik", "Ebatlı Mermer / Plaka"]
        default_ptype_idx = product_types.index(preset_data["product_type"]) if preset_data and preset_data.get("product_type") in product_types else 0
        product_type = st.selectbox("Ürün Tipi", product_types, index=default_ptype_idx, key="input_prod_type")
        
        sales_unit = st.radio("Satış / Hesaplama Birimi", ["Adet (Pcs)", "m² Bazlı"], horizontal=True, key="input_sales_unit")
        unit_system = st.radio("Ölçü Birimi System", ["Metrik (cm / m²)", "Imperial (inch / sqft)"], horizontal=True, key="input_unit_sys")
        
        if "Metrik" in unit_system:
            def_l = preset_data["p_length"] if preset_data else st.session_state.draft_data.get("p_length", 30.5)
            def_w = preset_data["p_width"] if preset_data else st.session_state.draft_data.get("p_width", 2.0)
            def_t = preset_data["p_thickness"] if preset_data else st.session_state.draft_data.get("p_thickness", 2.0)
            
            p_length = st.number_input("Ürün / Parça Boyu (cm)", value=float(def_l), step=0.5, key="input_p_len")
            p_width = st.number_input("Ürün / Parça Eni (cm)", value=float(def_w), step=0.1, key="input_p_wid")
            p_thickness = st.number_input("Kalınlık (cm)", value=float(def_t), step=0.1, key="input_p_thick")
        else:
            p_length_in = st.number_input("Ürün Boyu (inch)", value=12.0, step=0.5, key="input_p_len_in")
            p_width_in = st.number_input("Ürün Eni (inch)", value=0.78, step=0.05, key="input_p_wid_in")
            p_thickness_in = st.number_input("Kalınlık (inch)", value=0.78, step=0.05, key="input_p_thick_in")
            p_length = p_length_in * 2.54
            p_width = p_width_in * 2.54
            p_thickness = p_thickness_in * 2.54
            
        def_density = preset_data["density"] if preset_data else 2.7
        density = st.number_input("Taş Yoğunluğu (gr/cm³)", value=float(def_density), step=0.1, key="input_density")
        piece_m2 = calculate_piece_m2(p_length, p_width)

    with col2:
        st.subheader("🏬 Stok & İmalat Adımları")
        required_ops = st.multiselect(
            "Yapılacak Operasyonlar",
            ["Ebatlama / Kesim Gerekli", "Dizim / File / Şinik Gerekli", "Hazır Stok (Sadece Paketleme)"],
            default=["Ebatlama / Kesim Gerekli", "Dizim / File / Şinik Gerekli"],
            key="input_ops"
        )

        def_tpcs = preset_data["target_pcs"] if preset_data else st.session_state.draft_data.get("target_pcs", 4000)
        
        if sales_unit == "Adet (Pcs)":
            target_pcs = st.number_input("Net Sipariş Miktarı (Adet)", value=int(def_tpcs), step=100, key="input_target_pcs")
            target_m2 = target_pcs * piece_m2
            stock_qty = st.number_input("Mevcut Hazır Stok (Adet)", value=0, step=100, key="input_stock_pcs")
            needed_prod_pcs = max(0, target_pcs - stock_qty)
            needed_prod_m2 = needed_prod_pcs * piece_m2
            st.caption(f"İmal Edilecek Net Miktar: **{needed_prod_pcs:,} Adet** ({needed_prod_m2:.2f} m²)")
        else:
            target_m2 = st.number_input("Net Sipariş Miktarı (m²)", value=float(st.session_state.draft_data.get("target_m2", 150.0)), step=10.0, key="input_target_m2")
            target_pcs = math.ceil(target_m2 / piece_m2) if piece_m2 > 0 else 0
            stock_qty = st.number_input("Mevcut Hazır Stok (m²)", value=0.0, step=10.0, key="input_stock_m2")
            needed_prod_m2 = max(0.0, target_m2 - stock_qty)
            needed_prod_pcs = math.ceil(needed_prod_m2 / piece_m2) if piece_m2 > 0 else 0
            st.caption(f"İmal Edilecek Net Miktar: **{needed_prod_m2:.2f} m²** ({needed_prod_pcs:,} Adet)")

        saw_kerf = st.number_input("Testere Payı (mm)", value=1.0, step=0.5, key="input_saw_kerf")
        edge_trim = st.number_input("Kenar Fire / Kalibre (%)", value=0.0, step=0.5, key="input_edge_trim")
        breakage_rate = st.number_input("Kırılma / Seleksiyon Fire (%)", value=15.0, step=0.5, key="input_breakage")
        
        total_fire_pct, required_gross_m2, required_gross_pcs = calculate_fire_and_gross(
            needed_prod_m2, needed_prod_pcs, sales_unit, piece_m2, edge_trim, breakage_rate, saw_kerf
        )
        
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

        crate_length = st.number_input("Kasa Dış Boy (cm)", value=float(def_cl), step=1.0, key="input_crate_len")
        crate_width = st.number_input("Kasa Dış En (cm)", value=float(def_cw), step=1.0, key="input_crate_wid")
        crate_height = st.number_input("Kasa Dış Yükseklik (cm)", value=float(def_ch), step=1.0, key="input_crate_hgt")
        crate_tare_kg = st.number_input("Boş Kasa Ağırlığı (kg)", value=float(def_ctare), step=5.0, key="input_crate_tare")
        is_stackable = st.checkbox("Üst Üste İstiflenebilir (Stackable)", value=True, key="input_stackable")

    # TASLAK HAFIZA UPDATE
    st.session_state.draft_data.update({
        "customer_name": customer_name, "po_number": po_number, "product_name": product_name,
        "product_type": product_type, "sales_unit": sales_unit, "p_length": p_length,
        "p_width": p_width, "p_thickness": p_thickness, "density": density, "piece_m2": piece_m2,
        "target_pcs": target_pcs, "target_m2": target_m2, "stock_qty": stock_qty,
        "needed_prod_pcs": needed_prod_pcs, "needed_prod_m2": needed_prod_m2,
        "required_ops": required_ops, "preset_data": preset_data, "crate_length": crate_length,
        "crate_width": crate_width, "crate_height": crate_height, "crate_tare_kg": crate_tare_kg,
        "is_stackable": is_stackable
    })

    st.markdown("---")
    st.subheader("💾 Ekrandaki Parametreleri Yeni Reçete Olarak Kaydet")
    col_pr1, col_pr2 = st.columns([3, 1])
    
    default_new_preset_title = f"[{customer_name}] {product_name} ({p_length}x{p_width} cm)"
    
    with col_pr1:
        new_preset_title = st.text_input("Reçete Adı", value=default_new_preset_title, key="input_new_preset_title")
    with col_pr2:
        st.write("")
        st.write("")
        if st.button("💾 Reçeteyi Kütüphaneye Ekle", use_container_width=True, key="btn_add_preset"):
            if not new_preset_title.strip():
                st.error("Lütfen geçerli bir reçete adı girin!")
            else:
                # Dosya adını güvenli karakterlerle temizleme
                clean_filename = "".join([c for c in new_preset_title if c.isalnum() or c in (' ', '_', '-')]).strip() + ".json"
                file_path = os.path.join(PRESETS_DIR, clean_filename)
                
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
                
                try:
                    with open(file_path, "w", encoding="utf-8") as pf:
                        json.dump(save_preset_payload, pf, ensure_ascii=False, indent=4)
                    st.toast(f"'{new_preset_title}' reçetesi kaydedildi!", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Kayıt esnasında bir hata oluştu: {e}")
