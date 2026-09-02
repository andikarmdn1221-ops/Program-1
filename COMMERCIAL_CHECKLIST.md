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

## 3. Keamanan

- [ ] Password Developer memakai PBKDF2.
- [ ] `REQUIRE_HMAC = true`.
- [ ] `WRITE_BLOCK_WHEN_OFFLINE = true`.
- [ ] Token dan kunci lama sudah dirotasi.
- [ ] Tidak ada `secrets.toml`, token, atau password di GitHub.
- [ ] Hak akses setiap akun sudah diperiksa.
- [ ] Akun uji yang tidak diperlukan sudah dihapus.

## 4. Uji penerimaan

- [ ] Login dan logout berhasil pada komputer.
- [ ] Login dan logout berhasil pada ponsel.
- [ ] Barang masuk menambah stok tepat satu kali.
- [ ] Barang keluar mengurangi stok tepat satu kali.
- [ ] Stok tidak dapat menjadi negatif.
- [ ] Koreksi dan penyesuaian menghasilkan audit log.
- [ ] Riwayat dan laporan sesuai dengan transaksi.
- [ ] Backup dapat dibuat dan dibuka.
- [ ] Telegram mengirim pesan ke grup yang benar.
- [ ] Sistem menahan perubahan ketika backend tidak dapat diverifikasi.
- [ ] Refresh aplikasi memulihkan koneksi setelah backend aktif kembali.

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
