import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def render_tab4():
    st.header("🚢 İhracat, Liman Bazlı Min/Max Tonaj Limitleri & 3D Visualizer")
    
    col_ex1, col_ex2 = st.columns(2)
    with col_ex1:
        container_type = st.selectbox("Konteyner Tipi", [
            "20'lik Standart (20' DC) - Max Vol: 33.2 m³",
            "40'lık Standart (40' DC) - Max Vol: 67.7 m³",
            "40'lık High Cube (40' HC) - Max Vol: 76.2 m³"
        ])
    with col_ex2:
        port_preset = st.selectbox("ABD Varış Limanı / Tonaj Şablonu", [
            "Savannah 20' & 40' (Min: 24,040 kg / Max: 27,215 kg)",
            "Houston 20' & 40' (Min: 24,040 kg / Max: 27,215 kg)",
            "LA/Long Beach - 20' & 40' MORENO (Min: 18,143 kg / Max: 20,865 kg)",
            "Baltimore - 20' (Min: 24,040 kg / Max: 27,216 kg)",
            "LA Transload - 20' & 40' CARSON (Min: 20,865 kg / Max: 26,762 kg)"
        ])

    if "Savannah" in port_preset or "Houston" in port_preset or "Baltimore - 20'" in port_preset:
        min_allowed_kg, max_allowed_kg = 24040, 27215
    elif "MORENO" in port_preset:
        min_allowed_kg, max_allowed_kg = 18143, 20865
    else:
        min_allowed_kg, max_allowed_kg = 20865, 26762

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
        m1.metric("Ağırlık Limiti Aralığı", f"{min_allowed_kg:,.0f} - {max_allowed_kg:,.0f} kg")
        m2.metric("Mevcut Konteyner Brüt Ağırlığı", f"{total_weight_kg:,.0f} kg")
        
        if total_weight_kg < min_allowed_kg:
            status_text = "🟡 EKSİK YÜKLEME!"
            delta_msg = f"{min_allowed_kg - total_weight_kg:,.0f} kg eksik"
        elif total_weight_kg > max_allowed_kg:
            status_text = "🔴 AĞIR TONAJ UYARISI!"
            delta_msg = f"{total_weight_kg - max_allowed_kg:,.0f} kg fazla"
        else:
            status_text = "🟢 UYGUN ✅"
            delta_msg = "İdeal tonaj aralığında"
            
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
        st.plotly_chart(fig, use_container_width=True)