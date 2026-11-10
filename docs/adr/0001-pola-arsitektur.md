# ADR-001: Pola arsitektur monolith dengan server-side rendering

- Status: Diterima
- Tanggal: 2026-10-28

## Konteks

SIKAP dipakai empat peran (mahasiswa, dosen, admin, kaprodi) di satu program studi. Skalanya kecil: pengguna adalah mahasiswa dan dosen Prodi Informatika, dengan alur yang sudah jelas (pengajuan pembimbing, logbook, pendaftaran sidang, penilaian). Tim terdiri dari empat mahasiswa dengan waktu terbatas dan pengalaman utama di Python. Tim juga perlu satu sistem yang bisa dijalankan dan didemokan dengan langkah sederhana dari README.

## Keputusan

Kami membangun SIKAP sebagai **satu aplikasi monolith** dengan FastAPI, yang merender halaman HTML di server menggunakan Jinja2 dan Bootstrap 5.

- Satu proses Uvicorn melayani semua halaman, form, dan unggahan berkas.
- Semua route ada di `src/app.py`, template di `src/templates/`, aset di `src/static/`.
- Autentikasi memakai session berbasis cookie bertanda tangan (`SessionMiddleware` dengan `SECRET_KEY`), dan setiap route memeriksa `role` di session.
- Berkas PDF (proposal, logbook, sidang) disimpan di folder `src/uploads/`.

## Alternatif yang dipertimbangkan

- **REST API + frontend terpisah (React/Vue)**: pemisahan lebih rapi dan siap untuk aplikasi mobile. Ditolak karena menambah dua codebase, urusan CORS dan autentikasi token, serta pipeline build frontend, sementara kebutuhan saat ini hanya halaman web biasa.
- **Microservices**: skalabilitas independen per layanan. Ditolak karena terlalu berat untuk satu prodi dan empat orang pengembang; biaya operasional jauh lebih besar daripada manfaatnya.
- **Framework full-stack lain (Flask/Django)**: sama-sama layak. FastAPI dipilih karena ringan, mudah dijalankan dengan Uvicorn, dan menyediakan dokumentasi otomatis bila nanti API dibutuhkan.

## Konsekuensi

- Positif: setup cepat dan sederhana (satu perintah untuk menjalankan), satu codebase mudah di-debug, tidak ada masalah CORS, cocok untuk demo dari README.
- Negatif: `src/app.py` sudah panjang (lebih dari seribu baris) dan akan makin sulit dirawat; ini bisa dipecah dengan `APIRouter` per peran. Berkas upload disimpan di disk lokal, sehingga aplikasi belum bisa dijalankan di banyak instance tanpa penyimpanan bersama. Tidak ada API terpisah untuk klien lain (mis. aplikasi mobile).

## Kondisi untuk meninjau ulang

Keputusan ini ditinjau ulang bila ada kebutuhan resmi aplikasi mobile atau integrasi dengan sistem lain yang butuh API, atau bila tim pengembang bertambah banyak sehingga satu codebase menjadi hambatan kerja paralel.

## Pertahanan keputusan: melawan frontend terpisah (SPA + REST API)

**Alternatif yang ditolak:** memisahkan frontend (React/Vue) dari backend REST API.

**Mengapa monolith tetap lebih baik untuk kondisi SIKAP saat ini:**

1. **Kompleksitas sebanding dengan kebutuhan.** Semua fitur SIKAP adalah form, tabel, dan unggah berkas. Halaman yang dirender server menyelesaikan ini tanpa pipeline build, manajemen state klien, atau autentikasi token.
2. **Tim kecil dan waktu terbatas.** Satu codebase berarti satu tempat untuk debugging dan satu perintah untuk menjalankan, yang juga memenuhi syarat demo dari README.
3. **Keamanan lebih sederhana.** Session cookie bertanda tangan dan pengecekan role per route lebih sedikit titik kegagalannya dibanding mengelola JWT, CORS, dan penyimpanan token di sisi klien.
4. **Biaya operasional rendah.** Hanya satu proses yang dideploy dan dimonitor di server kampus.

**Kondisi yang akan membuat tim berganti ke SPA + REST API:**

- Ada permintaan resmi aplikasi mobile atau integrasi dengan sistem lain (mis. sistem akademik kampus) yang membutuhkan API.
- Antarmuka butuh interaktivitas tinggi yang sulit dipenuhi halaman server-rendered (mis. dashboard real-time).
- Jumlah pengembang bertambah sehingga pemisahan tim frontend dan backend memberi keuntungan nyata.

Selama tidak ada pemicu itu, pemisahan hanya menambah biaya tanpa manfaat bagi pengguna. Bila pemicunya muncul, jalur migrasinya jelas: route yang sudah ada dapat dipecah dengan `APIRouter` dan diubah bertahap menjadi endpoint JSON, tanpa menulis ulang logika bisnis dan skema database.
