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

Catatan: mengganti `AUTH_SIGNING_KEY` membuat verifier akun dinamis lama tidak
lagi cocok. Setelah rotasi, buat ulang akun dinamis atau lakukan migrasi verifier
melalui proses reset password yang terkontrol.

## Perlindungan repository yang direkomendasikan

Aktifkan branch protection untuk `main`:

- wajibkan pull request sebelum merge;
- wajibkan status check `test`;
- larang force push dan penghapusan branch;
- wajibkan branch selalu mutakhir sebelum merge.

## Pelaporan

Jangan membuka issue publik yang memuat credential atau data gudang. Laporkan
masalah keamanan langsung kepada pemilik aplikasi.
