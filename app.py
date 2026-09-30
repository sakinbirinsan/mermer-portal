import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math

st.set_page_config(page_title="Mermer & Doğaltaş Konteyner Portalı", layout="wide")

st.title("🧱 Doğaltaş İhracat, Kasa & Konteyner Optimizasyon Portalı")
st.markdown("---")

if "cart" not in st.session_state:
    st.session_state.cart = []

tab1, tab2, tab3 = st.tabs([
    "📐 1. Ürün, Fire & Kasa Hesabı", 
    "🛒 2. Sipariş Sepeti / Karma Havuz", 
    "🚢 3. Konteyner Doluluk & Eyalet Limitleri"
])

# ------------------------------------------
# TAB 1: ÜRÜN, FİRE & KASA HESABI
# ------------------------------------------
with tab1:
    st.header("Ürün Ebatları, Fire ve Kasa Kapasitesi")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("1. Ürün Detayları")
        product_name = st.text_input("Ürün Adı / Kodu", value="Flute Moulding A")
        product_type = st.selectbox("Ürün Tipi", ["Mozaik", "Flute / Moulding", "Ebatlı Mermer / Plaka"])
        
        # Ölçü Birimi Seçimi
        unit_system = st.radio("Ölçü Birimi Seçimi", ["Metrik (cm / m²)", "Imperial (inch / sqft)"], horizontal=True)
        
        if "Metrik" in unit_system:
            p_length = st.number_input("Ürün Boyu (cm)", value=60.0, step=0.5)
            p_width = st.number_input("Ürün Genişliği (cm)", value=15.0, step=0.5)
            p_thickness = st.number_input("Ürün Kalınlığı (cm)", value=2.0, step=0.1)
        else:
            p_length_in = st.number_input("Ürün Boyu (inch)", value=24.0, step=0.5)
            p_width_in = st.number_input("Ürün Genişliği (inch)", value=6.0, step=0.5)
            p_thickness_in = st.number_input("Ürün Kalınlığı (inch)", value=0.75, step=0.05)
            
            p_length = p_length_in * 2.54
            p_width = p_width_in * 2.54
            p_thickness = p_thickness_in * 2.54
            
        density = st.number_input("Taş Yoğunluğu (gr/cm³)", value=2.7, step=0.1)

    with col2:
        st.subheader("2. Fire & Kesim Payları")
        saw_kerf = st.number_input("Testere / Bıçak Payı (mm)", value=3.0, step=0.5)
        edge_trim = st.number_input("Kenar / Pah Kırma Fire (%)", value=5.0, step=0.5)
        breakage_rate = st.number_input("Kırılma / Çatlama Fire (%)", value=3.0, step=0.5)
        
        target_m2 = st.number_input("Siparişteki Net Miktar (m²)", value=100.0, step=5.0)
        target_sqft = target_m2 * 10.7639
        st.caption(f"Karşılığı: **{target_sqft:.2f} sqft**")
        
        total_fire_pct = edge_trim + breakage_rate + ((saw_kerf / 10) * 2)
        required_gross_m2 = target_m2 * (1 + (total_fire_pct / 100))
        
        st.info(f"**Toplam Fire Oranı:** %{total_fire_pct:.2f}")
        st.warning(f"**Gerekli Brüt Taş (İmalat):** {required_gross_m2:.2f} m² ({required_gross_m2 * 10.7639:.1f} sqft)")

    with col3:
        st.subheader("3. Ahşap Kasa & Kapasite")
        crate_length = st.number_input("Kasa Dış Boy (cm)", value=110.0, step=1.0)
        crate_width = st.number_input("Kasa Dış En (cm)", value=110.0, step=1.0)
        crate_height = st.number_input("Kasa Dış Yükseklik (cm)", value=85.0, step=1.0)
        
        foam_thickness = st.number_input("Strafor / Pay Toleransı (cm)", value=3.0, step=0.5)
        crate_tare_kg = st.number_input("Boş Kasa Ağırlığı (Tara - kg)", value=40.0, step=5.0)

        # Otomatik Hesaplama
        net_c_l = crate_length - (2 * foam_thickness)
        net_c_w = crate_width - (2 * foam_thickness)
        net_c_h = crate_height - (2 * foam_thickness) - 10.0

        piece_m2 = (p_length / 100) * (p_width / 100)
        piece_weight = piece_m2 * (p_thickness / 100) * (density * 1000)
        
        fit_len = math.floor(net_c_l / p_length) if p_length > 0 else 1
        fit_wid = math.floor(net_c_w / p_width) if p_width > 0 else 1
        fit_hgt = math.floor(net_c_h / p_thickness) if p_thickness > 0 else 1
        
        calc_max_pieces = max(1, fit_len * fit_wid * fit_hgt)
        calc_crate_m2 = calc_max_pieces * piece_m2

        st.markdown("---")
        st.markdown("**Kasa Kapasitesi Düzeltme / Elle Müdahale:**")
        manual_override = st.checkbox("Kasa Kapasitesini Manuel Gir", value=False)
        
        if manual_override:
            crate_m2_capacity = st.number_input("1 Kasa Net m² Kapasitesi", value=round(calc_crate_m2, 2), step=0.5)
            max_pieces_per_crate = math.ceil(crate_m2_capacity / piece_m2) if piece_m2 > 0 else 1
        else:
            crate_m2_capacity = calc_crate_m2
            max_pieces_per_crate = calc_max_pieces

        crate_gross_weight = (max_pieces_per_crate * piece_weight) + crate_tare_kg

        st.success(f"**1 Kasa Kapasitesi:** {crate_m2_capacity:.2f} m² ({crate_m2_capacity * 10.7639:.1f} sqft)")
        st.success(f"**1 Kasa Ağırlığı:** {crate_gross_weight:.1f} kg ({crate_gross_weight * 2.20462:.1f} lbs)")

    st.markdown("---")
    
    # Sepete Ekleme
    c_add1, c_add2, c_add3 = st.columns([2, 2, 1])
    with c_add1:
        req_m2_order = st.number_input("Siparişteki Miktar (m²)", value=target_m2, key="order_m2_input")
    with c_add2:
        needed_crates = math.ceil(req_m2_order / crate_m2_capacity) if crate_m2_capacity > 0 else 1
        st.markdown(f"### Gerekli Kasa: **{needed_crates} Adet Kasa**")
    with c_add3:
        st.write("")
        st.write("")
        if st.button("➕ Konteynere Ekle", use_container_width=True):
            st.session_state.cart.append({
                "Ürün Adı": product_name,
                "Tip": product_type,
                "Ebat (cm)": f"{p_length:.1f}x{p_width:.1f}x{p_thickness:.1f}",
                "Kasa Ebatı (cm)": f"{crate_length}x{crate_width}x{crate_height}",
                "Kasa L": crate_length,
                "Kasa W": crate_width,
                "Kasa H": crate_height,
                "Kasa Sayısı": needed_crates,
                "Toplam m²": round(needed_crates * crate_m2_capacity, 2),
                "Toplam sqft": round(needed_crates * crate_m2_capacity * 10.7639, 1),
                "Tek Kasa Ağırlık (kg)": round(crate_gross_weight, 1),
                "Toplam Ağırlık (kg)": round(needed_crates * crate_gross_weight, 1),
                "Toplam Ağırlık (lbs)": round(needed_crates * crate_gross_weight * 2.20462, 0),
                "Brüt Taş m²": round(needed_crates * crate_m2_capacity * (1 + (total_fire_pct / 100)), 2)
            })
            st.toast(f"{product_name} havuz eklendi!", icon="✅")

# ------------------------------------------
# TAB 2: SİPARİŞ SEPETİ / KARMA HAVUZ
# ------------------------------------------
with tab2:
    st.header("🛒 Karma Kasa Yükleme Havuzu")
    
    if not st.session_state.cart:
        st.info("Henüz sepete ürün eklenmedi. 1. sekmeden ürün hesaplayıp ekleyebilirsiniz.")
    else:
        df_cart = pd.DataFrame(st.session_state.cart)
        st.dataframe(df_cart, use_container_width=True)
        
        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        total_crates = df_cart["Kasa Sayısı"].sum()
        total_m2_sum = df_cart["Toplam m²"].sum()
        total_weight_kg = df_cart["Toplam Ağırlık (kg)"].sum()
        total_weight_lbs = df_cart["Toplam Ağırlık (lbs)"].sum()
        
        col_t1.metric("Toplam Kasa", f"{total_crates} Kasa")
        col_t2.metric("Toplam Net m² / sqft", f"{total_m2_sum:.2f} m²", f"{total_m2_sum * 10.7639:,.0f} sqft")
        col_t3.metric("Toplam Ağırlık (kg)", f"{total_weight_kg:,.0f} kg")
        col_t4.metric("Toplam Ağırlık (lbs)", f"{total_weight_lbs:,.0f} lbs")
        
        if st.button("🗑️ Sepeti Temizle"):
            st.session_state.cart = []
            st.rerun()

# ------------------------------------------
# TAB 3: KONTEYNER & EYALET LİMİTLERİ
# ------------------------------------------
with tab3:
    st.header("🚢 Konteyner Doluluk & Eyalet Kara Yolu Sınırları")
    
    col_cnt1, col_cnt2 = st.columns(2)
    
    with col_cnt1:
        container_type = st.selectbox("Konteyner Tipi", [
            "20'lik Standart (20' DC) - Max Vol: 33.2 m³",
            "40'lık Standart (40' DC) - Max Vol: 67.7 m³",
            "40'lık High Cube (40' HC) - Max Vol: 76.2 m³"
        ])
    
    with col_cnt2:
        us_state_preset = st.selectbox("ABD Eyalet / Taşıma Limiti Şablonu", [
            "Standart / Genel Limit (44,000 lbs / ~19,950 kg)",
            "Ağır Tonaj / Overweight Permit (47,000 lbs / ~21,300 kg)",
            "Kısıtlı Eyaletler / Sıkı Limit (38,000 lbs / ~17,230 kg)",
            "Maksimum Konteyner Kapasitesi (24,000 kg / ~52,900 lbs)",
            "Özel / Manuel Limit Gir"
        ])

    # Limit Belirleme
    if "44,000" in us_state_preset:
        max_allowed_kg = 19958
    elif "47,000" in us_state_preset:
        max_allowed_kg = 21318
    elif "38,000" in us_state_preset:
        max_allowed_kg = 17236
    elif "Maksimum" in us_state_preset:
        max_allowed_kg = 24000
    else:
        max_allowed_kg = st.number_input("Özel Ağırlık Limiti Girin (kg)", value=20000, step=500)

    # Konteyner Ölçüleri
    if "20'" in container_type:
        c_l, c_w, c_h, max_v = 589.8, 235.2, 239.3, 33.2
    elif "40' HC" in container_type:
        c_l, c_w, c_h, max_v = 1203.2, 235.2, 269.8, 76.2
    else:
        c_l, c_w, c_h, max_v = 1203.2, 235.2, 239.3, 67.7

    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        total_weight_kg = df_cart["Toplam Ağırlık (kg)"].sum()
        
        total_volume = 0
        for item in st.session_state.cart:
            v_crate = (item["Kasa L"] * item["Kasa W"] * item["Kasa H"]) / 1_000_000
            total_volume += v_crate * item["Kasa Sayısı"]

        weight_pct = (total_weight_kg / max_allowed_kg) * 100
        vol_pct = (total_volume / max_v) * 100
        
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("Seçilen Eyalet Ağırlık Limiti", f"{max_allowed_kg:,.0f} kg", f"{max_allowed_kg * 2.20462:,.0f} lbs")
        c_m2.metric("Ağırlık Doluluk Oranı", f"%{weight_pct:.1f}", f"{total_weight_kg:,.0f} kg")
        c_m3.metric("Ağırlık Statüsü", "UYGUN ✅" if weight_pct <= 100 else "AŞIRI YÜKLEME! ⚠️", 
                   delta_color="normal" if weight_pct <= 100 else "inverse")

        # 3D Visualizer
        st.subheader("📦 Konteyner Yerleşim Görseli")
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
                    opacity=0.6, name=f"{item['Ürün Adı']}"
                ))
                curr_y += cW

        fig.update_layout(scene=dict(xaxis=dict(range=[0, c_l]), yaxis=dict(range=[0, c_w]), zaxis=dict(range=[0, c_h]), aspectmode='data'))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Konteyner analizi için lütfen sepete ürün/kasa ekleyin.")