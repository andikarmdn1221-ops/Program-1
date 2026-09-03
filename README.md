# Mirai

Mirai adalah aplikasi manajemen inventaris dan operasional gudang untuk usaha
kecil dan menengah. Aplikasi berbasis Streamlit ini menggunakan Google Sheets
melalui Google Apps Script sebagai database, Google Drive untuk bukti transaksi,
serta Telegram untuk notifikasi operasional.

Data bawaan adalah data demo gudang umum. Mirai tidak memuat nama barang,
riwayat, akun, atau identitas perusahaan tempat pengembangan awal dilakukan.

## Fitur utama

- Dashboard stok dan peringatan barang kritis.
- Barang masuk, barang keluar, penyesuaian, dan koreksi transaksi.
- Master barang, batas minimum, serta saran restok.
- Role Developer, Boss, Admin, dan Staff.
- Pendaftaran, persetujuan, penonaktifan, dan penghapusan akun.
- Riwayat, laporan periodik, audit log, Excel/PDF, dan backup.
- Penghapusan audit lama khusus Developer dengan backup otomatis dan konfirmasi.
- Notifikasi Telegram dan persetujuan akun.
- Tampilan ringkas untuk kegiatan harian dan tampilan lengkap untuk administrasi.
- UI responsif untuk komputer dan telepon seluler.

## Struktur proyek

- `app.py` — entry point, sidebar, dan routing.
- `Code_Accounts.gs` — backend Google Apps Script.
- `wms/config.py` — konfigurasi, role, permission, dan schema.
- `wms/auth.py` — login, session, dan keamanan akun.
- `wms/api.py` — komunikasi bertanda tangan dengan backend.
- `wms/data.py` — normalisasi, cache, health check, dan sinkronisasi.
- `wms/operations.py` — transaksi server-side.
- `wms/notifications.py` — Telegram dan log pengiriman.
- `wms/components.py` — dashboard, stok, riwayat, laporan, dan audit.
- `wms/pages/` — halaman operasional dan administrasi.
- `tests/` — pengujian otomatis.
- `.github/workflows/quality.yml` — pemeriksaan kualitas setiap perubahan.

## Instalasi untuk pelanggan baru

Setiap perusahaan harus menggunakan database, folder Drive, token Telegram,
kunci API, dan akun miliknya sendiri. Jangan memakai credential atau data dari
instalasi pelanggan lain.

1. Buat spreadsheet kosong dan folder Google Drive baru khusus pelanggan.
2. Buat proyek Apps Script dan tempel seluruh isi `Code_Accounts.gs`.
3. Isi Script Properties: `SPREADSHEET_ID`, `API_SHARED_KEY`,
   `AUTH_SIGNING_KEY`, dan konfigurasi opsional lainnya.
4. Deploy Apps Script sebagai Web App dan simpan URL berakhiran `/exec`.
5. Deploy repository ke Streamlit Community Cloud.
6. Isi Streamlit Secrets berdasarkan `.streamlit/secrets.example.toml`.
7. Buat akun Developer pertama dengan password PBKDF2.
8. Jalankan `setupTelegramApprovalWebhook` bila persetujuan Telegram digunakan.
9. Uji login, koneksi database, transaksi masuk/keluar, backup, dan Telegram.
10. Serahkan akun dan panduan penggunaan kepada pelanggan.

Backend yang diperlukan adalah versi `7.5-performance`.

Versi ini mengurangi pekerjaan Google Apps Script saat startup: health check tidak
membuka spreadsheet, validasi akun dan pembacaan data memakai satu koneksi, serta
pengecekan schema di-cache selama lima menit. Batas kegagalan koneksi frontend juga
dipangkas dari sekitar 62 detik menjadi maksimal sekitar 25 detik dengan konfigurasi
default. Cache data aman per pengguna dipakai selama dua menit dan tetap diperiksa
melalui revision backend, tanpa menambah jeda buatan pada respons normal.

## Alur akun baru

1. Pengguna mengisi formulir pada tab **Daftar Akun Baru**.
2. Akun disimpan dengan status `PENDING`; password asli tidak disimpan.
3. Developer menerima notifikasi tanpa informasi password.
4. Developer menyetujui Staff/Admin atau menolak permintaan.
5. Role Boss/Developer hanya diberikan dari menu **Kelola Akun**.
6. Akun nonaktif atau terhapus kehilangan sesi aktif saat validasi berikutnya.

## Keamanan produksi

- Simpan credential hanya di Streamlit Secrets dan Apps Script Script Properties.
- Jangan commit `.streamlit/secrets.toml`, token, password, atau kunci API.
- Jadikan repository pelanggan **private**.
- Gunakan credential baru untuk setiap instalasi.
- Aktifkan branch protection pada `main` dan wajibkan pemeriksaan `test`.
- Rotasi seluruh credential yang pernah muncul dalam repository atau screenshot.
- Jangan menonaktifkan HMAC dan pemblokiran perubahan ketika database offline.
- Ikuti `SECURITY.md` sebelum menggunakan data produksi.

Repository ini pernah memiliki riwayat `secrets.toml`. Menghapus file dari
branch terbaru tidak membatalkan credential lama. Semua token dan kunci yang
pernah terekspos harus diganti sebelum penjualan atau pemasangan pelanggan.

## Pemeriksaan sebelum rilis

```bash
python -m pip install -r requirements-dev.txt
python scripts/check_secrets.py
python -m compileall -q app.py wms tests scripts
cp Code_Accounts.gs /tmp/Code_Accounts.js
node --check /tmp/Code_Accounts.js
python -m ruff check app.py wms tests scripts
python -m pytest
```

Daftar serah-terima pelanggan tersedia di `COMMERCIAL_CHECKLIST.md`.
