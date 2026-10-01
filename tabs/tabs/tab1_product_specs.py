import streamlit as st

import math

from utils.calculations import calculate_piece_m2, calculate_fire_and_gross

from utils.storage import save_auto_recovery

def render_tab1():

    st.header("1. Ürün, Müşteri, Fire ve Ahşap Kasa Spesifikasyonları")

    

    col_cust1, col_cust2 = st.columns(2)

    with col_cust1:

        customer_name = st.text_input("Müşteri / Şirket Adı", value=st.session_state.draft_data.get("customer_name", "Floor & Decor Stone Corp."))

    with col_cust2:

        po_number = st.text_input("Müşteri PO / Sipariş No", value=st.session_state.draft_data.get("po_number", "PO-2026-089"))

    col1, col2, col3 = st.columns(3)

    

    with col1:

        st.subheader("📦 Ürün Tanımı")

        product_name = st.text_input("Ürün Adı / Kodu", value=st.session_state.draft_data.get("product_name", "bullnose / pencil"))

        product_type = st.selectbox("Ürün Tipi", ["Flute / Moulding", "Mozaik", "Ebatlı Mermer / Plaka"])

        sales_unit = st.radio("Satış / Hesaplama Birimi", ["Adet (Pcs)", "m² Bazlı"], horizontal=True)

        unit_system = st.radio("Ölçü Birimi System", ["Metrik (cm / m²)", "Imperial (inch / sqft)"], horizontal=True)

        

        if "Metrik" in unit_system:

            p_length = st.number_input("Ürün / Parça Boyu (cm)", value=st.session_state.draft_data.get("p_length", 30.5), step=0.5)

            p_width = st.number_input("Ürün / Parça Eni (cm)", value=st.session_state.draft_data.get("p_width", 2.0), step=0.1)

            p_thickness = st.number_input("Kalınlık (cm)", value=st.session_state.draft_data.get("p_thickness", 2.0), step=0.1)

        else:

            p_length_in = st.number_input("Ürün Boyu (inch)", value=12.0, step=0.5)

            p_width_in = st.number_input("Ürün Eni (inch)", value=0.78, step=0.05)

            p_thickness_in = st.number_input("Kalınlık (inch)", value=0.78, step=0.05)

            p_length = p_length_in * 2.54

            p_width = p_width_in * 2.54

            p_thickness = p_thickness_in * 2.54

            

        density = st.number_input("Taş Yoğunluğu (gr/cm³)", value=2.7, step=0.1)

        piece_m2 = calculate_piece_m2(p_length, p_width)

    with col2:

        st.subheader("📈 Fire & Hammadde Metrajı")

        saw_kerf = st.number_input("Testere Payı (mm)", value=1.0, step=0.5)

        edge_trim = st.number_input("Kenar Fire / Kalibre (%)", value=0.0, step=0.5)

        breakage_rate = st.number_input("Kırılma / Seleksiyon Fire (%)", value=15.0, step=0.5)

        

        if sales_unit == "Adet (Pcs)":

            target_pcs = st.number_input("Net Sipariş Miktarı (Adet)", value=st.session_state.draft_data.get("target_pcs", 4000), step=100)

            target_m2 = target_pcs * piece_m2

            st.caption(f"Adet Karşılığı Alan: **{target_m2:.2f} m²** ({target_m2 * 10.7639:.1f} sqft)")

        else:

            target_m2 = st.number_input("Net Sipariş Miktarı (m²)", value=st.session_state.draft_data.get("target_m2", 150.0), step=10.0)

            target_pcs = math.ceil(target_m2 / piece_m2) if piece_m2 > 0 else 0

            st.caption(f"m² Karşılığı Adet: **{target_pcs:,} Adet**")

        

        total_fire_pct, req_gross_m2, req_gross_pcs = calculate_fire_and_gross(

            target_m2, target_pcs, sales_unit, piece_m2, edge_trim, breakage_rate, saw_kerf

        )

        

        st.info(f"**Toplam Üretim Firesi:** %{total_fire_pct:.2f}")

        if sales_unit == "Adet (Pcs)":

            st.warning(f"**Gerekli Brüt Taş:** {req_gross_pcs:,} Adet ({req_gross_m2:.2f} m²)")

        else:

            st.warning(f"**Gerekli Brüt Taş:** {req_gross_m2:.2f} m²")

    with col3:

        st.subheader("🪵 Ahşap Kasa Dış Ölçüleri")

        crate_length = st.number_input("Kasa Dış Boy (cm)", value=101.0, step=1.0)

        crate_width = st.number_input("Kasa Dış En (cm)", value=101.0, step=1.0)

        crate_height = st.number_input("Kasa Dış Yükseklik (cm)", value=40.0, step=1.0)

        crate_tare_kg = st.number_input("Boş Kasa Ağırlığı (kg)", value=35.0, step=5.0)

        is_stackable = st.checkbox("Üst Üste İstiflenebilir (Stackable)", value=True)

    if st.button("💾 Girdileri Taslak Olarak Geçici Kaydet", key="save_tab1"):

        st.session_state.draft_data.update({

            "customer_name": customer_name, "po_number": po_number,

            "product_name": product_name, "product_type": product_type,

            "sales_unit": sales_unit, "p_length": p_length, "p_width": p_width,

            "p_thickness": p_thickness, "density": density, "piece_m2": piece_m2,

            "target_pcs": target_pcs, "target_m2": target_m2, "total_fire_pct": total_fire_pct,

            "crate_length": crate_length, "crate_width": crate_width, "crate_height": crate_height,

            "crate_tare_kg": crate_tare_kg, "is_stackable": is_stackable

        })

        save_auto_recovery(st.session_state.cart, st.session_state.draft_data)

        st.toast("1. Sekme girdileri hafızaya kaydedildi!", icon="💾")
