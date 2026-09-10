# Mirai

Mirai adalah aplikasi manajemen inventaris dan operasional gudang berbasis
Streamlit. Sistem menggunakan Google Sheets melalui Google Apps Script sebagai
database, Google Drive untuk bukti transaksi, serta Telegram untuk notifikasi
operasional.

## Fitur utama

- Dashboard stok dan peringatan barang kritis.
- Barang masuk, barang keluar, penyesuaian, dan koreksi transaksi.
- Master barang, batas minimum, serta saran restok.
- Role Developer, Boss, Admin, dan Staff.
- Pendaftaran, persetujuan, penonaktifan, dan penghapusan akun.
- Riwayat, laporan periodik, audit log, Excel/PDF, dan backup.
- Penghapusan audit lama khusus Developer dengan backup otomatis dan konfirmasi.
- Notifikasi Telegram dan persetujuan akun.
- Idempotensi transaksi, stale-stock guard, serta rollback otomatis bila penulisan
  stok/riwayat/audit terputus di tengah jalan.
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

1. Salin spreadsheet dan siapkan folder Google Drive baru.
2. Buat proyek Apps Script dan tempel seluruh isi `Code_Accounts.gs`.
3. Isi seluruh Script Properties wajib mengikuti `DEPLOYMENT.md`, termasuk
   `DRIVE_FOLDER_ID`, pemetaan akun lokal, dan pengaman approver Telegram.
4. Deploy Apps Script sebagai Web App dan simpan URL berakhiran `/exec`.
5. Deploy repository ke Streamlit Community Cloud.
6. Isi Streamlit Secrets berdasarkan `.streamlit/secrets.example.toml`.
7. Buat akun Developer pertama dengan password PBKDF2.
8. Jalankan `setupTelegramApprovalWebhook` bila persetujuan Telegram digunakan.
9. Uji login, koneksi database, transaksi masuk/keluar, backup, dan Telegram.
10. Serahkan akun dan panduan penggunaan kepada pelanggan.

Backend yang diperlukan adalah versi `7.6-production`.

Deploy backend **lebih dahulu**, baru frontend. Aplikasi memblokir mutasi bila versi
atau capability backend tidak cocok. Urutan, verifikasi, rollback, dan uji penerimaan
lengkap tersedia di `DEPLOYMENT.md`.

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
- Jangan menjalankan **Reset Database** pada database produksi untuk pengujian.
- Ikuti `SECURITY.md` sebelum menggunakan data produksi.

Repository ini pernah memiliki riwayat `secrets.toml`. Menghapus file dari
branch terbaru tidak membatalkan credential lama. Semua token dan kunci yang
pernah terekspos harus diganti sebelum penjualan atau pemasangan pelanggan.

## Pemeriksaan sebelum rilis

```bash
python -m pip install -r requirements-dev.txt
python scripts/check_secrets.py
python -m pip_audit --cache-dir /tmp/mirai-pip-audit -r requirements.txt
python -m compileall -q app.py wms tests scripts
cp Code_Accounts.gs /tmp/Code_Accounts.js
node --check /tmp/Code_Accounts.js
node scripts/test_backend_contract.js
python -m ruff check app.py wms tests scripts
python -m pytest
```

Daftar serah-terima pelanggan tersedia di `COMMERCIAL_CHECKLIST.md`.
