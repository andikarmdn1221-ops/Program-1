# Kebijakan Keamanan WMS

## Aturan credential

- Simpan credential produksi hanya di Streamlit Secrets dan Apps Script
  Script Properties.
- Jangan commit `.streamlit/secrets.toml`.
- File `.streamlit/secrets.example.toml` hanya berisi placeholder.
- Jangan menaruh bot token, API key, password, atau signing key dalam issue,
  screenshot, log, maupun source code.

CI menjalankan `python scripts/check_secrets.py` pada setiap push dan pull
request. Pemeriksaan ini mencegah kebocoran baru, tetapi tidak membersihkan
credential yang pernah masuk ke riwayat Git.

## Pemulihan credential yang pernah terekspos

Jika credential pernah masuk ke repository, menghapus file saja tidak cukup.

1. Cabut dan buat ulang token Telegram melalui BotFather.
2. Ganti `API_SHARED_KEY` dan `AUTH_SIGNING_KEY` jika keduanya pernah
   terlihat oleh pihak lain.
3. Perbarui nilai baru di Streamlit Secrets dan Apps Script Script Properties.
4. Deploy ulang Apps Script sebagai versi baru.
5. Jalankan `setupTelegramApprovalWebhook` kembali setelah token diganti.
6. Bersihkan riwayat Git dengan prosedur terkontrol atau pindahkan source ke
   repository baru yang bersih.
7. Jadikan repository private jika tidak perlu dipublikasikan.

Catatan: verifier legacy terikat pada `AUTH_SIGNING_KEY`, sedangkan verifier PBKDF2
8.9 tetap valid setelah signing key dirotasi. Bila akun legacy perlu dipertahankan,
rotasi `API_SHARED_KEY` lebih dahulu, migrasikan seluruh akun lewat satu login valid,
lalu rotasi `AUTH_SIGNING_KEY`. Detailnya ada di `DEPLOYMENT.md`. Akun legacy yang
tidak dapat dimigrasikan harus dibuat ulang melalui proses terkontrol.

## Konfigurasi yang wajib tetap aktif

- `REQUIRE_HMAC = true` pada frontend dan backend.
- `ALLOW_NO_LOGIN = false` dan `ALLOW_LEGACY_PASSWORDS = false`.
- `WRITE_BLOCK_WHEN_OFFLINE = true`.
- `REQUIRE_SERVER_BACKUP_BEFORE_RESET = true`.
- `API_SHARED_KEY` dan `AUTH_SIGNING_KEY` berbeda, acak, dan minimal 32 karakter.
- `LOCAL_ACCOUNT_ROLES_JSON` memuat setiap akun lokal dengan role yang sama seperti
  Streamlit Secrets.
- `TELEGRAM_APPROVER_USER_ID` menunjuk satu akun Telegram berwenang; approval dari
  pengguna grup lain selalu ditolak.
- `TELEGRAM_WEBHOOK_SECRET` acak minimal 32 karakter; token dan ID Telegram harus
  lolos validasi format sebelum capability approval dinyatakan aktif.

Backend menolak request ketika HMAC dinonaktifkan atau key inti lemah. Frontend
menolak semua mutasi ketika capability keamanan backend tidak lengkap.

## Data dan bukti transaksi

Backup spreadsheet menyimpan manifest URL bukti, bukan salinan file gambarnya.
Folder Drive bukti harus dicadangkan dengan kebijakan retensi terpisah dan diuji
restore secara berkala. Jangan mengubah stok/riwayat langsung di Google Sheets;
gunakan aplikasi agar stale-stock, idempotensi, dan audit tetap berlaku.

## Perlindungan repository yang direkomendasikan

Aktifkan branch protection untuk `main`:

- wajibkan pull request sebelum merge;
- wajibkan status check `test`;
- larang force push dan penghapusan branch;
- wajibkan branch selalu mutakhir sebelum merge.

## Pelaporan

Jangan membuka issue publik yang memuat credential atau data gudang. Laporkan
masalah keamanan langsung kepada pemilik aplikasi.
