import streamlit as st
import math
from utils.calculations import calculate_crate_capacity
from utils.storage import save_auto_recovery

def render_tab2():
    st.header("🧩 Dizim Şefi & Kutulama Operasyon Paneli")
    d_data = st.session_state.draft_data
    
    sales_unit = d_data.get("sales_unit", "Adet (Pcs)")
    piece_m2 = d_data.get("piece_m2", 0.061)
    target_pcs = d_data.get("target_pcs", 4000)
    target_m2 = d_data.get("target_m2", 244.0)
    needed_prod_pcs = d_data.get("needed_prod_pcs", 4000)
    needed_prod_m2 = d_data.get("needed_prod_m2", 244.0)
    p_thickness = d_data.get("p_thickness", 2.0)
    density = d_data.get("density", 2.7)
    crate_tare_kg = d_data.get("crate_tare_kg", 35.0)
    required_ops = d_data.get("required_ops", ["Dizim / File / Şinik Gerekli"])
    preset_data = d_data.get("preset_data")
    
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
        
        crate_pcs_cap, crate_m2_cap, crate_gross_weight = calculate_crate_capacity(
            pcs_per_box, boxes_in_crate, piece_m2, p_thickness, density, crate_tare_kg
        )
        
        if sales_unit == "Adet (Pcs)":
            total_boxes = math.ceil(target_pcs / pcs_per_box) if pcs_per_box > 0 else 1
            needed_crates = math.ceil(target_pcs / crate_pcs_cap) if crate_pcs_cap > 0 else 1
            st.info(f"**1 Kasa Kapasitesi:** {crate_pcs_cap} Adet ({crate_m2_cap:.2f} m²)")
        else:
            needed_crates = math.ceil(target_m2 / crate_m2_cap) if crate_m2_cap > 0 else 1
            total_boxes = needed_crates * boxes_in_crate
            st.info(f"**1 Kasa Kapasitesi:** {crate_m2_cap:.2f} m²")
            
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
        else:
            workers_count = st.number_input("Tezgahtaki İşçi Sayısı", value=2, step=1)
            daily_total_sheets = st.number_input("Bu Ürün İçin Ekip Günlük Toplam Üretim (Adet)", value=4000, step=100)
            daily_total_m2 = daily_total_sheets * piece_m2
            daily_crates = daily_total_sheets / crate_pcs_cap if crate_pcs_cap > 0 else 0
            
            if sales_unit == "Adet (Pcs)":
                needed_days = math.ceil(needed_prod_pcs / daily_total_sheets) if daily_total_sheets > 0 else 1
                st.metric("Günlük Ekip Dizim Kapasitesi", f"{daily_total_sheets:,.0f} Adet / Gün", f"~{daily_total_m2:.2f} m² / Gün")
            else:
                needed_days = math.ceil(needed_prod_m2 / daily_total_m2) if daily_total_m2 > 0 else 1
                st.metric("Günlük Ekip Dizim Kapasitesi", f"{daily_total_m2:.2f} m² / Gün", f"{daily_total_sheets:,.0f} Adet")
                
        st.metric("Tahmini İmalat Süresi", f"{needed_days} İş Günü")

    st.markdown("---")
    if st.button("➕ Bu Ürün & Müşteri Siparişini Sepete Ekle", use_container_width=True):
        st.session_state.cart.append({
            "Müşteri": d_data.get("customer_name", "Bilinmeyen"),
            "PO / Sipariş No": d_data.get("po_number", "PO-000"),
            "Ürün Adı": d_data.get("product_name", "Ürün"),
            "Tip": d_data.get("product_type", "Mozaik"),
            "Satış Birimi": sales_unit,
            "Ebat (cm)": f"{d_data.get('p_length', 30.5):.1f}x{d_data.get('p_width', 2.0):.1f}x{p_thickness:.1f}",
            "Stok Durumu": f"{d_data.get('stock_qty', 0)} ({sales_unit}) Stokta",
            "İmal Edilecek": f"{needed_prod_pcs:,} Adet" if sales_unit == "Adet (Pcs)" else f"{needed_prod_m2:.2f} m²",
            "İmalat Süresi": f"{needed_days} Gün",
            "Kutu İçi Adet": pcs_per_box, "Kutu İçi m²": round(box_net_m2, 3),
            "Kasadaki Kutu": boxes_in_crate, "1 Kasa Kapasite (Adet)": crate_pcs_cap,
            "1 Kasa Kapasite (m²)": crate_m2_cap, "1 Kasa Ağırlık (kg)": crate_gross_weight,
            "Kalın Şinik / Kutu": thick_sinik_per_box, "İnce Şinik / Kutu": thin_sinik_per_box,
            "Kasa Sayısı": int(needed_crates), "Kasa L": d_data.get("crate_length", 101.0),
            "Kasa W": d_data.get("crate_width", 101.0), "Kasa H": d_data.get("crate_height", 40.0),
            "Stackable": "Evet" if d_data.get("is_stackable", True) else "Hayır"
        })
        save_auto_recovery(st.session_state.cart, st.session_state.draft_data)
        st.toast("Sipariş sepete eklendi ve yedeklendi!", icon="✅")
