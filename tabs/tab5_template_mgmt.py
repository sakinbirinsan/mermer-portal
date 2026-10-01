import streamlit as st
import json
import os
from utils.storage import TEMPLATES_DIR, save_auto_recovery

def render_tab5():
    st.header("💾 Sunucu Taslak Kayıt & Yükleme Yönetimi")
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        st.subheader("📝 Taslağı Sunucuya Kaydet")
        order_no = st.text_input("Konteyner / Proje Dosya Adı", value="KONTEYNER-2026-01")
        approval_status = st.selectbox("Yönetici Onay Durumu", ["Taslak / İncelemede", "Dizim Onayladı", "YÖNETİM ONAYLADI"])
        exec_notes = st.text_area("Fabrika & Paketleme Özel Talimatları", value="Kasalar fumigasyonlu ve takozlu hazırlanacak.")

        if st.session_state.cart:
            if st.button("☁️ Taslağı Portala Kaydet", use_container_width=True):
                payload = {
                    "proje_kodu": order_no, "onay_durumu": approval_status,
                    "yonetici_notu": exec_notes, "sepet": st.session_state.cart
                }
                save_path = os.path.join(TEMPLATES_DIR, f"{order_no}.json")
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=4)
                st.success(f"✅ '{order_no}' sunucuya kaydedildi!")
                st.rerun()

    with col_m2:
        st.subheader("📂 Dışarıdan (.json) Yükle")
        up_file = st.file_uploader("JSON Dosyası Seçin", type=["json"])
        if up_file:
            data = json.load(up_file)
            if st.button("📥 Ekrana Aktar", use_container_width=True):
                st.session_state.cart = data.get("sepet", [])
                save_auto_recovery(st.session_state.cart, st.session_state.draft_data)
                st.toast("Dosya yüklendi!", icon="🚀")
                st.rerun()
