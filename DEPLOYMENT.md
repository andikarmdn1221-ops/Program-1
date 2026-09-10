# Runbook Deployment Produksi Mirai 8.9

Dokumen ini adalah urutan rilis wajib. Menyalin kode ke GitHub tidak memperbarui
Google Apps Script secara otomatis.

## 1. Siapkan staging dan backup

1. Gunakan spreadsheet, folder Drive, bot Telegram, dan deployment Apps Script
   staging yang terpisah dari produksi.
2. Buat backup server dari versi aktif dan pastikan file dapat dibuka.
3. Cadangkan folder Drive bukti secara terpisah. Backup spreadsheet hanya menyimpan
   URL/manifest bukti.
4. Jangan memakai menu **Reset Database** pada database produksi untuk pengujian.

## 2. Isi Apps Script Properties

Semua nilai berikut wajib pada production:

| Property | Ketentuan |
|---|---|
| `SPREADSHEET_ID` | Spreadsheet milik instalasi ini |
| `DRIVE_FOLDER_ID` | Folder khusus backup dan bukti, bukan Drive root |
| `API_SHARED_KEY` | Acak, minimal 32 karakter |
| `AUTH_SIGNING_KEY` | Acak, minimal 32 karakter dan berbeda dari API key |
| `REQUIRE_HMAC` | `true` |
| `REQUIRE_SERVER_BACKUP_BEFORE_RESET` | `true` |
| `LOCAL_ACCOUNT_ROLES_JSON` | JSON username lokal ke role, mis. `{"developer":"Developer"}` |
| `ACCOUNT_TELEGRAM_BOT_TOKEN` | Token bot approval akun dari BotFather |
| `ACCOUNT_TELEGRAM_CHAT_ID` | ID chat numerik tujuan approval akun |
| `TELEGRAM_APPROVER_USER_ID` | User ID Telegram numerik approver tunggal |
| `TELEGRAM_WEBHOOK_SECRET` | Acak minimal 32 karakter; dibuat otomatis oleh setup webhook |

Buat key baru dengan password manager atau generator kriptografis. Jangan menyalin
key dari instalasi pelanggan lain dan jangan menaruh nilainya di source, issue, atau
log. Jika credential lama pernah terekspos dan masih ada akun dinamis legacy, ikuti
rotasi dua tahap pada bagian berikut; mengganti kedua key sekaligus akan memutus
migrasi akun tersebut.

## 3. Deploy backend lebih dahulu

1. Tempel seluruh `Code_Accounts.gs` ke proyek Apps Script.
2. Atur timezone proyek Apps Script ke `Asia/Jakarta`.
3. Buat deployment Web App versi baru dan pertahankan URL `/exec` yang benar.
4. Jalankan `setupTelegramApprovalWebhook()` dari editor Apps Script. Fungsi ini
   membuat webhook secret bila belum ada.
5. Pastikan execution log tidak menunjukkan error property/schema.

Backend 7.6 tetap menerima verifier akun dinamis lama selama jendela rollout.
Frontend 8.9 akan mengubahnya ke PBKDF2 secara atomik saat login yang valid.

### Rotasi dua tahap untuk instalasi dengan akun legacy

1. Jadwalkan maintenance window dan buat backup terverifikasi.
2. Deploy backend 7.6 dan frontend 8.9 dengan `API_SHARED_KEY` **baru**, tetapi
   pertahankan `AUTH_SIGNING_KEY` lama sementara. Pasangan credential lama tidak
   lagi dapat mengakses backend karena API key sudah berubah.
3. Minta seluruh akun dinamis aktif login sekali dan pastikan `active_legacy = 0`.
4. Rotasi `AUTH_SIGNING_KEY` di Apps Script dan Streamlit Secrets dalam satu window,
   lalu restart frontend. Verifier PBKDF2 8.9 tetap valid setelah rotasi signing key.
5. Akun legacy yang tidak sempat login harus dibuat ulang melalui proses terkontrol;
   jangan mempertahankan signing key lama tanpa batas waktu.

Jika tidak ada akun legacy yang perlu dipertahankan, rotasi kedua key sekaligus.

## 4. Deploy frontend

1. Salin `.streamlit/secrets.example.toml` ke pengaturan Secrets deployment.
2. Gunakan URL backend baru, key yang sama dengan Apps Script, dan seluruh flag aman.
3. Deploy commit yang memakai app `8.9-production`.
4. Login sebagai akun lokal Developer. Sidebar harus menunjukkan database terhubung,
   backend cocok, dan Telegram berhasil ketika tombol tes dijalankan.

Jika backend/capability tidak cocok, frontend sengaja menahan seluruh mutasi. Jangan
mematikan pengaman untuk melewatinya.

## 5. Uji penerimaan di staging

1. Uji login/logout untuk Developer, Boss, Admin, dan Staff.
2. Uji satu barang masuk dan keluar; ulangi payload dengan ID transaksi yang sama dan
   pastikan stok hanya berubah sekali.
3. Uji stale-stock memakai dua perangkat: simpan dari perangkat pertama, lalu coba
   simpan snapshot lama dari perangkat kedua. Request kedua harus ditolak.
4. Uji stok negatif, koreksi, void, penyesuaian, bukti JPEG valid/tidak valid, dan
   proteksi input berawalan `=`, `+`, `-`, atau `@`.
5. Matikan backend staging sementara. Data terakhir boleh terlihat sebagai snapshot,
   tetapi semua perubahan harus ditahan.
6. Uji Telegram operasional dan approval; user Telegram selain approver harus ditolak.
7. Buat backup, buka hasilnya, lalu lakukan restore drill ke spreadsheet staging lain.
8. Buka perangkat kedua dan pastikan perubahan muncul melalui revision/auto-sync.

Catat hasil dan penanggung jawab di `COMMERCIAL_CHECKLIST.md`.

## 6. Selesaikan migrasi akun

Setiap akun dinamis aktif lama harus login sekali melalui frontend 8.9. Developer lalu
membuka **Kelola Akun** dan memastikan kolom Password seluruh akun menunjukkan
`PBKDF2`. Hapus permintaan/rejected account lama yang tidak diperlukan. Jangan rollback
frontend ke versi sebelum 8.9 setelah akun mulai dimigrasikan, karena frontend lama
tidak memahami verifier PBKDF2 dinamis.

## 7. Batas operasi dan pemulihan

- Frontend memberi peringatan ketika riwayat atau audit mencapai 5.000 baris.
- Rollback mutasi dibatasi 150.000 sel gabungan agar Apps Script tidak kehabisan waktu.
  Buat backup lalu arsipkan riwayat/audit sebelum melewati batas tersebut.
- Bila hasil transaksi tidak pasti akibat timeout, cari ID transaksi di Riwayat/Audit.
  Jangan membuat transaksi baru sebelum status ID lama jelas.
- Untuk rollback rilis, rollback frontend terlebih dahulu hanya bila belum ada migrasi
  PBKDF2 dinamis. Backend 7.6 dapat tetap aktif. Jangan menurunkan backend saat frontend
  8.9 masih melayani pengguna.

## 8. Kontrol GitHub sebelum go-live

- Repository pelanggan private.
- Branch `main` dilindungi: pull request wajib, check `test` wajib, force-push dan
  penghapusan branch dilarang.
- Semua credential yang pernah muncul di riwayat telah dirotasi.
- CI secret scan, compile, Apps Script syntax/contract, lint, pytest, dan smoke test
  seluruhnya hijau.
