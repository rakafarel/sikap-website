import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()  # baca file .env

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# --- Konfigurasi folder upload (src/uploads) ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_ROOT = os.path.join(BASE_DIR, 'uploads')

UPLOAD_FOLDER = os.path.join(UPLOAD_ROOT, 'proposal')
UPLOAD_LOGBOOK = os.path.join(UPLOAD_ROOT, 'logbook')
UPLOAD_SIDANG = os.path.join(UPLOAD_ROOT, 'sidang')
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['UPLOAD_FOLDER_PROPOSAL'] = UPLOAD_FOLDER
app.config['UPLOAD_LOGBOOK'] = UPLOAD_LOGBOOK
app.config['UPLOAD_SIDANG'] = UPLOAD_SIDANG

# Buat folder penyimpanan jika belum ada
for folder in (UPLOAD_FOLDER, UPLOAD_LOGBOOK, UPLOAD_SIDANG):
    os.makedirs(folder, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME'),
        cursorclass=pymysql.cursors.DictCursor
    )

# --- FUNGSI BANTUAN: Cek Kelulusan Sidang KP ---
def cek_sudah_lulus_kp(user_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT nilai_akhir FROM pendaftaran_sidang 
            WHERE id_mahasiswa = %s AND nilai_akhir IS NOT NULL
        """, (user_id,))
        sidang = cursor.fetchone()
    conn.close()
    return sidang is not None

# --- ROUTE UTAMA & AUTENTIKASI ---

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for(f"dashboard_{session['role']}"))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['nama'] = user['nama']
            session['role'] = user['role']
            
            flash(f"Selamat datang, {user['nama']}!", "success")
            return redirect(url_for(f"dashboard_{user['role']}"))
        else:
            flash("Username atau password salah!", "danger")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        nama = request.form['nama']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            existing_user = cursor.fetchone()

            if existing_user:
                flash("NPM / NIDN / Username sudah terdaftar!", "danger")
                conn.close()
                return redirect(url_for('register'))

            cursor.execute(
                "INSERT INTO users (username, password, nama, role) VALUES (%s, %s, %s, %s)",
                (username, hashed_password, nama, role)
            )
            user_id = cursor.lastrowid

            if role == 'dosen':
                cursor.execute(
                    "INSERT INTO dosen (id_dosen, max_kuota, kuota_terpakai) VALUES (%s, 2, 0)",
                    (user_id,)
                )

            conn.commit()
        conn.close()

        flash("Registrasi berhasil! Silakan login dengan akun kamu.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Anda berhasil keluar dari sistem SiKP.", "info")
    return redirect(url_for('login'))

# --- ROUTE DASHBOARD MULTI-ROLE ---

@app.route('/dashboard/mahasiswa')
def dashboard_mahasiswa():
    if 'role' not in session or session['role'] != 'mahasiswa':
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT p.*, u1.nama AS nama_p1, u2.nama AS nama_p2 
            FROM pengajuan_pembimbing p
            LEFT JOIN users u1 ON p.id_dosen_p1 = u1.id
            LEFT JOIN users u2 ON p.id_dosen_p2 = u2.id
            WHERE p.id_mahasiswa = %s
            ORDER BY p.id_pengajuan DESC LIMIT 1
        """, (user_id,))
        pengajuan = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) AS total_acc FROM logbook WHERE id_mahasiswa = %s AND status_acc = 'approved'", (user_id,))
        logbook_stat = cursor.fetchone()

        cursor.execute("""
            SELECT p.*, d1.nama AS nama_p1, d2.nama AS nama_p2, d3.nama AS nama_p3 
            FROM pengajuan_ta p
            JOIN users d1 ON p.id_dosen_p1 = d1.id
            JOIN users d2 ON p.id_dosen_p2 = d2.id
            JOIN users d3 ON p.id_dosen_p3 = d3.id
            WHERE p.id_mahasiswa = %s
            ORDER BY p.id_pengajuan DESC LIMIT 1
        """, (user_id,))
        pengajuan_ta = cursor.fetchone()

    conn.close()

    return render_template('dashboard_mahasiswa.html', pengajuan=pengajuan, pengajuan_ta=pengajuan_ta, logbook_stat=logbook_stat)

@app.route('/mahasiswa/pengajuan', methods=['GET', 'POST'])
def mahasiswa_pengajuan():
    if 'role' not in session or session['role'] != 'mahasiswa':
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    if request.method == 'POST':
        id_dosen_p1 = request.form['id_dosen_p1']
        id_dosen_p2 = request.form['id_dosen_p2']
        judul_kp = request.form['judul_kp']
        topik_kp = request.form['topik_kp']
        file = request.files['file_proposal']

        if id_dosen_p1 == id_dosen_p2:
            flash("Dosen Prioritas 1 dan Prioritas 2 tidak boleh orang yang sama!", "danger")
            return redirect(url_for('mahasiswa_pengajuan'))

        if file and allowed_file(file.filename):
            filename = secure_filename(f"{session['username']}_proposal.pdf")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO pengajuan_pembimbing 
                    (id_mahasiswa, id_dosen_p1, id_dosen_p2, judul_kp, topik_kp, file_proposal, status_p1, status_p2, status_final)
                    VALUES (%s, %s, %s, %s, %s, %s, 'pending', 'in_queue', 'waiting')
                """, (user_id, id_dosen_p1, id_dosen_p2, judul_kp, topik_kp, filename))
                conn.commit()

            flash("Pengajuan Dosen Pembimbing berhasil dikirim!", "success")
            return redirect(url_for('mahasiswa_pengajuan'))
        else:
            flash("Format file proposal harus berupa file .PDF!", "danger")

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT d.id_dosen, u.nama, d.max_kuota, d.kuota_terpakai 
            FROM dosen d 
            JOIN users u ON d.id_dosen = u.id 
            WHERE d.kuota_terpakai < d.max_kuota
        """)
        daftar_dosen = cursor.fetchall()

        cursor.execute("""
            SELECT p.*, u1.nama AS nama_p1, u2.nama AS nama_p2 
            FROM pengajuan_pembimbing p
            LEFT JOIN users u1 ON p.id_dosen_p1 = u1.id
            LEFT JOIN users u2 ON p.id_dosen_p2 = u2.id
            WHERE p.id_mahasiswa = %s
            ORDER BY p.id_pengajuan DESC LIMIT 1
        """, (user_id,))
        pengajuan_saya = cursor.fetchone()

    conn.close()

    return render_template('mahasiswa_pengajuan.html', daftar_dosen=daftar_dosen, pengajuan=pengajuan_saya)

@app.route('/dashboard/admin')
def dashboard_admin():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT ps.*, u.nama AS nama_mahasiswa, u.username AS npm,
                   p.judul_kp, u_penguji.nama AS nama_penguji
            FROM pendaftaran_sidang ps
            JOIN users u ON ps.id_mahasiswa = u.id
            JOIN pengajuan_pembimbing p ON ps.id_mahasiswa = p.id_mahasiswa
            LEFT JOIN users u_penguji ON ps.id_penguji = u_penguji.id
            ORDER BY ps.created_at DESC
        """)
        daftar_sidang = cursor.fetchall()

        cursor.execute("SELECT id, nama FROM users WHERE role = 'dosen'")
        daftar_dosen = cursor.fetchall()
    conn.close()

    return render_template('dashboard_admin.html', pendaftaran=daftar_sidang, dosen=daftar_dosen)

@app.route('/admin/verifikasi_sidang', methods=['POST'])
def admin_verifikasi_sidang():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    id_sidang = request.form['id_sidang']
    aksi = request.form['aksi']
    
    conn = get_db_connection()
    with conn.cursor() as cursor:
        if aksi == 'terima':
            tanggal = request.form['tanggal_sidang']
            waktu = request.form['waktu_sidang']
            ruangan = request.form['ruangan']
            id_penguji = request.form['id_penguji']

            cursor.execute("""
                UPDATE pendaftaran_sidang 
                SET status_verifikasi = 'verified', tanggal_sidang = %s, waktu_sidang = %s, ruangan = %s, id_penguji = %s
                WHERE id_sidang = %s
            """, (tanggal, waktu, ruangan, id_penguji, id_sidang))
            flash("Berkas disetujui dan jadwal sidang berhasil diplot!", "success")
            
        elif aksi == 'tolak':
            catatan = request.form['catatan_admin']
            cursor.execute("""
                UPDATE pendaftaran_sidang 
                SET status_verifikasi = 'rejected', catatan_admin = %s
                WHERE id_sidang = %s
            """, (catatan, id_sidang))
            flash("Pendaftaran sidang ditolak.", "warning")

        conn.commit()
    conn.close()

    return redirect(url_for('dashboard_admin'))

@app.route('/dashboard/kaprodi')
def dashboard_kaprodi():
    if 'role' not in session or session['role'] != 'kaprodi':
        return redirect(url_for('login'))

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'mahasiswa'")
        stat_mhs = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM pendaftaran_sidang WHERE nilai_akhir IS NOT NULL")
        stat_lulus = cursor.fetchone()['total']

        cursor.execute("""
            SELECT u.nama, d.kuota_terpakai, d.max_kuota 
            FROM dosen d 
            JOIN users u ON d.id_dosen = u.id
            ORDER BY d.kuota_terpakai DESC
        """)
        beban_dosen = cursor.fetchall()

        cursor.execute("""
            SELECT ps.nilai_akhir, u.nama AS nama_mahasiswa, u.username AS npm, p.judul_kp
            FROM pendaftaran_sidang ps
            JOIN users u ON ps.id_mahasiswa = u.id
            JOIN pengajuan_pembimbing p ON ps.id_mahasiswa = p.id_mahasiswa
            WHERE ps.nilai_akhir IS NOT NULL
            ORDER BY ps.tanggal_sidang DESC
        """)
        rekap_nilai = cursor.fetchall()
    conn.close()

    return render_template('dashboard_kaprodi.html', 
                           stat={'mhs': stat_mhs, 'lulus': stat_lulus}, 
                           beban_dosen=beban_dosen, 
                           rekap=rekap_nilai)

@app.route('/mahasiswa/logbook', methods=['GET', 'POST'])
def mahasiswa_logbook():
    if 'role' not in session or session['role'] != 'mahasiswa':
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    if request.method == 'POST':
        tanggal = request.form['tanggal']
        topik = request.form['topik']
        file = request.files['file_progress']

        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{session['username']}_log_{tanggal}.pdf")
            file.save(os.path.join(app.config['UPLOAD_LOGBOOK'], filename))

        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO logbook (id_mahasiswa, tanggal_bimbingan, topik_pembahasan, file_progress)
                VALUES (%s, %s, %s, %s)
            """, (user_id, tanggal, topik, filename))
            conn.commit()

        flash("Catatan logbook berhasil ditambahkan!", "success")
        return redirect(url_for('mahasiswa_logbook'))

    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM logbook WHERE id_mahasiswa = %s ORDER BY tanggal_bimbingan DESC", (user_id,))
        daftar_logbook = cursor.fetchall()
    conn.close()

    return render_template('mahasiswa_logbook.html', logbook=daftar_logbook)

@app.route('/dashboard/dosen')
def dashboard_dosen():
    if 'role' not in session or session['role'] != 'dosen':
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM dosen WHERE id_dosen = %s", (user_id,))
        data_dosen = cursor.fetchone()

        cursor.execute("""
            SELECT p.*, u.nama AS nama_mahasiswa, u.username AS npm
            FROM pengajuan_pembimbing p
            JOIN users u ON p.id_mahasiswa = u.id
            WHERE (p.id_dosen_p1 = %s AND p.status_p1 = 'pending')
               OR (p.id_dosen_p2 = %s AND p.status_p2 = 'pending')
        """, (user_id, user_id))
        pengajuan_masuk = cursor.fetchall()

        cursor.execute("""
            SELECT p.*, u.nama AS nama_mahasiswa, u.username AS npm
            FROM pengajuan_pembimbing p
            JOIN users u ON p.id_mahasiswa = u.id
            WHERE (p.id_dosen_p1 = %s AND p.status_p1 = 'accepted')
               OR (p.id_dosen_p2 = %s AND p.status_p2 = 'accepted')
        """, (user_id, user_id))
        mahasiswa_bimbingan = cursor.fetchall()

    conn.close()

    return render_template('dashboard_dosen.html', dosen=data_dosen, pengajuan=pengajuan_masuk, bimbingan=mahasiswa_bimbingan)

@app.route('/dosen/pengajuan/<int:id_pengajuan>/<string:aksi>')
def dosen_aksi_pengajuan(id_pengajuan, aksi):
    if 'role' not in session or session['role'] != 'dosen':
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM dosen WHERE id_dosen = %s", (user_id,))
        data_dosen = cursor.fetchone()

        cursor.execute("SELECT * FROM pengajuan_pembimbing WHERE id_pengajuan = %s", (id_pengajuan,))
        pengajuan = cursor.fetchone()

        if not pengajuan:
            flash("Data pengajuan tidak ditemukan!", "danger")
            conn.close()
            return redirect(url_for('dashboard_dosen'))

        is_p1 = (pengajuan['id_dosen_p1'] == user_id)

        if aksi == 'terima':
            if data_dosen['kuota_terpakai'] >= data_dosen['max_kuota']:
                flash("Gagal menerima! Kuota bimbingan Anda sudah penuh.", "danger")
            else:
                cursor.execute("UPDATE dosen SET kuota_terpakai = kuota_terpakai + 1 WHERE id_dosen = %s", (user_id,))
                if is_p1:
                    cursor.execute("""
                        UPDATE pengajuan_pembimbing 
                        SET status_p1 = 'accepted', status_p2 = 'rejected', status_final = 'accepted' 
                        WHERE id_pengajuan = %s
                    """, (id_pengajuan,))
                else:
                    cursor.execute("""
                        UPDATE pengajuan_pembimbing 
                        SET status_p2 = 'accepted', status_final = 'accepted' 
                        WHERE id_pengajuan = %s
                    """, (id_pengajuan,))

                flash("Pengajuan bimbingan berhasil disetujui!", "success")

        elif aksi == 'tolak':
            if is_p1:
                cursor.execute("""
                    UPDATE pengajuan_pembimbing 
                    SET status_p1 = 'rejected', status_p2 = 'pending' 
                    WHERE id_pengajuan = %s
                """, (id_pengajuan,))
            else:
                cursor.execute("""
                    UPDATE pengajuan_pembimbing 
                    SET status_p2 = 'rejected', status_final = 'unassigned' 
                    WHERE id_pengajuan = %s
                """, (id_pengajuan,))

            flash("Pengajuan bimbingan telah ditolak.", "warning")

        conn.commit()
    conn.close()

    return redirect(url_for('dashboard_dosen'))

@app.route('/dosen/logbook')
def dosen_logbook():
    if 'role' not in session or session['role'] != 'dosen':
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT l.*, u.nama AS nama_mahasiswa, u.username AS npm
            FROM logbook l
            JOIN users u ON l.id_mahasiswa = u.id
            JOIN pengajuan_pembimbing p ON l.id_mahasiswa = p.id_mahasiswa
            WHERE ((p.id_dosen_p1 = %s AND p.status_p1 = 'accepted') 
               OR (p.id_dosen_p2 = %s AND p.status_p2 = 'accepted'))
            ORDER BY l.created_at DESC
        """, (user_id, user_id))
        daftar_logbook = cursor.fetchall()
    conn.close()

    return render_template('dosen_logbook.html', logbook=daftar_logbook)

@app.route('/dosen/logbook/<int:id_logbook>/<string:aksi>')
def dosen_aksi_logbook(id_logbook, aksi):
    if 'role' not in session or session['role'] != 'dosen':
        return redirect(url_for('login'))

    conn = get_db_connection()
    status = 'approved' if aksi == 'acc' else 'rejected'
    
    with conn.cursor() as cursor:
        cursor.execute("UPDATE logbook SET status_acc = %s WHERE id_logbook = %s", (status, id_logbook))
        conn.commit()
    conn.close()

    flash(f"Status logbook berhasil diubah menjadi {status}.", "success")
    return redirect(url_for('dosen_logbook'))

@app.route('/mahasiswa/sidang', methods=['GET', 'POST'])
def mahasiswa_sidang():
    if 'role' not in session or session['role'] != 'mahasiswa':
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    if request.method == 'POST':
        f_laporan = request.files['file_laporan']
        f_transkrip = request.files['file_transkrip']
        f_krs = request.files['file_krs']

        if f_laporan and f_transkrip and f_krs:
            fn_laporan = secure_filename(f"{session['username']}_laporan.pdf")
            fn_transkrip = secure_filename(f"{session['username']}_transkrip.pdf")
            fn_krs = secure_filename(f"{session['username']}_krs.pdf")

            f_laporan.save(os.path.join(app.config['UPLOAD_SIDANG'], fn_laporan))
            f_transkrip.save(os.path.join(app.config['UPLOAD_SIDANG'], fn_transkrip))
            f_krs.save(os.path.join(app.config['UPLOAD_SIDANG'], fn_krs))

            with conn.cursor() as cursor:
                cursor.execute("SELECT id_sidang FROM pendaftaran_sidang WHERE id_mahasiswa = %s", (user_id,))
                cek_sidang = cursor.fetchone()

                if cek_sidang:
                    cursor.execute("""
                        UPDATE pendaftaran_sidang 
                        SET file_laporan_final=%s, file_transkrip=%s, file_krs=%s, status_verifikasi='pending'
                        WHERE id_mahasiswa=%s
                    """, (fn_laporan, fn_transkrip, fn_krs, user_id))
                else:
                    cursor.execute("""
                        INSERT INTO pendaftaran_sidang (id_mahasiswa, file_laporan_final, file_transkrip, file_krs)
                        VALUES (%s, %s, %s, %s)
                    """, (user_id, fn_laporan, fn_transkrip, fn_krs))
                conn.commit()

            flash("Berkas pendaftaran sidang berhasil dikirim!", "success")
            return redirect(url_for('mahasiswa_sidang'))

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT ps.*, u_penguji.nama AS nama_penguji 
            FROM pendaftaran_sidang ps
            LEFT JOIN users u_penguji ON ps.id_penguji = u_penguji.id
            WHERE ps.id_mahasiswa = %s 
            ORDER BY ps.id_sidang DESC LIMIT 1
        """, (user_id,))
        data_sidang = cursor.fetchone()
    conn.close()

    return render_template('mahasiswa_sidang.html', sidang=data_sidang)

@app.route('/dosen/jadwal_menguji', methods=['GET', 'POST'])
def dosen_jadwal_menguji():
    if 'role' not in session or session['role'] != 'dosen':
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()

    if request.method == 'POST':
        id_sidang = request.form['id_sidang']
        nilai = request.form['nilai_akhir']
        revisi = request.form['catatan_revisi']

        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE pendaftaran_sidang 
                SET nilai_akhir = %s, catatan_revisi = %s 
                WHERE id_sidang = %s AND id_penguji = %s
            """, (nilai, revisi, id_sidang, user_id))
            conn.commit()
            
        flash("Nilai dan catatan revisi berhasil disimpan!", "success")
        return redirect(url_for('dosen_jadwal_menguji'))

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT ps.*, u.nama AS nama_mahasiswa, u.username AS npm, p.judul_kp 
            FROM pendaftaran_sidang ps
            JOIN users u ON ps.id_mahasiswa = u.id
            JOIN pengajuan_pembimbing p ON ps.id_mahasiswa = p.id_mahasiswa
            WHERE ps.id_penguji = %s AND ps.status_verifikasi = 'verified'
            ORDER BY ps.tanggal_sidang ASC, ps.waktu_sidang ASC
        """, (user_id,))
        jadwal_menguji = cursor.fetchall()
    conn.close()

    return render_template('dosen_jadwal_menguji.html', jadwal=jadwal_menguji)

@app.route('/admin/kuota_dosen', methods=['GET', 'POST'])
def admin_kuota_dosen():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    if request.method == 'POST':
        id_dosen = request.form['id_dosen']
        max_kuota = request.form['max_kuota']

        with conn.cursor() as cursor:
            cursor.execute("UPDATE dosen SET max_kuota = %s WHERE id_dosen = %s", (max_kuota, id_dosen))
            conn.commit()
        
        flash("Batas kuota dosen berhasil diperbarui!", "success")
        return redirect(url_for('admin_kuota_dosen'))

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT d.*, u.nama, u.username AS nidn 
            FROM dosen d 
            JOIN users u ON d.id_dosen = u.id
            ORDER BY u.nama ASC
        """)
        daftar_dosen = cursor.fetchall()
    conn.close()

    return render_template('admin_kuota_dosen.html', dosen=daftar_dosen)

@app.route('/admin/mahasiswa')
def admin_mahasiswa():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT u.id, u.nama, u.username AS npm,
                   p.status_final, p.judul_kp,
                   u_p1.nama AS nama_p1, u_p2.nama AS nama_p2,
                   ps.status_verifikasi AS status_sidang, ps.nilai_akhir
            FROM users u
            LEFT JOIN pengajuan_pembimbing p ON u.id = p.id_mahasiswa
            LEFT JOIN users u_p1 ON p.id_dosen_p1 = u_p1.id
            LEFT JOIN users u_p2 ON p.id_dosen_p2 = u_p2.id
            LEFT JOIN pendaftaran_sidang ps ON u.id = ps.id_mahasiswa
            WHERE u.role = 'mahasiswa'
            ORDER BY u.nama ASC
        """)
        daftar_mahasiswa = cursor.fetchall()
    conn.close()

    return render_template('admin_mahasiswa.html', mahasiswa=daftar_mahasiswa)

@app.route('/mahasiswa/ta/pengajuan', methods=['GET', 'POST'])
def mahasiswa_ta_pengajuan():
    if 'role' not in session or session['role'] != 'mahasiswa':
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    
    if not cek_sudah_lulus_kp(user_id):
        flash("Anda belum dapat mengakses Modul Tugas Akhir. Silakan selesaikan dan lulus Sidang Kerja Praktek (KP) terlebih dahulu.", "danger")
        return redirect(url_for('dashboard_mahasiswa'))

    conn = get_db_connection()

    if request.method == 'POST':
        id_p1 = request.form['id_dosen_p1']
        id_p2 = request.form['id_dosen_p2']
        id_p3 = request.form['id_dosen_p3']
        judul = request.form['judul_ta']
        topik = request.form['topik_ta']
        
        if id_p1 == id_p2 or id_p1 == id_p3 or id_p2 == id_p3:
            flash("Pilihan Dosen Pembimbing 1, 2, dan 3 tidak boleh ada yang sama!", "danger")
            return redirect(url_for('mahasiswa_ta_pengajuan'))

        file_prop = request.files['file_proposal_ta']
        
        if file_prop and file_prop.filename != '':
            filename = secure_filename(file_prop.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER_PROPOSAL'], filename)
            file_prop.save(file_path)

            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO pengajuan_ta (id_mahasiswa, id_dosen_p1, id_dosen_p2, id_dosen_p3, judul_ta, topik_ta, file_proposal_ta, pilihan_aktif, status_p1, status_final)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 'pending', 'pending')
                """, (user_id, id_p1, id_p2, id_p3, judul, topik, filename))
                conn.commit()
            
            flash("Pengajuan Dosen Pembimbing Tugas Akhir dengan 3 pilihan berhasil dikirim!", "success")
            return redirect(url_for('mahasiswa_ta_pengajuan'))

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT p.*, 
                   d1.nama AS nama_p1, d2.nama AS nama_p2, d3.nama AS nama_p3 
            FROM pengajuan_ta p
            JOIN users d1 ON p.id_dosen_p1 = d1.id
            JOIN users d2 ON p.id_dosen_p2 = d2.id
            JOIN users d3 ON p.id_dosen_p3 = d3.id
            WHERE p.id_mahasiswa = %s
            ORDER BY p.id_pengajuan DESC LIMIT 1
        """, (user_id,))
        pengajuan = cursor.fetchone()

        cursor.execute("SELECT u.id, u.nama FROM users u JOIN dosen d ON u.id = d.id_dosen ORDER BY u.nama ASC")
        daftar_dosen = cursor.fetchall()
    conn.close()

    return render_template('mahasiswa_ta_pengajuan.html', pengajuan=pengajuan, daftar_dosen=daftar_dosen)

@app.route('/mahasiswa/ta/reset_pengajuan')
def mahasiswa_ta_reset_pengajuan():
    if 'role' not in session or session['role'] != 'mahasiswa':
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM pengajuan_ta WHERE id_mahasiswa = %s AND status_final = 'rejected'", (user_id,))
        conn.commit()
    conn.close()
    
    flash("Silakan ajukan kembali dosen pembimbing TA dengan pilihan yang berbeda.", "info")
    return redirect(url_for('mahasiswa_ta_pengajuan'))

@app.route('/admin/akun')
def admin_akun():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, nama, username, role FROM users ORDER BY role ASC, nama ASC")
        users = cursor.fetchall()
    conn.close()

    return render_template('admin_akun.html', users=users)

@app.route('/admin/akun/tambah', methods=['POST'])
def admin_tambah_akun():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    nama = request.form['nama']
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    hashed_password = generate_password_hash(password)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users (nama, username, password, role) 
                VALUES (%s, %s, %s, %s)
            """, (nama, username, hashed_password, role))
            
            if role == 'dosen':
                user_id = cursor.lastrowid
                cursor.execute("""
                    INSERT INTO dosen (id_dosen, max_kuota, kuota_terpakai) 
                    VALUES (%s, 2, 0)
                """, (user_id,))
                
            conn.commit()
        flash("Akun baru berhasil ditambahkan!", "success")
    except Exception as e:
        flash(f"Gagal menambahkan akun: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for('admin_akun'))

@app.route('/admin/akun/edit/<int:id_user>', methods=['POST'])
def admin_edit_akun(id_user):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    nama = request.form['nama']
    username = request.form['username']
    role = request.form['role']
    password = request.form['password']

    conn = get_db_connection()
    with conn.cursor() as cursor:
        if password:
            hashed_password = generate_password_hash(password)
            cursor.execute("""
                UPDATE users SET nama = %s, username = %s, role = %s, password = %s WHERE id = %s
            """, (nama, username, role, hashed_password, id_user))
        else:
            cursor.execute("""
                UPDATE users SET nama = %s, username = %s, role = %s WHERE id = %s
            """, (nama, username, role, id_user))
        conn.commit()
    conn.close()

    flash("Data akun berhasil diperbarui!", "success")
    return redirect(url_for('admin_akun'))

@app.route('/admin/akun/hapus/<int:id_user>')
def admin_hapus_akun(id_user):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM dosen WHERE id_dosen = %s", (id_user,))
        cursor.execute("DELETE FROM users WHERE id = %s", (id_user,))
        conn.commit()
    conn.close()

    flash("Akun berhasil dihapus dari sistem.", "success")
    return redirect(url_for('admin_akun'))

# --- ROUTE KELOLA PENGAJUAN TA (DOSEN) - DIPERBARUI UNTUK 3 PILIHAN ---
@app.route('/dosen/ta')
def dosen_ta():
    if 'role' not in session or session['role'] != 'dosen':
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT p.*, m.nama AS nama_mahasiswa, m.username AS npm,
                   d1.nama AS nama_p1, d2.nama AS nama_p2, d3.nama AS nama_p3
            FROM pengajuan_ta p
            JOIN users m ON p.id_mahasiswa = m.id
            JOIN users d1 ON p.id_dosen_p1 = d1.id
            JOIN users d2 ON p.id_dosen_p2 = d2.id
            JOIN users d3 ON p.id_dosen_p3 = d3.id
            WHERE p.id_dosen_p1 = %s OR p.id_dosen_p2 = %s OR p.id_dosen_p3 = %s
        """, (user_id, user_id, user_id))
        pengajuan_ta = cursor.fetchall()
    conn.close()

    return render_template('dosen_ta.html', pengajuan_ta=pengajuan_ta, user_id=user_id)

# --- AKSI TERIMA / TOLAK PENGAJUAN TA (FALLBACK 3 PILIHAN) - NAMA FUNGSI UNIK ---
@app.route('/dosen/ta/<int:id_pengajuan>/<aksi>')
def dosen_aksi_ta_pengajuan(id_pengajuan, aksi):
    if 'role' not in session or session['role'] != 'dosen':
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM pengajuan_ta WHERE id_pengajuan = %s", (id_pengajuan,))
        p = cursor.fetchone()
        
        if p:
            aktif = p['pilihan_aktif']
            
            if aksi == 'terima':
                cursor.execute("UPDATE pengajuan_ta SET status_final = 'accepted' WHERE id_pengajuan = %s", (id_pengajuan,))
                flash("Pengajuan Tugas Akhir berhasil diterima!", "success")
            else:
                if aktif == 1 and p['id_dosen_p1'] == user_id:
                    cursor.execute("""
                        UPDATE pengajuan_ta 
                        SET status_p1 = 'rejected', pilihan_aktif = 2, status_p2 = 'pending' 
                        WHERE id_pengajuan = %s
                    """, (id_pengajuan,))
                    flash("Pengajuan ditolak dan otomatis diteruskan ke Dosen Pilihan ke-2.", "warning")
                elif aktif == 2 and p['id_dosen_p2'] == user_id:
                    cursor.execute("""
                        UPDATE pengajuan_ta 
                        SET status_p2 = 'rejected', pilihan_aktif = 3, status_p3 = 'pending' 
                        WHERE id_pengajuan = %s
                    """, (id_pengajuan,))
                    flash("Pengajuan ditolak dan otomatis diteruskan ke Dosen Pilihan ke-3.", "warning")
                elif aktif == 3 and p['id_dosen_p3'] == user_id:
                    cursor.execute("""
                        UPDATE pengajuan_ta 
                        SET status_p3 = 'rejected', status_final = 'rejected' 
                        WHERE id_pengajuan = %s
                    """, (id_pengajuan,))
                    flash("Pengajuan ditolak oleh seluruh pilihan dosen.", "danger")
            
            conn.commit()
    conn.close()
    return redirect(url_for('dosen_ta'))

@app.route('/mahasiswa/ta/logbook', methods=['GET', 'POST'])
def mahasiswa_ta_logbook():
    if 'role' not in session or session['role'] != 'mahasiswa':
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    
    if not cek_sudah_lulus_kp(user_id):
        flash("Anda belum dapat mengakses Logbook Tugas Akhir sebelum menyelesaikan Sidang Kerja Praktek (KP).", "danger")
        return redirect(url_for('dashboard_mahasiswa'))

    conn = get_db_connection()

    if request.method == 'POST':
        tanggal = request.form['tanggal_bimbingan']
        topik = request.form['topik_pembahasan']
        file_prog = request.files['file_progress']
        
        filename = None
        if file_prog and file_prog.filename != '':
            filename = secure_filename(file_prog.filename)
            file_path = os.path.join(app.config['UPLOAD_LOGBOOK'], filename)
            file_prog.save(file_path)

        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO logbook_ta (id_mahasiswa, tanggal_bimbingan, topik_pembahasan, file_progress, status_acc)
                VALUES (%s, %s, %s, %s, 'pending')
            """, (user_id, tanggal, topik, filename))
            conn.commit()
        
        flash("Catatan bimbingan TA berhasil dikirim!", "success")
        return redirect(url_for('mahasiswa_ta_logbook'))

    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM logbook_ta WHERE id_mahasiswa = %s ORDER BY tanggal_bimbingan DESC", (user_id,))
        logbook_list = cursor.fetchall()
    conn.close()

    return render_template('mahasiswa_ta_logbook.html', logbook=logbook_list)

@app.route('/dosen/ta/logbook')
def dosen_ta_logbook():
    if 'role' not in session or session['role'] != 'dosen':
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT l.*, m.nama AS nama_mahasiswa, m.username AS npm
            FROM logbook_ta l
            JOIN users m ON l.id_mahasiswa = m.id
            JOIN pengajuan_ta p ON m.id = p.id_mahasiswa
            WHERE p.id_dosen_p1 = %s OR p.id_dosen_p2 = %s OR p.id_dosen_p3 = %s
            ORDER BY l.tanggal_bimbingan DESC
        """, (user_id, user_id, user_id))
        logbook_ta = cursor.fetchall()
    conn.close()

    return render_template('dosen_ta_logbook.html', logbook=logbook_ta)

@app.route('/dosen/ta/logbook/<int:id_logbook>/acc')
def dosen_ta_logbook_acc(id_logbook):
    if 'role' not in session or session['role'] != 'dosen':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("UPDATE logbook_ta SET status_acc = 'approved' WHERE id_logbook = %s", (id_logbook,))
        conn.commit()
    conn.close()
    
    flash("Logbook TA berhasil disetujui!", "success")
    return redirect(url_for('dosen_ta_logbook'))

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG') == '1')