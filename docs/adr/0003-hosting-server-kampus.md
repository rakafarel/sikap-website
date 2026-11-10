# ADR-003: Hosting di server kampus

- Status: Diterima
- Tanggal: 2026-10-28

## Konteks

SIKAP menyimpan data akademik yang bersifat internal: identitas mahasiswa dan dosen, logbook, berkas sidang, dan nilai. Pengguna utamanya adalah civitas Prodi Informatika, Universitas Muhammadiyah Indonesia. Anggaran proyek terbatas, dan data sebaiknya tetap berada di bawah kendali institusi. Selama pengembangan, tim menjalankan aplikasi secara lokal.

## Keputusan

Kami meng-host SIKAP di **server milik kampus**.

- Aplikasi dijalankan dengan Uvicorn dari folder `src` dan melayani pengguna lewat jaringan kampus [isi: domain/alamat yang disepakati, mis. `sikap.<domain-kampus>`].
- MySQL/MariaDB berjalan di server yang sama atau server basis data kampus [isi sesuai kondisi sebenarnya].
- Untuk produksi, aplikasi dijalankan tanpa mode `reload`, dan terikat ke alamat yang bisa dijangkau pengguna, misalnya `uvicorn app:app --host 0.0.0.0 --port 8000` dari folder `src`, idealnya di belakang reverse proxy (Nginx) dengan HTTPS.
- `SECRET_KEY` dan password database harus diganti dari nilai default, dan password admin awal (`admin123`) wajib diubah.

## Alternatif yang dipertimbangkan

- **VPS/cloud (mis. DigitalOcean, AWS)**: bisa diakses dari mana saja dan kendali penuh. Ditolak karena ada biaya berulang dan data akademik berada di luar institusi.
- **PaaS (mis. Railway, Render)**: deploy paling mudah. Ditolak karena biaya, batasan penyimpanan berkas upload, dan data berada di pihak ketiga.
- **Laptop lokal + ngrok**: cepat untuk demo. Ditolak untuk penggunaan nyata karena tidak stabil, bergantung pada laptop yang menyala, dan membuka aplikasi lewat tunnel publik; tetap dipakai hanya untuk demo sementara.

## Konsekuensi

- Positif: tanpa biaya hosting tambahan, data tetap di bawah kendali kampus, mudah diintegrasikan dengan jaringan internal.
- Negatif: ketersediaan dan backup bergantung pada kebijakan dan jadwal tim IT kampus; akses dari luar jaringan kampus mungkin memerlukan VPN atau pengaturan khusus; tim perlu koordinasi untuk akses server dan penerapan HTTPS. Berkas upload tersimpan di disk server sehingga folder `src/uploads/` perlu masuk jadwal backup.

## Kondisi untuk meninjau ulang

Keputusan ini ditinjau ulang bila kampus tidak dapat menyediakan server atau akses yang memadai, bila downtime server kampus mengganggu proses pendaftaran sidang, atau bila pengguna perlu mengakses SIKAP dari luar kampus secara rutin tanpa VPN.
