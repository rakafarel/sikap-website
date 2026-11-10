# ADR-002: MySQL/MariaDB sebagai basis data, diakses dengan PyMySQL

- Status: Diterima
- Tanggal: 2026-10-28

## Konteks

Data SIKAP sangat relasional: `users`, `dosen`, `pengajuan_pembimbing`, `logbook`, `pendaftaran_sidang`, `pengajuan_ta`, dan `logbook_ta` saling terhubung lewat foreign key (mis. mahasiswa ke dosen pembimbing, logbook ke mahasiswa). Aturan seperti kuota dosen dan status pengajuan butuh konsistensi data. Anggota tim sudah terbiasa dengan MySQL lewat XAMPP dan Laragon.

## Keputusan

Kami memakai **MySQL/MariaDB**, diakses dengan **PyMySQL** menggunakan query SQL berparameter (tanpa ORM).

- Skema lengkap ada di `db_sidang_kp.sql`, ditulis idempoten (`CREATE TABLE IF NOT EXISTS` dan pengecekan kolom sebelum `ALTER`), sehingga aman dijalankan berulang kali.
- Relasi dijaga dengan foreign key (`ON DELETE CASCADE` untuk data turunan) dan kolom `role` bertipe `ENUM`.
- Password disimpan sebagai hash (Werkzeug), bukan teks biasa.
- Konfigurasi koneksi dibaca dari `.env` (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`).

## Alternatif yang dipertimbangkan

- **PostgreSQL**: fitur lebih lengkap dan sangat andal. Ditolak karena tidak ada kebutuhan fitur khusus, tim lebih familiar dengan MySQL, dan tooling lokal tim (XAMPP/Laragon) sudah menyediakan MySQL.
- **SQLite**: tanpa server, paling mudah disiapkan. Ditolak karena akses tulis bersamaan terbatas dan kurang cocok untuk aplikasi multi-pengguna yang diakses banyak orang sekaligus.
- **MongoDB (NoSQL)**: skema fleksibel. Ditolak karena data bersifat relasional dan butuh konsistensi antar tabel.

## Konsekuensi

- Positif: relasi dan konsistensi data terjamin, tooling dan dokumentasi melimpah, mudah di-setup di lingkungan lokal maupun server.
- Negatif: query SQL ditulis manual di `app.py` sehingga rawan duplikasi dan kesalahan; migrasi skema masih lewat skrip SQL, belum memakai alat migrasi khusus. Setiap permintaan membuka koneksi baru (belum ada connection pooling).

## Kondisi untuk meninjau ulang

Keputusan ini ditinjau ulang bila jumlah pengguna bersamaan membuat koneksi jadi hambatan (perlu connection pooling atau database terkelola), bila skema berubah cukup sering sehingga butuh alat migrasi (mis. Alembic) dan ORM, atau bila hosting kampus ternyata hanya menyediakan database selain MySQL.
