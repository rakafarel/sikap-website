import os
from dotenv import load_dotenv
import pymysql
from werkzeug.security import generate_password_hash

# Baca konfigurasi dari file .env
load_dotenv()

# Hubungkan ke database MySQL
conn = pymysql.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME'),
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with conn.cursor() as cursor:
        username = "admin"  # Ganti username/NIDN admin sesuai keinginan
        nama = "Administrator Sistem"
        password_plain = "admin123"  # Ganti password sesuai keinginan
        
        # Hash password menggunakan Werkzeug agar sinkron dengan app.py
        hashed_password = generate_password_hash(password_plain)

        # Cek apakah username sudah ada
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            print(f"Gagal: Username '{username}' sudah terdaftar di database!")
        else:
            # Masukkan ke tabel users dengan role 'admin'
            cursor.execute(
                "INSERT INTO users (username, password, nama, role) VALUES (%s, %s, %s, %s)",
                (username, hashed_password, nama, 'admin')
            )
            conn.commit()
            print("Sukses! Akun Admin berhasil dibuat.")
            print(f"Username : {username}")
            print(f"Password : {password_plain}")
finally:
    conn.close()