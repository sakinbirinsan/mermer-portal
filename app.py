"""
Emre Doğaltaş Karma Sipariş, Müşteri Takipli Üretim & Konteyner Portalı
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import json

st.set_page_config(page_title="Mermer & Doğaltaş Entegre Yönetim Portalı", layout="wide")

st.title("🗿 Emre Doğaltaş Entegre Mermer Üretim, Dizim, İhracat & Konteyner Portalı")
st.caption("Fabrika Müdürü, Dizim Şefi, İhracat Sorumlusu ve Yönetim İçin Ortak Operasyon Paneli")
st.markdown("---")

if "cart" not in st.session_state:
    st.session_state.cart = []

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📐 1. Ürün & Kasa Parametreleri", 
    "🧩 2. Dizim Şefi & Vardiya Planı",
    "🛒 3. Sipariş Havuzu & Packing List", 
    "🚢 4. İhracat & Konteyner Doluluk",
    "💾 5. Yönetici Şablon & Onay Yönetimi"
])

# ------------------------------------------
# TAB 1: ÜRÜN & KASA HESABI
# ------------------------------------------
with tab1:
    st.header("1. Ürün, Müşteri, Fire ve Ahşap Kasa Spesifikasyonları")
    
    col_cust1, col_cust2 = st.columns(2)
    with col_cust1:
        customer_name = st.text_input("Müşteri / Şirket Adı", value="Apex Tile & Stone Corp.")
    with col_cust2:
        po_number = st.text_input("Müşteri PO / Sipariş No", value="PO-2026-089")

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📦 Ürün Tanımı")
        product_name = st.text_input("Ürün Adı / Kodu", value="Carrara Basketweave Mosaic")
        product_type = st.selectbox("Ürün Tipi", ["Mozaik", "Flute / Moulding", "Ebatlı Mermer / Plaka"])
        
        unit_system = st.radio("Ölçü Birimi", ["Metrik (cm / m²)", "Imperial (inch / sqft)"], horizontal=True)
        
        if "Metrik" in unit_system:
            p_length = st.number_input("Ürün / File Boyu (cm)", value=30.5, step=0.5)
            p_width = st.number_input("Ürün / File Eni (cm)", value=30.5, step=0.5)
            p_thickness = st.number_input("Kalınlık (cm)", value=1.0, step=0.1)
        else:
            p_length_in = st.number_input("Ürün Boyu (inch)", value=12.0, step=0.5)
            p_width_in = st.number_input("Ürün Eni (inch)", value=12.0, step=0.5)
            p_thickness_in = st.number_input("Kalınlık (inch)", value=0.38, step=0.05)
            
            p_length = p_length_in * 2.54
            p_width = p_width_in * 2.54
            p_thickness = p_thickness_in * 2.54
            
        density = st.number_input("Taş Yoğunluğu (gr/cm³)", value=2.7, step=0.1)

    with col2:
        st.subheader("📈Fire & Hammadde Metrajı")
        saw_kerf = st.number_input("Testere Payı (mm)", value=3.0, step=0.5)
        edge_trim = st.number_input("Kenar Fire / Kalibre (%)", value=5.0, step=0.5)
        breakage_rate = st.number_input("Kırılma / Seleksiyon Fire (%)", value=4.0, step=0.5)
        
        target_m2 = st.number_input("Net Sipariş Miktarı (m²)", value=150.0, step=10.0)
        target_sqft = target_m2 * 10.7639
        st.caption(f"Imperial Karşılığı: **{target_sqft:,.1f} sqft**")
        
        total_fire_pct = edge_trim + breakage_rate + ((saw_kerf / 10) * 2)
        required_gross_m2 = target_m2 * (1 + (total_fire_pct / 100))
        
        st.info(f"**Toplam Üretim Firesi:** %{total_fire_pct:.2f}")
        st.warning(f"**Gerekli Brüt Taş (Depodan Çıkacak):** {required_gross_m2:.2f} m²")

    with col3:
        st.subheader("🪵 Ahşap Kasa ve Paketleme")
        crate_length = st.number_input("Kasa Dış Boy (cm)", value=115.0, step=1.0)
        crate_width = st.number_input("Kasa Dış En (cm)", value=115.0, step=1.0)
        crate_height = st.number_input("Kasa Dış Yükseklik (cm)", value=90.0, step=1.0)
        
        crate_tare_kg = st.number_input("Boş Kasa Ağırlığı (kg)", value=45.0, step=5.0)
        is_stackable = st.checkbox("Üst Üste İstiflenebilir (Stackable)", value=True)

        if product_type == "Mozaik":
            st.markdown("---")
            st.markdown("**Mozaik Kutu / Kasalama:**")
            box_m2 = st.number_input("1 Kutu İçi m²", value=0.93, step=0.05)
            boxes_in_crate = st.number_input("1 Kasadaki Kutu Sayısı", value=54, step=1)
            calc_crate_m2 = box_m2 * boxes_in_crate
        else:
            net_c_l = crate_length - 6.0
            net_c_w = crate_width - 6.0
            net_c_h = crate_height - 10.0
            piece_m2 = (p_length / 100) * (p_width / 100)
            fit_len = math.floor(net_c_l / p_length) if p_length > 0 else 1
            fit_wid = math.floor(net_c_w / p_width) if p_width > 0 else 1
            fit_hgt = math.floor(net_c_h / p_thickness) if p_thickness > 0 else 1
            calc_crate_m2 = (fit_len * fit_wid * fit_hgt) * piece_m2

        crate_m2_capacity = st.number_input("1 Kasa Kapasitesi (m²)", value=round(calc_crate_m2, 2))
        piece_m2_val = (p_length / 100) * (p_width / 100)
        total_pcs_in_crate = math.ceil(crate_m2_capacity / piece_m2_val) if piece_m2_val > 0 else 1
        stone_weight = total_pcs_in_crate * piece_m2_val * (p_thickness / 100) * (density * 1000)
        crate_gross_weight = stone_weight + crate_tare_kg

        st.success(f"**1 Kasa Ağırlığı:** {crate_gross_weight:.1f} kg ({crate_gross_weight * 2.20462:,.0f} lbs)")

# ------------------------------------------
# TAB 2: DİZİM ŞEFİ & VARDİYA PLANLAMA
# ------------------------------------------
with tab2:
    st.header("🧩 Dizim Şefi Operasyon & Vardiya Paneli")
    st.write("Bu bölüm fabrika dizim başı ve ustaların günlük imalat hızını planlaması içindir.")
    
    col_d1, col_d2, col_d3 = st.columns(3)
    
    with col_d1:
        st.subheader("⚙️ Dizim & Seperatör Detayı")
        sinik_per_sheet = st.number_input("1 Fileye Giden Şinik / Taş Adedi", value=36, step=1)
        seperator_type = st.selectbox("Seperatör / Kalıp Tipi", ["Plastik Seperatör", "Sünger Şerit", "Karton / Kağıt", "Yok / Dökme"])
        glue_type = st.selectbox("Tutkal / File Tipi", ["Fiber File + Tutkal", "Kağıt Ön Yüz", "Nylon File"])

    with col_d2:
        st.subheader("👥 Vardiya & İşçilik")
        workers_count = st.number_input("Dizim Tezgahındaki İşçi Sayısı", value=6, step=1)
        daily_pcs_per_worker = st.number_input("İşçi Başı Günlük Dizim (File/Adet)", value=80, step=5)
        
        sheet_m2 = (p_length / 100) * (p_width / 100)
        daily_total_sheets = workers_count * daily_pcs_per_worker
        daily_total_m2 = daily_total_sheets * sheet_m2
        
        st.metric("Günlük Toplam Dizim Kapasitesi", f"{daily_total_m2:.2f} m² / Gün", f"{daily_total_sheets} File")

    with col_d3:
        st.subheader("⏱ Termin & İmalat Süresi")
        needed_days = math.ceil(target_m2 / daily_total_m2) if daily_total_m2 > 0 else 1
        total_sinik_needed = math.ceil(target_m2 / sheet_m2) * sinik_per_sheet if sheet_m2 > 0 else 0
        
        st.metric("Tahmini Dizim Tamamlanma Süresi", f"{needed_days} İş Günü")
        st.metric("Toplam Kullanılacak Şinik/Taş Parçası", f"{total_sinik_needed:,.0f} Adet")

    # Ekleme Butonu
    st.markdown("---")
    if st.button("➕ Bu Ürün & Müşteri Siparişini Sepete Ekle", use_container_width=True):
        needed_crates = math.ceil(target_m2 / crate_m2_capacity) if crate_m2_capacity > 0 else 1
        st.session_state.cart.append({
            "Müşteri": customer_name,
            "PO / Sipariş No": po_number,
            "Ürün Adı": product_name,
            "Tip": product_type,
            "Ebat (cm)": f"{p_length:.1f}x{p_width:.1f}x{p_thickness:.1f}",
            "Günlük Dizim (m²)": round(daily_total_m2, 2),
            "Tahmini Dizim Süresi": f"{needed_days} Gün",
            "Kasa Ebatı (cm)": f"{crate_length}x{crate_width}x{crate_height}",
            "Kasa L": crate_length,
            "Kasa W": crate_width,
            "Kasa H": crate_height,
            "Stackable": "Evet" if is_stackable else "Hayır",
            "Kasa Sayısı": needed_crates,
            "Toplam m²": round(needed_crates * crate_m2_capacity, 2),
            "Toplam sqft": round(needed_crates * crate_m2_capacity * 10.7639, 1),
            "Tek Kasa Ağırlık (kg)": round(crate_gross_weight, 1),
            "Toplam Ağırlık (kg)": round(needed_crates * crate_gross_weight, 1),
            "Toplam Ağırlık (lbs)": round(needed_crates * crate_gross_weight * 2.20462, 0),
            "Brüt Taş m²": round(needed_crates * crate_m2_capacity * (1 + (total_fire_pct / 100)), 2)
        })
        st.toast(f"{customer_name} - {product_name} sepete eklendi!", icon="✅")

# ------------------------------------------
# TAB 3: SIPARIS HAVUZU & PACKING LIST
# ------------------------------------------
with tab3:
    st.header("🛒 Sipariş Havuzu & Çeki Listesi (Packing List)")
    
    if not st.session_state.cart:
        st.info("Sepet henüz boş. 1. ve 2. sekmelerden ürün ekleyebilirsiniz.")
    else:
        df_cart = pd.DataFrame(st.session_state.cart)
        st.dataframe(df_cart, use_container_width=True)
        
        c_p1, c_p2, c_p3, c_p4 = st.columns(4)
        tot_crates = df_cart["Kasa Sayısı"].sum()
        tot_m2 = df_cart["Toplam m²"].sum()
        tot_kg = df_cart["Toplam Ağırlık (kg)"].sum()
        tot_gross_m2 = df_cart["Brüt Taş m²"].sum()
        
        c_p1.metric("Toplam Kasa Adedi", f"{tot_crates} Kasa")
        c_p2.metric("Toplam Net m²", f"{tot_m2:.2f} m²", f"{tot_m2 * 10.7639:,.0f} sqft")
        c_p3.metric("Toplam Brüt Ağırlık", f"{tot_kg:,.0f} kg", f"{tot_kg * 2.20462:,.0f} lbs")
        c_p4.metric("Depodan Çıkacak Brüt Taş", f"{tot_gross_m2:.2f} m²")

        st.markdown("---")
        if st.button("🗑️️ Sepeti Temizle"):
            st.session_state.cart = []
            st.rerun()

# ------------------------------------------
# TAB 4: İHRACAT & KONTEYNER DOLULUK
# ------------------------------------------
with tab4:
    st.header("🚢 İhracat, ABD Karayolu Limiti & 3D Visualizer")
    
    col_ex1, col_ex2 = st.columns(2)
    
    with col_ex1:
        container_type = st.selectbox("Konteyner Tipi", [
            "20'lik Standart (20' DC) - Max Vol: 33.2 m³",
            "40'lık Standart (40' DC) - Max Vol: 67.7 m³",
            "40'lık High Cube (40' HC) - Max Vol: 76.2 m³"
        ])
    
    with col_ex2:
        us_state_preset = st.selectbox("ABD Eyalet / Karayolu Ağırlık Sınırı", [
            "Standart / Genel Limit (44,000 lbs / ~19,958 kg)",
            "Ağır Tonaj İzinli / Overweight Permit (47,000 lbs / ~21,318 kg)",
            "Sıkı Limitli Eyaletler (38,000 lbs / ~17,236 kg)",
            "Maksimum Konteyner Kapasitesi (24,000 kg / ~52,900 lbs)",
            "Özel Manuel Limit"
        ])

    if "44,000" in us_state_preset:
        max_allowed_kg = 19958
    elif "47,000" in us_state_preset:
        max_allowed_kg = 21318
    elif "38,000" in us_state_preset:
        max_allowed_kg = 17236
    elif "Maksimum" in us_state_preset:
        max_allowed_kg = 24000
    else:
        max_allowed_kg = st.number_input("Özel Limit (kg)", value=20000)

    if "20'" in container_type:
        c_l, c_w, c_h, max_v = 589.8, 235.2, 239.3, 33.2
    elif "40' HC" in container_type:
        c_l, c_w, c_h, max_v = 1203.2, 235.2, 269.8, 76.2
    else:
        c_l, c_w, c_h, max_v = 1203.2, 235.2, 239.3, 67.7

    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        total_weight_kg = df_cart["Toplam Ağırlık (kg)"].sum()
        
        weight_pct = (total_weight_kg / max_allowed_kg) * 100
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Ağırlık Limiti", f"{max_allowed_kg:,.0f} kg")
        m2.metric("Mevcut Konteyner Ağırlığı", f"{total_weight_kg:,.0f} kg", f"%{weight_pct:.1f} Dolu")
        m3.metric("İhracat Onay Statüsü", "UYGUN ✅" if weight_pct <= 100 else "AĞIR TONAJ UYARISI ⚠️")

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
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------
# TAB 5: YÖNETİCİ ŞABLON & ONAY YÖNETİMİ
# ------------------------------------------
with tab5:
    st.header("💾 Yönetici Şablon, Onay & İmalat Talimatı")
    
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        st.subheader("📝 Sipariş Reçetesini Kaydet")
        order_no = st.text_input("Konteyner / Proje Dosya Kodu", value="KONTEYNER-2026-01")
        approval_status = st.selectbox("Yönetici Onay Durumu", ["Taslak / İncelemede", "Dizim Onayladı", "İhracat Onayladı", "YÖNETİM ONAYLADI (Üretime Verilsin)"])
        exec_notes = st.text_area("Fabrika & Paketleme Özel Talimatları", value="Kasalar fumigasyonlu ve alt kısmı forklift girişine uygun takozlu hazırlanacak. Nem alıcı jel konulacak.")

        if st.session_state.cart:
            payload = {
                "proje_kodu": order_no,
                "onay_durumu": approval_status,
                "yonetici_notu": exec_notes,
                "sepet": st.session_state.cart
            }
            json_out = json.dumps(payload, ensure_ascii=False, indent=4)
            st.download_button("💾 Üretim & İhracat Reçetesini İndir (.json)", data=json_out, file_name=f"{order_no}_recete.json", mime="application/json", use_container_width=True)

    with col_m2:
        st.subheader("📂 Kayıtlı Reçete Yükle")
        up_file = st.file_uploader("Daha önce indirilen .json reçetesini yükleyin", type=["json"])
        if up_file is not None:
            data = json.load(up_file)
            st.success(f"Proje: **{data.get('proje_kodu')}** | Durum: **{data.get('onay_durumu')}**")
            st.info(f"Yönetici Notu: {data.get('yonetici_notu')}")
            
            if st.button("📥 Reçeteyi Aktif Sipariş Yap", use_container_width=True):
                st.session_state.cart = data.get("sepet", [])
                st.toast("Müşteri takipli reçete başarıyla yüklendi!", icon="🚀")
                st.rerun()
