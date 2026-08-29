# WMS Microcement Pro

Versi multi-file dari aplikasi WMS Microcement. Tampilan, role, transaksi,
Telegram, backup, laporan, dan koneksi Google Apps Script tetap sama.

## Struktur

- `app.py` — entry point dan routing halaman.
- `wms/config.py` — konfigurasi, secrets, role, dan schema.
- `wms/styles.py` — CSS desktop dan mobile.
- `wms/auth.py` — login, session, role, dan permission.
- `wms/api.py` — komunikasi aman dengan Code.gs.
- `wms/notifications.py` — Telegram dan log pengiriman.
- `wms/data.py` — normalisasi, cache, health check, dan sinkronisasi.
- `wms/operations.py` — transaksi dan perubahan data server.
- `wms/exports.py` — Excel, PDF, dan backup.
- `wms/components.py` — dashboard, stok, riwayat, laporan, dan audit.
- `wms/pages/` — halaman master, transaksi, backup, notifikasi, pengaturan, dan tentang.

## Deploy ke Streamlit

1. Ekstrak ZIP, lalu unggah seluruh isi folder ini ke root repository GitHub; jangan hanya `app.py`.
2. Pastikan main file pada Streamlit adalah `app.py`.
3. Jika Streamlit Secrets Anda sudah berfungsi, tidak perlu mengubahnya. Untuk instalasi baru, gunakan `.streamlit/secrets.example.toml` sebagai contoh.
4. Gunakan nilai API dan HMAC yang sama dengan Script Properties pada Code.gs.
5. Jangan mengunggah file `.streamlit/secrets.toml` asli ke GitHub.

Backend Code.gs versi `7.1-production` tidak perlu diubah untuk refactor ini.
