import streamlit as st
import utils.storage as storage

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Emre Doğaltaş Portalı",
    page_icon="🗿",
    layout="wide"
)

# Klasörleri doğrula
storage.ensure_storage_dirs()

st.title("🗿 Emre Doğaltaş Entegre Yönetim Portalı")
st.caption("Üretim, Dizim, İhracat ve Konteyner Operasyon Paneli")
st.markdown("---")

# Otomatik Kurtarma Kontrolü
recovery = storage.load_auto_recovery()
if recovery:
    col_rec1, col_rec2 = st.columns([4, 1])
    with col_rec1:
        st.warning("⚠️ Tamamlanmamış bir oturum verisi bulundu. Kaldığınız yerden devam etmek ister misiniz?")
    with col_rec2:
        if st.button("Kurtarma Verisini Sil"):
            storage.clear_auto_recovery()
            st.experimental_rerun()

st.success("Sistem hazır. Lütfen sol menüden veya sekmelerden işlem yapmak istediğiniz modülü seçin.")
