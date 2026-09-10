# Checklist Rilis dan Serah-Terima Mirai

Gunakan daftar ini untuk setiap instalasi pelanggan. Jangan menandai aplikasi
siap produksi sebelum seluruh bagian wajib selesai.

## 1. Identitas pelanggan

- [ ] Nama perusahaan dan penanggung jawab dicatat.
- [ ] Ruang lingkup fitur dan jumlah pengguna disepakati.
- [ ] Data contoh/dummy dihapus.
- [ ] Database pelanggan tidak bercampur dengan instalasi lain.

## 2. Infrastruktur

- [ ] Spreadsheet baru milik pelanggan tersedia.
- [ ] Folder Google Drive baru tersedia.
- [ ] Apps Script terbaru sudah ditempel dan di-deploy sebagai versi baru.
- [ ] URL Web App berakhiran `/exec` sudah digunakan.
- [ ] Repository deployment dibuat private.
- [ ] Streamlit Secrets dan Apps Script Properties sudah lengkap.
- [ ] Semua credential dibuat khusus untuk pelanggan ini.
- [ ] Backend `7.6-production` dipasang sebelum frontend `8.9-production`.
- [ ] Health backend melaporkan semua capability produksi aktif.

## 3. Keamanan

- [ ] Password Developer memakai PBKDF2.
- [ ] `REQUIRE_HMAC = true`.
- [ ] `WRITE_BLOCK_WHEN_OFFLINE = true`.
- [ ] `ALLOW_NO_LOGIN = false` dan `ALLOW_LEGACY_PASSWORDS = false`.
- [ ] `REQUIRE_SERVER_BACKUP_BEFORE_RESET = true`.
- [ ] `LOCAL_ACCOUNT_ROLES_JSON` sama dengan daftar akun lokal frontend.
- [ ] `TELEGRAM_APPROVER_USER_ID` sudah diisi dan approver lain ditolak.
- [ ] Seluruh akun lokal dan dinamis berstatus password `PBKDF2`.
- [ ] Token dan kunci lama sudah dirotasi.
- [ ] Tidak ada `secrets.toml`, token, atau password di GitHub.
- [ ] Hak akses setiap akun sudah diperiksa.
- [ ] Akun uji yang tidak diperlukan sudah dihapus.

## 4. Uji penerimaan

- [ ] Login dan logout berhasil pada komputer.
- [ ] Login dan logout berhasil pada ponsel.
- [ ] Barang masuk menambah stok tepat satu kali.
- [ ] Barang keluar mengurangi stok tepat satu kali.
- [ ] Retry dengan ID transaksi yang sama tidak mengubah stok dua kali.
- [ ] Stok tidak dapat menjadi negatif.
- [ ] Koreksi dan penyesuaian menghasilkan audit log.
- [ ] Riwayat dan laporan sesuai dengan transaksi.
- [ ] Backup dapat dibuat dan dibuka.
- [ ] Telegram mengirim pesan ke grup yang benar.
- [ ] Sistem menahan perubahan ketika backend tidak dapat diverifikasi.
- [ ] Refresh aplikasi memulihkan koneksi setelah backend aktif kembali.
- [ ] Perubahan dari perangkat kedua muncul melalui sinkronisasi/revision.
- [ ] Uji penerimaan dilakukan pada database staging, bukan stok produksi.
- [ ] File bukti Drive ikut dicadangkan dan satu restore drill berhasil.

## 5. Serah-terima

- [ ] Akun Developer/pemilik diserahkan melalui saluran aman.
- [ ] Panduan penggunaan singkat diberikan.
- [ ] Masa garansi perbaikan dan biaya dukungan disepakati.
- [ ] Tanggal backup pertama dijadwalkan.
- [ ] Pelanggan menyetujui hasil uji penerimaan.

## Status rilis

- **Demo:** boleh memakai data contoh dan belum dipakai untuk keputusan stok.
- **Pilot:** dipakai terbatas dengan pendampingan dan backup rutin.
- **Produksi:** seluruh checklist wajib selesai dan hasil uji telah disetujui.
