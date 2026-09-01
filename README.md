# WMS Microcement Pro

Versi multi-file dari aplikasi WMS Microcement dengan pendaftaran akun,
persetujuan Developer, role sesuai jabatan, pembatasan login lintas sesi,
notifikasi Telegram, dan pemeriksaan otomatis melalui GitHub Actions.

## Struktur

- `app.py` — entry point dan routing halaman.
- `wms/config.py` — konfigurasi, secrets, role, dan schema.
- `wms/styles.py` — CSS desktop dan mobile.
- `wms/auth.py` — login, session, role, dan permission.
- `wms/accounts.py` — pendaftaran dan autentikasi akun dinamis.
- `wms/api.py` — komunikasi aman dengan Code.gs.
- `wms/notifications.py` — Telegram dan log pengiriman.
- `wms/data.py` — normalisasi, cache, health check, dan sinkronisasi.
- `wms/operations.py` — transaksi dan perubahan data server.
- `wms/exports.py` — Excel, PDF, dan backup.
- `wms/components.py` — dashboard, stok, riwayat, laporan, dan audit.
- `wms/pages/accounts.py` — persetujuan, perubahan role, dan status akun.
- `wms/pages/` — halaman master, transaksi, backup, notifikasi, pengaturan, dan tentang.

## Alur Akun Baru

1. Pengguna membuka tab `Daftar Akun Baru` pada halaman login.
2. Pengguna mengisi nama, username, jabatan, role Staff/Admin yang diminta, dan password.
3. Akun disimpan dengan status `PENDING`; password asli tidak disimpan.
4. Developer menerima notifikasi Telegram tanpa informasi password.
5. Developer dapat menekan tombol `Staff`, `Admin`, `Boss`, `Developer`, atau `Tolak` langsung dari Telegram.
6. Menu `Kelola Akun` tetap tersedia untuk mengubah role atau menonaktifkan akun setelahnya.

## Deploy ke Streamlit

1. Ganti seluruh kode Google Apps Script dengan file `Code_Accounts.gs` yang diberikan terpisah.
2. Pada `Project Settings` → `Script Properties`, tambahkan `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID` dengan nilai yang sama seperti Streamlit Secrets.
3. Jika notifikasi dikirim ke grup, tambahkan `TELEGRAM_APPROVER_USER_ID` berisi ID akun Telegram Anda. Untuk chat pribadi, ini tidak wajib.
4. Di Apps Script pilih `Deploy` → `Manage deployments` → ikon pensil → `New version` → `Deploy`.
5. Jalankan fungsi `setupTelegramApprovalWebhook` satu kali dari editor Apps Script dan izinkan akses yang diminta.
6. Ekstrak ZIP aplikasi, lalu unggah seluruh isinya ke root repository GitHub.
7. Pastikan main file pada Streamlit adalah `app.py`.
8. Streamlit Secrets lama tetap digunakan; tidak ada secret Streamlit baru yang wajib ditambahkan.
9. Jangan mengubah `AUTH_SIGNING_KEY` setelah akun dinamis dibuat, karena nilai ini juga melindungi password verifier.
10. Jangan mengunggah `.streamlit/secrets.toml` asli ke GitHub.

Gunakan `.streamlit/secrets.example.toml` sebagai contoh konfigurasi. Role Boss
dan Developer sengaja tidak tersedia pada formulir publik; Developer dapat
memberikannya sebagai role final dari menu `Kelola Akun`.

## Pemeriksaan sebelum deploy

```bash
python -m pip install -r requirements-dev.txt
python -m compileall -q app.py wms tests
python -m pytest
```

Workflow `.github/workflows/quality.yml` menjalankan pemeriksaan yang sama pada
setiap push dan pull request.

Backend yang diperlukan adalah versi `7.2-accounts`.
