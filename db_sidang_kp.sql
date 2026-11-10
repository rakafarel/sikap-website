-- =====================================================================
-- SIKAP - skema database lengkap (dibuat dari query di app.py)
-- Untuk MySQL/MariaDB (XAMPP). Aman dijalankan berulang kali:
-- tabel yang sudah ada tidak dihapus, hanya kolom yang kurang ditambah.
-- =====================================================================

-- Pastikan DB_NAME di file .env = db_sidang_kp
CREATE DATABASE IF NOT EXISTS db_sidang_kp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE db_sidang_kp;

-- ---------------------------------------------------------------------
-- 1. users (login, register, semua role)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  username  VARCHAR(50)  NOT NULL UNIQUE,          -- NPM / NIDN / username
  password  VARCHAR(255) NOT NULL,                 -- hash dari werkzeug
  nama      VARCHAR(150) NOT NULL,
  role      ENUM('mahasiswa','dosen','admin','kaprodi') NOT NULL
);

-- ---------------------------------------------------------------------
-- 2. dosen (kuota bimbingan KP)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dosen (
  id_dosen       INT PRIMARY KEY,                  -- = users.id
  max_kuota      INT NOT NULL DEFAULT 2,
  kuota_terpakai INT NOT NULL DEFAULT 0,
  FOREIGN KEY (id_dosen) REFERENCES users(id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- 3. pengajuan_pembimbing (pengajuan dosen pembimbing KP, 2 pilihan)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pengajuan_pembimbing (
  id_pengajuan  INT AUTO_INCREMENT PRIMARY KEY,
  id_mahasiswa  INT NOT NULL,
  id_dosen_p1   INT NOT NULL,
  id_dosen_p2   INT NOT NULL,
  judul_kp      VARCHAR(255) NOT NULL,
  topik_kp      VARCHAR(255) NOT NULL,
  file_proposal VARCHAR(255) NULL,
  status_p1     VARCHAR(20) NOT NULL DEFAULT 'pending',   -- pending/accepted/rejected
  status_p2     VARCHAR(20) NOT NULL DEFAULT 'in_queue',  -- in_queue/pending/accepted/rejected
  status_final  VARCHAR(20) NOT NULL DEFAULT 'waiting',   -- waiting/accepted/unassigned
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_mahasiswa) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (id_dosen_p1)  REFERENCES users(id),
  FOREIGN KEY (id_dosen_p2)  REFERENCES users(id)
);

-- ---------------------------------------------------------------------
-- 4. logbook (bimbingan KP)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS logbook (
  id_logbook        INT AUTO_INCREMENT PRIMARY KEY,
  id_mahasiswa      INT NOT NULL,
  tanggal_bimbingan DATE NOT NULL,
  topik_pembahasan  TEXT NOT NULL,
  file_progress     VARCHAR(255) NULL,
  status_acc        VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending/approved/rejected
  created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_mahasiswa) REFERENCES users(id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- 5. pendaftaran_sidang (sidang KP)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pendaftaran_sidang (
  id_sidang          INT AUTO_INCREMENT PRIMARY KEY,
  id_mahasiswa       INT NOT NULL,
  file_laporan_final VARCHAR(255) NULL,
  file_transkrip     VARCHAR(255) NULL,
  file_krs           VARCHAR(255) NULL,
  status_verifikasi  VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending/verified/rejected
  catatan_admin      TEXT NULL,
  tanggal_sidang     DATE NULL,
  waktu_sidang       TIME NULL,
  ruangan            VARCHAR(100) NULL,
  id_penguji         INT NULL,
  nilai_akhir        VARCHAR(10) NULL,      -- VARCHAR supaya bisa angka (85) atau huruf (A)
  catatan_revisi     TEXT NULL,
  created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_mahasiswa) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (id_penguji)   REFERENCES users(id) ON DELETE SET NULL
);

-- ---------------------------------------------------------------------
-- 6. pengajuan_ta (pengajuan dosen pembimbing TA, 3 pilihan berurutan)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pengajuan_ta (
  id_pengajuan     INT AUTO_INCREMENT PRIMARY KEY,
  id_mahasiswa     INT NOT NULL,
  id_dosen_p1      INT NOT NULL,
  id_dosen_p2      INT NOT NULL,
  id_dosen_p3      INT NOT NULL,
  judul_ta         VARCHAR(255) NOT NULL,
  topik_ta         VARCHAR(255) NOT NULL,
  file_proposal_ta VARCHAR(255) NULL,
  pilihan_aktif    TINYINT NOT NULL DEFAULT 1,               -- 1, 2, atau 3
  status_p1        VARCHAR(20) NOT NULL DEFAULT 'pending',
  status_p2        VARCHAR(20) NOT NULL DEFAULT 'in_queue',
  status_p3        VARCHAR(20) NOT NULL DEFAULT 'in_queue',
  status_final     VARCHAR(20) NOT NULL DEFAULT 'pending',   -- pending/accepted/rejected
  created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_mahasiswa) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (id_dosen_p1)  REFERENCES users(id),
  FOREIGN KEY (id_dosen_p2)  REFERENCES users(id),
  FOREIGN KEY (id_dosen_p3)  REFERENCES users(id)
);

-- ---------------------------------------------------------------------
-- 7. logbook_ta (bimbingan TA)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS logbook_ta (
  id_logbook        INT AUTO_INCREMENT PRIMARY KEY,
  id_mahasiswa      INT NOT NULL,
  tanggal_bimbingan DATE NOT NULL,
  topik_pembahasan  TEXT NOT NULL,
  file_progress     VARCHAR(255) NULL,
  status_acc        VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_mahasiswa) REFERENCES users(id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- 8. Untuk database yang SUDAH ADA tapi strukturnya lama:
--    tambahkan kolom yang kurang. Tiap kolom dicek dulu, jadi aman
--    dijalankan berulang kali (MySQL maupun MariaDB).
-- ---------------------------------------------------------------------
SET @s = (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE pengajuan_ta ADD COLUMN id_dosen_p3 INT NULL AFTER id_dosen_p2',
  'SELECT 1')
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'pengajuan_ta' AND COLUMN_NAME = 'id_dosen_p3');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @s = (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE pengajuan_ta ADD COLUMN status_p2 VARCHAR(20) NOT NULL DEFAULT ''in_queue''',
  'SELECT 1')
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'pengajuan_ta' AND COLUMN_NAME = 'status_p2');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @s = (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE pengajuan_ta ADD COLUMN status_p3 VARCHAR(20) NOT NULL DEFAULT ''in_queue''',
  'SELECT 1')
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'pengajuan_ta' AND COLUMN_NAME = 'status_p3');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @s = (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE pengajuan_ta ADD COLUMN pilihan_aktif TINYINT NOT NULL DEFAULT 1',
  'SELECT 1')
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'pengajuan_ta' AND COLUMN_NAME = 'pilihan_aktif');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @s = (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE logbook ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP',
  'SELECT 1')
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'logbook' AND COLUMN_NAME = 'created_at');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @s = (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE pendaftaran_sidang ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP',
  'SELECT 1')
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'pendaftaran_sidang' AND COLUMN_NAME = 'created_at');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

-- ---------------------------------------------------------------------
-- 9. Akun Admin dan Kaprodi
--    Daftar dulu lewat halaman /register (pilih role apa saja),
--    lalu ubah rolenya di sini. Ganti 'username_kamu'.
-- ---------------------------------------------------------------------
-- UPDATE users SET role = 'admin'   WHERE username = 'username_admin';
-- UPDATE users SET role = 'kaprodi' WHERE username = 'username_kaprodi';
-- DELETE FROM dosen WHERE id_dosen IN (SELECT id FROM users WHERE role IN ('admin','kaprodi'));
