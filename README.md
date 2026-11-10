# SIKAP (Sistem Informasi Kerja Praktek)

Aplikasi web untuk mengelola Kerja Praktek (KP) dan Tugas Akhir (TA). Pengajuan pembimbing, logbook, dan pendaftaran sidang yang tadinya manual dipindahkan ke satu sistem.

- **Mahasiswa**: ajukan pembimbing KP dan TA, isi logbook, daftar sidang KP, lihat jadwal dan nilai.
- **Dosen**: terima/tolak pengajuan bimbingan (sesuai kuota), ACC logbook, beri nilai sidang.
- **Admin**: verifikasi berkas sidang dan atur penguji serta jadwal, atur kuota dosen, kelola akun.
- **Kaprodi**: lihat ringkasan jumlah mahasiswa, kuota dosen, dan rekap nilai.

## Tech Stack

Python, FastAPI, Uvicorn, MySQL (PyMySQL), Jinja2, Bootstrap 5.

## Project Structure

```
sikap-website/
├── src/
│   ├── app.py            # aplikasi utama (semua route)
│   ├── buat_admin.py     # script membuat akun admin pertama
│   ├── templates/        # halaman HTML (Jinja2)
│   ├── static/           # CSS, JS, gambar
│   └── uploads/          # berkas PDF (proposal, logbook, sidang), dibuat otomatis
├── db_sidang_kp.sql      # skema database
├── requirements.txt
└── .env                  # konfigurasi lokal (tidak ikut di-commit)
```

## Prerequisites

- Python 3.10 atau lebih baru
- MySQL atau MariaDB, bebas lewat apa saja: [XAMPP](https://www.apachefriends.org/), [Laragon](https://laragon.org/), MySQL Server standalone, atau Docker
- Git

## Getting Started

### 1. Clone repository

```bash
git clone <url-repository>
cd sikap-website
```

### 2. Buat virtual environment dan install dependensi

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Siapkan database

1. Jalankan server **MySQL/MariaDB** kamu (Start di XAMPP/Laragon, atau service MySQL biasa).
2. Import file `db_sidang_kp.sql` dengan salah satu cara berikut:
   - **phpMyAdmin / HeidiSQL / DBeaver**: buka menu Import atau Run SQL File, lalu pilih `db_sidang_kp.sql`.
   - **Terminal**:
     ```bash
     mysql -u root -p < db_sidang_kp.sql
     ```
     Kalau perintah `mysql` tidak dikenali, pakai path lengkapnya, misalnya `C:\xampp\mysql\bin\mysql.exe` (XAMPP) atau lewat menu Terminal di Laragon.

File SQL otomatis membuat database `db_sidang_kp` beserta semua tabelnya, dan aman dijalankan berulang kali.

### 4. Buat file `.env`

Buat file `.env` di folder root proyek (sejajar dengan `requirements.txt`):

```env
SECRET_KEY=isi-dengan-string-acak
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=db_sidang_kp
```

Sesuaikan `DB_USER` dan `DB_PASSWORD` dengan MySQL kamu (default XAMPP dan Laragon: user `root`, password kosong).

### 5. Buat akun admin pertama

```bash
python src/buat_admin.py
```

Akun yang dibuat: username `admin`, password `admin123`. Ganti password ini setelah login pertama, atau ubah nilainya langsung di `src/buat_admin.py` sebelum dijalankan.

### 6. Jalankan aplikasi

Masuk ke folder `src`, lalu jalankan:

```bash
cd src
python app.py
```

Buka **http://127.0.0.1:8000** di browser.

> Aplikasi harus dijalankan dari dalam folder `src`. Kalau dijalankan dari folder root, bisa muncul error `Directory 'static' does not exist`.

## Team

Raka Farrel Naufalsyah, Rafka Zurfarel Alkahfi, Nurhamid, Fikri Ardiansyah