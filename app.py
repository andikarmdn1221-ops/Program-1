import    barang = st.selectbox("Pilih Barang", list(st.session_state.stok.keys()))
    jumlah = st.number_input("Jumlah Masuk", min_value=1, step=1)
    if st.button("Simpan Barang Masuk"):
        st.session_state.stok[barang] += jumlah
        st.session_state.riwayat.append(f"RESTOK: {barang} (+{jumlah} pcs)")
        st.success(f"Berhasil menambahkan {jumlah} pcs ke {barang}!")

elif menu == "📤 Pengiriman Barang Keluar":
    st.header("📤 Pengurangan Stok")
    barang = st.selectbox("Pilih Barang", list(st.session_state.stok.keys()))
    jumlah = st.number_input("Jumlah Keluar", min_value=1, step=1)
    if st.button("Proses Pengiriman"):
        if jumlah <= st.session_state.stok[barang]:
            st.session_state.stok[barang] -= jumlah
            st.session_state.riwayat.append(f"KELUAR: {barang} (-{jumlah} pcs)")
            st.success(f"Berhasil mengeluarkan {jumlah} pcs dari {barang}!")
        else:
            st.error("Stok tidak mencukupi!")

elif menu == "➕ Tambah Jenis Barang":
    st.header("➕ Tambah Jenis Barang Baru")
    nama_baru = st.text_input("Nama Barang Baru")
    stok_awal = st.number_input("Stok Awal", min_value=0, step=1)
    if st.button("Daftarkan Barang"):
        if nama_baru in st.session_state.stok:
            st.warning("Barang sudah ada di dalam sistem!")
        elif nama_baru.strip() != "":
            st.session_state.stok[nama_baru] = stok_awal
            st.session_state.riwayat.append(f"TAMBAH: {nama_baru} ({stok_awal} pcs)")
            st.success(f"{nama_baru} berhasil didaftarkan!")

elif menu == "📜 Riwayat Transaksi":
    st.header("📜 Catatan Riwayat Transaksi")
    if not st.session_state.riwayat:
        st.info("Belum ada riwayat transaksi.")
    else:
        for log in reversed(st.session_state.riwayat):
            st.write(f"- {log}")
  
