# WMS Microcement Pro

Versi multi-file dari aplikasi WMS Microcement dengan pendaftaran akun,
persetujuan Developer, role sesuai jabatan, pencabutan sesi akun nonaktif,
penghapusan akun permanen, notifikasi Telegram, dan pemeriksaan keamanan otomatis.

## Struktur

- `app.py` — entry point dan routing halaman.
- `Code_Accounts.gs` — backend Apps Script v7.3 lengkap tanpa credential produksi.
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
5. Developer dapat menekan tombol `Staff`, `Admin`, atau `Tolak` langsung dari Telegram.
6. Role `Boss` dan `Developer` hanya dapat diberikan melalui menu `Kelola Akun`; menu ini juga tersedia untuk mengubah role atau menonaktifkan akun.

## Deploy ke Streamlit

1. Ganti seluruh kode Google Apps Script dengan `Code_Accounts.gs` dari root repository.
2. Pada `Project Settings` → `Script Properties`, isi `SPREADSHEET_ID`, `API_SHARED_KEY`, dan `AUTH_SIGNING_KEY`. Nilai key harus sama dengan Streamlit Secrets.
3. Tambahkan `DRIVE_FOLDER_ID`, `ACCOUNT_TELEGRAM_BOT_TOKEN`, `ACCOUNT_TELEGRAM_CHAT_ID`, dan `TELEGRAM_APPROVER_USER_ID` bila fitur terkait digunakan.
4. Jika notifikasi dikirim ke grup, `TELEGRAM_APPROVER_USER_ID` wajib berisi ID akun Telegram Developer yang berwenang.
5. Isi `LOCAL_ACCOUNT_ROLES_JSON` untuk mengikat akun dari Streamlit Secrets ke role backend, misalnya `{"andika":"Developer"}`.
6. Di Apps Script pilih `Deploy` → `Manage deployments` → ikon pensil → `New version` → `Deploy`.
7. Jalankan `setupTelegramApprovalWebhook` satu kali dan izinkan akses yang diminta.
8. Pastikan main file Streamlit adalah `app.py` dan tambahkan `SESSION_REVALIDATE_SECONDS = 60`.
9. Jangan mengubah `AUTH_SIGNING_KEY` tanpa rencana migrasi akun dinamis.
10. Jangan pernah mengunggah `.streamlit/secrets.toml` asli ke GitHub.

Gunakan `.streamlit/secrets.example.toml` sebagai contoh konfigurasi. Role Boss
dan Developer sengaja tidak tersedia pada formulir publik; Developer dapat
memberikannya sebagai role final dari menu `Kelola Akun`.

## Pemeriksaan sebelum deploy

```bash
python -m pip install -r requirements-dev.txt
python scripts/check_secrets.py
python -m compileall -q app.py wms tests scripts
cp Code_Accounts.gs /tmp/Code_Accounts.js && node --check /tmp/Code_Accounts.js
python -m ruff check app.py wms tests scripts
python -m pytest
```

Workflow `.github/workflows/quality.yml` menjalankan pemeriksaan yang sama pada
setiap push dan pull request.

## Perlindungan v8.4

- Login akun di Streamlit Secrets tidak lagi gagal hanya karena perbedaan huruf besar/kecil.
- Cache pembacaan database dipisahkan per username dan role agar data sesi tidak tertukar.
- Data server dengan stok negatif, minimum tidak valid, status asing, atau nama barang duplikat akan ditolak.
- Data riwayat/audit format lama tanpa baris header tidak lagi kehilangan catatan pertama.
- Teks pengguna dinetralkan saat ekspor Excel agar tidak dijalankan sebagai formula.
- Developer tidak dapat menonaktifkan, menurunkan role, atau menghapus akun yang sedang dipakai sendiri.
- Akun dinamis yang dinonaktifkan atau dihapus kehilangan sesi maksimal dalam 60 detik.
- Akun dapat dihapus permanen dengan konfirmasi username; audit transaksi tetap dipertahankan.
- Backend menolak penghapusan Developer aktif terakhir.
- Pemberian role Boss dan Developer melalui tombol Telegram dinonaktifkan; gunakan halaman Kelola Akun.
- CI menolak `secrets.toml`, token Telegram, private key, dan pola credential lain.
- Password akun dinamis dibatasi 8–128 karakter dan input jabatan divalidasi.

Untuk akun di Streamlit Secrets, `display_name` dapat ditambahkan secara opsional:

```toml
[USERS.developer]
display_name = "Andika"
role = "Developer"
password_hash = "pbkdf2_sha256$ITERATIONS$SALT_HEX$DIGEST_HEX"
```

Backend yang diperlukan adalah versi `7.3-accounts-delete`.

## Penghapusan akun permanen

Buka `Kelola Akun`, pilih akun, centang peringatan, lalu ketik username yang sama persis. Record akun beserta password verifier dihapus dari sheet `accounts`. Riwayat transaksi dan audit tidak ikut dihapus agar pertanggungjawaban stok tetap utuh. Akun yang sedang digunakan dan Developer aktif terakhir selalu ditolak oleh backend.

## Insiden secrets lama

Repository pernah memiliki riwayat perubahan `secrets.toml`. Menghapus file dari branch terbaru tidak membatalkan credential yang pernah terlihat. Ikuti seluruh langkah rotasi pada `SECURITY.md` sebelum aplikasi dipakai untuk data produksi.
