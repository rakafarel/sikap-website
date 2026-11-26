# Laporan Perancangan ERD & Pemetaan Tabel Story Must — SIKAP
**Mata Kuliah:** Proyek Perangkat Lunak (S1 Informatika, Semester Ganjil 2026/2027)  
**Tim:** VanguardT1 (4 Anggota)  
**Produk:** SIKAP (Sistem Informasi Kerja Praktik & Tugas Akhir)  

---

## 1. Diagram Hubungan Entitas (Entity-Relationship Diagram / ERD)
Berikut adalah visualisasi struktur basis data SIKAP yang dirancang untuk mendukung alur kerja sekuensial (dari Kerja Praktik hingga Tugas Akhir):

```mermaid
erDiagram
    users ||--o{ mahasiswa : "memiliki"
    users ||--o{ dosen : "memiliki"
    mahasiswa ||--o{ pengajuan_kp : "mengajukan"
    dosen ||--o{ pengajuan_kp : "membimbing (P1, P2, P3)"
    pengajuan_kp ||--o{ logbook : "mencatat"
    pengajuan_kp ||--o{ sidang_kp : "diuji dalam"
    mahasiswa ||--o{ pengajuan_ta : "mengajukan (bersyarat)"
    dosen ||--o{ pengajuan_ta : "membimbing TA"
    sidang_kp ||--|| pengajuan_ta : "prasyarat kelulusan (sequential lock)"

    users {
        int id PK
        string email
        string password
        string peran
    }

    mahasiswa {
        int id PK
        int user_id FK
        string npm
        string prodi
    }

    dosen {
        int id PK
        int user_id FK
        string nidn
        int kuota_maksimal
        int kuota_terpakai
    }

    pengajuan_kp {
        int id PK
        int mahasiswa_id FK
        int id_dosen_p1 FK
        int id_dosen_p2 FK
        int id_dosen_p3 FK
        string judul_kp
        string file_proposal
        string status
    }

    logbook {
        int id PK
        int pengajuan_id FK
        string tipe
        date tanggal
        string topik_pembahasan
        string file_progress
        string status_acc
    }

    sidang_kp {
        int id PK
        int pengajuan_kp_id FK
        int penguji_id FK
        datetime tanggal_waktu
        string status_kelulusan
    }

    pengajuan_ta {
        int id PK
        int mahasiswa_id FK
        int dosen_id FK
        string judul_ta
        string status
    }