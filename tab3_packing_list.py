import streamlit as st
import pandas as pd
from utils.storage import save_auto_recovery

def render_tab3():
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
            if st.button("🗑 Seçili Siparişi Sil", use_container_width=True):
                delete_index = item_labels.index(selected_item_to_delete)
                deleted_item = st.session_state.cart.pop(delete_index)
                save_auto_recovery(st.session_state.cart, st.session_state.draft_data)
                st.toast(f"'{deleted_item['Ürün Adı']}' siparişten silindi!", icon="🗑️")
                st.rerun()

        st.markdown("---")
        df_cart = pd.DataFrame(st.session_state.cart)

        edited_df = st.data_editor(
            df_cart, num_rows="dynamic",
            column_config={
                "Kasa Sayısı": st.column_config.NumberColumn("Kasa Sayısı", min_value=1, max_value=100, step=1, format="%d 📦")
            },
            disabled=[col for col in df_cart.columns if col != "Kasa Sayısı"],
            use_container_width=True, hide_index=True
        )

        updated_cart = []
        for index, row in edited_df.iterrows():
            crates = row["Kasa Sayısı"]
            tot_pcs = crates * row["1 Kasa Kapasite (Adet)"]
            tot_m2 = crates * row["1 Kasa Kapasite (m²)"]
            tot_boxes = crates * row["Kasadaki Kutu"]
            tot_wt = crates * row["1 Kasa Ağırlık (kg)"]

            row_copy = dict(row)
            row_copy["Toplam Adet"] = tot_pcs
            row_copy["Toplam m²"] = round(tot_m2, 2)
            row_copy["Toplam Kutu"] = tot_boxes
            row_copy["Toplam Ağırlık (kg)"] = round(tot_wt, 1)
            row_copy["Sipariş Miktarı"] = f"{tot_pcs:,} Adet" if row["Satış Birimi"] == "Adet (Pcs)" else f"{tot_m2:.2f} m²"
            updated_cart.append(row_copy)

        st.session_state.cart = updated_cart
        save_auto_recovery(st.session_state.cart, st.session_state.draft_data)
        df_updated = pd.DataFrame(updated_cart)

        st.subheader("📊 Genel Konteyner Özeti")
        c_p1, c_p2, c_p3, c_p4 = st.columns(4)
        c_p1.metric("TOPLAM KASA", f"{df_updated['Kasa Sayısı'].sum()} Kasa")
        c_p2.metric("TOPLAM METRAJ & ADET", f"{df_updated['Toplam Adet'].sum():,.0f} Pcs", f"{df_updated['Toplam m²'].sum():.2f} m²")
        c_p3.metric("TOPLAM BRÜT AĞIRLIK", f"{df_updated['Toplam Ağırlık (kg)'].sum():,.0f} kg")
        c_p4.metric("TOPLAM KUTU", f"{df_updated['Toplam Kutu'].sum():,.0f} Kutu")

        st.markdown("---")
        st.subheader("🏢 Müşteri / Firma Bazlı Ayrıştırılmış Packing List")
        for cust in df_updated["Müşteri"].unique():
            cust_df = df_updated[df_updated["Müşteri"] == cust]
            with st.expander(f"📌 Müşteri: **{cust}**", expanded=True):
                st.dataframe(cust_df[["PO / Sipariş No", "Ürün Adı", "Ebat (cm)", "Stok Durumu", "İmalat Süresi", "Kasa Sayısı", "Toplam Kutu", "Sipariş Miktarı", "Toplam Ağırlık (kg)"]], hide_index=True)