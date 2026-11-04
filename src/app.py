import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from jinja2 import pass_context
import pymysql
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()  # baca file .env

app = FastAPI()

# Middleware Session untuk kompatibilitas session & flash message Flask
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
app.add_middleware(SessionMiddleware, secret_key=app.secret_key)

# --- Konfigurasi folder upload (src/uploads) ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_ROOT = os.path.join(BASE_DIR, 'uploads')

UPLOAD_FOLDER = os.path.join(UPLOAD_ROOT, 'proposal')
UPLOAD_LOGBOOK = os.path.join(UPLOAD_ROOT, 'logbook')
UPLOAD_SIDANG = os.path.join(UPLOAD_ROOT, 'sidang')
UPLOAD_PROFIL = os.path.join(UPLOAD_ROOT, 'profil')
os.makedirs(UPLOAD_PROFIL, exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf'}

# Buat folder penyimpanan jika belum ada
for folder in (UPLOAD_FOLDER, UPLOAD_LOGBOOK, UPLOAD_SIDANG, UPLOAD_PROFIL):
    os.makedirs(folder, exist_ok=True)

# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- CONTEXT PROCESSOR & JINJA2 GLOBALS (KOMPATIBILITAS FLASK) ---

# 1. Otomatis menyuntikkan 'session' ke seluruh template HTML
def session_context_processor(request: Request):
    return {"session": request.session}

templates = Jinja2Templates(
    directory="templates",
    context_processors=[session_context_processor]
)

# 2. Custom url_for agar mendukung static filename='...' ala Flask dan route FastAPI
def custom_url_for(name: str, **path_params):
    try:
        if name == 'static' and 'filename' in path_params:
            path_params['path'] = path_params.pop('filename')
        return app.url_path_for(name, **path_params)
    except Exception:
        return "#"

templates.env.globals['url_for'] = custom_url_for

# 3. Custom Flash Message Bridge dengan @pass_context agar mendukung {{ get_flashed_messages(...) }}
@pass_context
def get_flashed_messages(context, **kwargs):
    request = context.get("request")
    if request and "_messages" in request.session:
        messages = request.session["_messages"]
        del request.session["_messages"]
        return messages
    return []

def flash(request: Request, message: str, category: str = "info"):
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append((category, message))

templates.env.globals['get_flashed_messages'] = get_flashed_messages


# --- FUNGSI UTILITY & DATABASE ---

def allowed_file(filename: str):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME'),
        cursorclass=pymysql.cursors.DictCursor
    )

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


@app.get('/api/status-kp')
async def api_status_kp(request: Request):
    if request.session.get('role') != 'mahasiswa':
        return JSONResponse({'lulus': False}, status_code=401)
    return JSONResponse({'lulus': cek_sudah_lulus_kp(request.session['user_id'])})

# --- ROUTE UTAMA & AUTENTIKASI ---

@app.get('/', name='home')
async def home(request: Request):
    if 'user_id' in request.session:
        role = request.session['role']
        return RedirectResponse(url=f"/dashboard/{role}", status_code=303)
    return RedirectResponse(url="/login", status_code=303)

@app.get('/login', name='login')
async def login_get(request: Request):
    return templates.TemplateResponse(request=request, name='auth.html')

@app.post('/login')
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password'], password):
        request.session['user_id'] = user['id']
        request.session['username'] = user['username']
        request.session['nama'] = user['nama']
        request.session['role'] = user['role']
        
        return RedirectResponse(url=f"/dashboard/{user['role']}", status_code=303)
    else:
        flash(request, "Username atau password salah!", "danger")
        return templates.TemplateResponse(request=request, name='auth.html')

@app.get('/register', name='register')
async def register_get(request: Request):
    return templates.TemplateResponse(request=request, name='auth.html')

@app.post('/register')
async def register_post(
    request: Request, 
    username: str = Form(...), 
    nama: str = Form(...), 
    password: str = Form(...), 
    role: str = Form(...)
):
    hashed_password = generate_password_hash(password)

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash(request, "NPM / NIDN / Username sudah terdaftar!", "danger")
            conn.close()
            return templates.TemplateResponse(request=request, name='auth.html')

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

    flash(request, "Registrasi berhasil! Silakan login dengan akun kamu.", "success")
    return RedirectResponse(url='/login', status_code=303)

@app.get('/logout', name='logout')
async def logout(request: Request):
    request.session.clear()
    flash(request, "Anda berhasil keluar dari SIKAP.", "info")
    return RedirectResponse(url='/login', status_code=303)

# --- BUKA BERKAS UPLOAD (proposal, logbook, sidang) ---
@app.get('/uploads/{folder}/{filename}', name='buka_berkas')
async def buka_berkas(request: Request, folder: str, filename: str):
    if 'user_id' not in request.session:
        return RedirectResponse(url='/login', status_code=303)
    
    folders = {
        'proposal': UPLOAD_FOLDER,
        'logbook': UPLOAD_LOGBOOK,
        'sidang': UPLOAD_SIDANG,
        'profil': UPLOAD_PROFIL,
    }
    if folder not in folders:
        raise HTTPException(status_code=404)
    
    file_path = os.path.join(folders[folder], filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404)
        
    return FileResponse(file_path)

# --- ROUTE DASHBOARD MULTI-ROLE & FITUR MAHASISWA ---

@app.get('/dashboard/mahasiswa', name='dashboard_mahasiswa')
async def dashboard_mahasiswa(request: Request):
    if request.session.get('role') != 'mahasiswa':
        return RedirectResponse(url='/login', status_code=303)

    user_id = request.session['user_id']
    conn = get_db_connection()
    
    with conn.cursor() as cursor:
        # TAMBAHKAN INI: Ambil data user yang sedang login (termasuk foto_profil)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

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

        cursor.execute("""
            SELECT status_verifikasi, nilai_akhir, tanggal_sidang, waktu_sidang
            FROM pendaftaran_sidang WHERE id_mahasiswa = %s
            ORDER BY id_sidang DESC LIMIT 1
        """, (user_id,))
        sidang = cursor.fetchone()

    conn.close()

    return templates.TemplateResponse(
        request=request, 
        name='dashboard_mahasiswa.html', 
        context={
            'user': user,  # <--- WAJIB ADA AGAR TERBACA DI HTML SIDEBAR
            'pengajuan': pengajuan, 
            'pengajuan_ta': pengajuan_ta, 
            'logbook_stat': logbook_stat, 
            'sidang': sidang
        }
    )

@app.get('/mahasiswa/pengajuan', name='mahasiswa_pengajuan')
async def mahasiswa_pengajuan_get(request: Request):
    if request.session.get('role') != 'mahasiswa':
        return RedirectResponse(url='/login', status_code=303)

    user_id = request.session['user_id']
    conn = get_db_connection()

    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

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
    return templates.TemplateResponse(
        request=request, 
        name='mahasiswa_pengajuan.html', 
        context={'user': user, 'daftar_dosen': daftar_dosen, 'pengajuan': pengajuan_saya}
    )

@app.post('/mahasiswa/pengajuan')
async def mahasiswa_pengajuan_post(
    request: Request,
    id_dosen_p1: int = Form(...),
    id_dosen_p2: int = Form(...),
    judul_kp: str = Form(...),
    topik_kp: str = Form(...),
    file_proposal: UploadFile = File(...)
):
    if request.session.get('role') != 'mahasiswa':
        return RedirectResponse(url='/login', status_code=303)

    user_id = request.session['user_id']
    if id_dosen_p1 == id_dosen_p2:
        flash(request, "Dosen Prioritas 1 dan Prioritas 2 tidak boleh orang yang sama!", "danger")
        return RedirectResponse(url='/mahasiswa/pengajuan', status_code=303)

    if file_proposal and allowed_file(file_proposal.filename):
        filename = secure_filename(f"{request.session['username']}_proposal.pdf")
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(await file_proposal.read())

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO pengajuan_pembimbing 
                (id_mahasiswa, id_dosen_p1, id_dosen_p2, judul_kp, topik_kp, file_proposal, status_p1, status_p2, status_final)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending', 'in_queue', 'waiting')
            """, (user_id, id_dosen_p1, id_dosen_p2, judul_kp, topik_kp, filename))
            conn.commit()
        conn.close()

        flash(request, "Pengajuan Dosen Pembimbing berhasil dikirim!", "success")
    else:
        flash(request, "Format file proposal harus berupa file .PDF!", "danger")

    return RedirectResponse(url='/mahasiswa/pengajuan', status_code=303)

@app.get('/mahasiswa/logbook', name='mahasiswa_logbook')
async def mahasiswa_logbook_get(request: Request):
    if request.session.get('role') != 'mahasiswa':
        return RedirectResponse(url='/login', status_code=303)

    user_id = request.session['user_id']
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.execute("SELECT * FROM logbook WHERE id_mahasiswa = %s ORDER BY tanggal_bimbingan DESC", (user_id,))
        daftar_logbook = cursor.fetchall()
    conn.close()

    return templates.TemplateResponse(
        request=request, 
        name='mahasiswa_logbook.html', 
        context={'user': user, 'logbook': daftar_logbook}
    )

@app.post('/mahasiswa/logbook')
async def mahasiswa_logbook_post(
    request: Request,
    tanggal_bimbingan: str = Form(...),
    topik_pembahasan: str = Form(...),
    file_progress: UploadFile = File(None)
):
    if request.session.get('role') != 'mahasiswa':
        return RedirectResponse(url='/login', status_code=303)

    user_id = request.session['user_id']
    filename = None
    if file_progress and file_progress.filename and allowed_file(file_progress.filename):
        filename = secure_filename(f"{request.session['username']}_log_{tanggal_bimbingan}.pdf")
        file_path = os.path.join(UPLOAD_LOGBOOK, filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file_progress.read())

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO logbook (id_mahasiswa, tanggal_bimbingan, topik_pembahasan, file_progress)
            VALUES (%s, %s, %s, %s)
        """, (user_id, tanggal_bimbingan, topik_pembahasan, filename))
        conn.commit()
    conn.close()

    flash(request, "Catatan logbook berhasil ditambahkan!", "success")
    return RedirectResponse(url='/mahasiswa/logbook', status_code=303)

@app.get('/mahasiswa/sidang', name='mahasiswa_sidang')
async def mahasiswa_sidang_get(request: Request):
    if request.session.get('role') != 'mahasiswa':
        return RedirectResponse(url='/login', status_code=303)

    user_id = request.session['user_id']
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.execute("""
            SELECT ps.*, u_penguji.nama AS nama_penguji 
            FROM pendaftaran_sidang ps
            LEFT JOIN users u_penguji ON ps.id_penguji = u_penguji.id
            WHERE ps.id_mahasiswa = %s 
            ORDER BY ps.id_sidang DESC LIMIT 1
        """, (user_id,))
        data_sidang = cursor.fetchone()
    conn.close()

    return templates.TemplateResponse(
        request=request, 
        name='mahasiswa_sidang.html', 
        context={'user': user, 'sidang': data_sidang}
    )

@app.post('/mahasiswa/sidang')
async def mahasiswa_sidang_post(
    request: Request,
    file_laporan: UploadFile = File(...),
    file_transkrip: UploadFile = File(...),
    file_krs: UploadFile = File(...)
):
    if request.session.get('role') != 'mahasiswa':
        return RedirectResponse(url='/login', status_code=303)

    user_id = request.session['user_id']
    if file_laporan and file_transkrip and file_krs:
        fn_laporan = secure_filename(f"{request.session['username']}_laporan.pdf")
        fn_transkrip = secure_filename(f"{request.session['username']}_transkrip.pdf")
        fn_krs = secure_filename(f"{request.session['username']}_krs.pdf")

        for f_obj, f_name in [(file_laporan, fn_laporan), (file_transkrip, fn_transkrip), (file_krs, fn_krs)]:
            path = os.path.join(UPLOAD_SIDANG, f_name)
            with open(path, "wb") as buffer:
                buffer.write(await f_obj.read())

        conn = get_db_connection()
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
        conn.close()

        flash(request, "Berkas pendaftaran sidang berhasil dikirim!", "success")

    return RedirectResponse(url='/mahasiswa/sidang', status_code=303)

# --- MODUL TUGAS AKHIR (TA) MAHASISWA ---

@app.get('/mahasiswa/ta/pengajuan', name='mahasiswa_ta_pengajuan')
async def mahasiswa_ta_pengajuan_get(request: Request):
    if request.session.get('role') != 'mahasiswa':
        return RedirectResponse(url='/login', status_code=303)
        
    user_id = request.session['user_id']
    if not cek_sudah_lulus_kp(user_id):
        flash(request, "Anda belum dapat mengakses Modul Tugas Akhir. Silakan selesaikan dan lulus Sidang Kerja Praktek (KP) terlebih dahulu.", "danger")
        return RedirectResponse(url='/dashboard/mahasiswa', status_code=303)

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.execute("""
            SELECT p.*, d1.nama AS nama_p1, d2.nama AS nama_p2, d3.nama AS nama_p3 
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

    return templates.TemplateResponse(
        request=request, 
        name='mahasiswa_ta_pengajuan.html', 
        context={'user': user, 'pengajuan': pengajuan, 'daftar_dosen': daftar_dosen}
    )

@app.post('/mahasiswa/ta/pengajuan')
async def mahasiswa_ta_pengajuan_post(
    request: Request,
    id_dosen_p1: int = Form(...),
    id_dosen_p2: int = Form(...),
    id_dosen_p3: int = Form(...),
    judul_ta: str = Form(...),
    topik_ta: str = Form(...),
    file_proposal_ta: UploadFile = File(...)
):
    if request.session.get('role') != 'mahasiswa':
        return RedirectResponse(url='/login', status_code=303)
        
    user_id = request.session['user_id']
    if id_dosen_p1 == id_dosen_p2 or id_dosen_p1 == id_dosen_p3 or id_dosen_p2 == id_dosen_p3:
        flash(request, "Pilihan Dosen Pembimbing 1, 2, dan 3 tidak boleh ada yang sama!", "danger")
        return RedirectResponse(url='/mahasiswa/ta/pengajuan', status_code=303)

    if file_proposal_ta and file_proposal_ta.filename:
        filename = secure_filename(file_proposal_ta.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file_proposal_ta.read())

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO pengajuan_ta (id_mahasiswa, id_dosen_p1, id_dosen_p2, id_dosen_p3, judul_ta, topik_ta, file_proposal_ta, pilihan_aktif, status_p1, status_final)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 'pending', 'pending')
            """, (user_id, id_dosen_p1, id_dosen_p2, id_dosen_p3, judul_ta, topik_ta, filename))
            conn.commit()
        conn.close()
        
        flash(request, "Pengajuan Dosen Pembimbing Tugas Akhir dengan 3 pilihan berhasil dikirim!", "success")

    return RedirectResponse(url='/mahasiswa/ta/pengajuan', status_code=303)

@app.get('/mahasiswa/ta/reset_pengajuan', name='mahasiswa_ta_reset_pengajuan')
async def mahasiswa_ta_reset_pengajuan(request: Request):
    if request.session.get('role') != 'mahasiswa':
        return RedirectResponse(url='/login', status_code=303)
        
    user_id = request.session['user_id']
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM pengajuan_ta WHERE id_mahasiswa = %s AND status_final = 'rejected'", (user_id,))
        conn.commit()
    conn.close()
    
    flash(request, "Silakan ajukan kembali dosen pembimbing TA dengan pilihan yang berbeda.", "info")
    return RedirectResponse(url='/mahasiswa/ta/pengajuan', status_code=303)

@app.get('/mahasiswa/ta/logbook', name='mahasiswa_ta_logbook')
async def mahasiswa_ta_logbook_get(request: Request):
    if request.session.get('role') != 'mahasiswa':
        return RedirectResponse(url='/login', status_code=303)
        
    user_id = request.session['user_id']
    if not cek_sudah_lulus_kp(user_id):
        flash(request, "Anda belum dapat mengakses Logbook Tugas Akhir sebelum menyelesaikan Sidang Kerja Praktek (KP).", "danger")
        return RedirectResponse(url='/dashboard/mahasiswa', status_code=303)

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM logbook_ta WHERE id_mahasiswa = %s ORDER BY tanggal_bimbingan DESC", (user_id,))
        logbook_list = cursor.fetchall()
    conn.close()

    return templates.TemplateResponse(
        request=request, 
        name='mahasiswa_ta_logbook.html', 
        context={'logbook': logbook_list}
    )

@app.post('/mahasiswa/ta/logbook')
async def mahasiswa_ta_logbook_post(
    request: Request,
    tanggal_bimbingan: str = Form(...),
    topik_pembahasan: str = Form(...),
    file_progress: UploadFile = File(None)
):
    if request.session.get('role') != 'mahasiswa':
        return RedirectResponse(url='/login', status_code=303)
        
    user_id = request.session['user_id']
    filename = None
    if file_progress and file_progress.filename:
        filename = secure_filename(file_progress.filename)
        file_path = os.path.join(UPLOAD_LOGBOOK, filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file_progress.read())

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO logbook_ta (id_mahasiswa, tanggal_bimbingan, topik_pembahasan, file_progress, status_acc)
            VALUES (%s, %s, %s, %s, 'pending')
        """, (user_id, tanggal_bimbingan, topik_pembahasan, filename))
        conn.commit()
    conn.close()

    flash(request, "Catatan bimbingan TA berhasil dikirim!", "success")
    return RedirectResponse(url='/mahasiswa/ta/logbook', status_code=303)


# --- DASHBOARD & FITUR DOSEN ---

@app.get('/dashboard/dosen', name='dashboard_dosen')
async def dashboard_dosen(request: Request):
    if request.session.get('role') != 'dosen':
        return RedirectResponse(url='/login', status_code=303)

    user_id = request.session['user_id']
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

    return templates.TemplateResponse(
        request=request, 
        name='dashboard_dosen.html', 
        context={
            'dosen': data_dosen, 
            'pengajuan': pengajuan_masuk, 
            'bimbingan': mahasiswa_bimbingan
        }
    )

@app.get('/dosen/pengajuan/{id_pengajuan}/{aksi}', name='dosen_aksi_pengajuan')
async def dosen_aksi_pengajuan(request: Request, id_pengajuan: int, aksi: str):
    if request.session.get('role') != 'dosen':
        return RedirectResponse(url='/login', status_code=303)

    user_id = request.session['user_id']
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM dosen WHERE id_dosen = %s", (user_id,))
        data_dosen = cursor.fetchone()

        cursor.execute("SELECT * FROM pengajuan_pembimbing WHERE id_pengajuan = %s", (id_pengajuan,))
        pengajuan = cursor.fetchone()

        if not pengajuan:
            flash(request, "Data pengajuan tidak ditemukan!", "danger")
            conn.close()
            return RedirectResponse(url='/dashboard/dosen', status_code=303)

        # Gunakan int() untuk memastikan perbandingan Integer == Integer
        is_p1 = (int(pengajuan['id_dosen_p1']) == int(user_id))

        if aksi == 'terima':
            if data_dosen['kuota_terpakai'] >= data_dosen['max_kuota']:
                flash(request, "Gagal menerima! Kuota bimbingan Anda sudah penuh.", "danger")
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

                flash(request, "Pengajuan bimbingan berhasil disetujui!", "success")

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

            flash(request, "Pengajuan bimbingan telah ditolak.", "warning")

        conn.commit()
    conn.close()

    return RedirectResponse(url='/dashboard/dosen', status_code=303)

@app.get('/dosen/logbook', name='dosen_logbook')
async def dosen_logbook(request: Request):
    if request.session.get('role') != 'dosen':
        return RedirectResponse(url='/login', status_code=303)

    user_id = request.session['user_id']
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

    return templates.TemplateResponse(
        request=request, 
        name='dosen_logbook.html', 
        context={'logbook': daftar_logbook}
    )

@app.get('/dosen/logbook/{id_logbook}/{aksi}', name='dosen_aksi_logbook')
async def dosen_aksi_logbook(request: Request, id_logbook: int, aksi: str):
    if request.session.get('role') != 'dosen':
        return RedirectResponse(url='/login', status_code=303)

    status_val = 'approved' if aksi == 'acc' else 'rejected'
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("UPDATE logbook SET status_acc = %s WHERE id_logbook = %s", (status_val, id_logbook))
        conn.commit()
    conn.close()

    flash(request, f"Status logbook berhasil diubah menjadi {status_val}.", "success")
    return RedirectResponse(url='/dosen/logbook', status_code=303)

# 1. RUTE GET: Untuk membuka/menampilkan halaman jadwal menguji
@app.get('/dosen/jadwal_menguji', name='dosen_jadwal_menguji')
async def dosen_jadwal_menguji_get(request: Request):
    if request.session.get('role') != 'dosen':
        return RedirectResponse(url='/login', status_code=303)
        
    user_id = request.session['user_id']
    conn = get_db_connection()
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

    return templates.TemplateResponse(
        request=request, 
        name='dosen_jadwal_menguji.html', 
        context={'jadwal': jadwal_menguji}
    )

# 2. RUTE POST: Untuk memproses form input/edit nilai akhir dari modal
@app.post('/dosen/jadwal_menguji', name='dosen_jadwal_menguji_post')
async def dosen_jadwal_menguji_post(
    request: Request,
    id_sidang: int = Form(...),
    nilai_akhir: str = Form(...),
    catatan_revisi: str = Form(...)
):
    if request.session.get('role') != 'dosen':
        return RedirectResponse(url='/login', status_code=303)
        
    user_id = request.session['user_id']
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE pendaftaran_sidang 
            SET nilai_akhir = %s, catatan_revisi = %s 
            WHERE id_sidang = %s AND id_penguji = %s
        """, (nilai_akhir, catatan_revisi, id_sidang, user_id))
        conn.commit()
    conn.close()

    flash(request, "Nilai dan catatan revisi berhasil disimpan!", "success")
    return RedirectResponse(url='/dosen/jadwal_menguji', status_code=303)

@app.get('/dosen/ta', name='dosen_ta')
async def dosen_ta(request: Request):
    if request.session.get('role') != 'dosen':
        return RedirectResponse(url='/login', status_code=303)
        
    user_id = request.session['user_id']
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

    return templates.TemplateResponse(
        request=request, 
        name='dosen_ta.html', 
        context={'pengajuan_ta': pengajuan_ta, 'user_id': user_id}
    )

@app.get('/dosen/ta/{id_pengajuan}/{aksi}', name='dosen_aksi_ta_pengajuan')
async def dosen_aksi_ta_pengajuan(request: Request, id_pengajuan: int, aksi: str):
    if request.session.get('role') != 'dosen':
        return RedirectResponse(url='/login', status_code=303)
        
    user_id = request.session['user_id']
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM pengajuan_ta WHERE id_pengajuan = %s", (id_pengajuan,))
        p = cursor.fetchone()
        
        if p:
            aktif = p['pilihan_aktif']
            if aksi == 'terima':
                cursor.execute("UPDATE pengajuan_ta SET status_final = 'accepted' WHERE id_pengajuan = %s", (id_pengajuan,))
                flash(request, "Pengajuan Tugas Akhir berhasil diterima!", "success")
            else:
                if aktif == 1 and p['id_dosen_p1'] == user_id:
                    cursor.execute("""
                        UPDATE pengajuan_ta 
                        SET status_p1 = 'rejected', pilihan_aktif = 2, status_p2 = 'pending' 
                        WHERE id_pengajuan = %s
                    """, (id_pengajuan,))
                    flash(request, "Pengajuan ditolak dan otomatis diteruskan ke Dosen Pilihan ke-2.", "warning")
                elif aktif == 2 and p['id_dosen_p2'] == user_id:
                    cursor.execute("""
                        UPDATE pengajuan_ta 
                        SET status_p2 = 'rejected', pilihan_aktif = 3, status_p3 = 'pending' 
                        WHERE id_pengajuan = %s
                    """, (id_pengajuan,))
                    flash(request, "Pengajuan ditolak dan otomatis diteruskan ke Dosen Pilihan ke-3.", "warning")
                elif aktif == 3 and p['id_dosen_p3'] == user_id:
                    cursor.execute("""
                        UPDATE pengajuan_ta 
                        SET status_p3 = 'rejected', status_final = 'rejected' 
                        WHERE id_pengajuan = %s
                    """, (id_pengajuan,))
                    flash(request, "Pengajuan ditolak oleh seluruh pilihan dosen.", "danger")
            conn.commit()
    conn.close()

    return RedirectResponse(url='/dosen/ta', status_code=303)

@app.get('/dosen/ta/logbook', name='dosen_ta_logbook')
async def dosen_ta_logbook(request: Request):
    if request.session.get('role') != 'dosen':
        return RedirectResponse(url='/login', status_code=303)
        
    user_id = request.session['user_id']
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

    return templates.TemplateResponse(
        request=request, 
        name='dosen_ta_logbook.html', 
        context={'logbook': logbook_ta}
    )

@app.get('/dosen/ta/logbook/{id_logbook}/acc', name='dosen_ta_logbook_acc')
async def dosen_ta_logbook_acc(request: Request, id_logbook: int):
    if request.session.get('role') != 'dosen':
        return RedirectResponse(url='/login', status_code=303)
        
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("UPDATE logbook_ta SET status_acc = 'approved' WHERE id_logbook = %s", (id_logbook,))
        conn.commit()
    conn.close()

    flash(request, "Logbook TA berhasil disetujui!", "success")
    return RedirectResponse(url='/dosen/ta/logbook', status_code=303)


# --- DASHBOARD & FITUR ADMIN & KAPRODI ---

@app.get('/dashboard/admin', name='dashboard_admin')
async def dashboard_admin(request: Request):
    if request.session.get('role') != 'admin':
        return RedirectResponse(url='/login', status_code=303)

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

    return templates.TemplateResponse(
        request=request, 
        name='dashboard_admin.html', 
        context={'pendaftaran': daftar_sidang, 'dosen': daftar_dosen}
    )

@app.post('/admin/verifikasi_sidang', name='admin_verifikasi_sidang')
async def admin_verifikasi_sidang(
    request: Request,
    id_sidang: int = Form(...),
    aksi: str = Form(...),
    tanggal_sidang: str = Form(None),
    waktu_sidang: str = Form(None),
    ruangan: str = Form(None),
    id_penguji: int = Form(None),
    catatan_admin: str = Form(None)
):
    if request.session.get('role') != 'admin':
        return RedirectResponse(url='/login', status_code=303)

    conn = get_db_connection()
    with conn.cursor() as cursor:
        if aksi == 'terima':
            cursor.execute("""
                UPDATE pendaftaran_sidang 
                SET status_verifikasi = 'verified', tanggal_sidang = %s, waktu_sidang = %s, ruangan = %s, id_penguji = %s
                WHERE id_sidang = %s
            """, (tanggal_sidang, waktu_sidang, ruangan, id_penguji, id_sidang))
            flash(request, "Berkas disetujui dan jadwal sidang berhasil diplot!", "success")
        elif aksi == 'tolak':
            cursor.execute("""
                UPDATE pendaftaran_sidang 
                SET status_verifikasi = 'rejected', catatan_admin = %s
                WHERE id_sidang = %s
            """, (catatan_admin, id_sidang))
            flash(request, "Pendaftaran sidang ditolak.", "warning")
        conn.commit()
    conn.close()

    return RedirectResponse(url='/dashboard/admin', status_code=303)

@app.get('/dashboard/kaprodi', name='dashboard_kaprodi')
async def dashboard_kaprodi(request: Request):
    if request.session.get('role') != 'kaprodi':
        return RedirectResponse(url='/login', status_code=303)

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

    return templates.TemplateResponse(
        request=request, 
        name='dashboard_kaprodi.html', 
        context={
            'stat': {'mhs': stat_mhs, 'lulus': stat_lulus}, 
            'beban_dosen': beban_dosen, 
            'rekap': rekap_nilai
        }
    )

@app.get('/admin/kuota_dosen', name='admin_kuota_dosen')
async def admin_kuota_dosen_get(request: Request):
    if request.session.get('role') != 'admin':
        return RedirectResponse(url='/login', status_code=303)

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT d.*, u.nama, u.username AS nidn 
            FROM dosen d 
            JOIN users u ON d.id_dosen = u.id
            ORDER BY u.nama ASC
        """)
        daftar_dosen = cursor.fetchall()
    conn.close()

    return templates.TemplateResponse(
        request=request, 
        name='admin_kuota_dosen.html', 
        context={'dosen': daftar_dosen}
    )

@app.post('/admin/kuota_dosen')
async def admin_kuota_dosen_post(request: Request, id_dosen: int = Form(...), max_kuota: int = Form(...)):
    if request.session.get('role') != 'admin':
        return RedirectResponse(url='/login', status_code=303)

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("UPDATE dosen SET max_kuota = %s WHERE id_dosen = %s", (max_kuota, id_dosen))
        conn.commit()
    conn.close()

    flash(request, "Batas kuota dosen berhasil diperbarui!", "success")
    return RedirectResponse(url='/admin/kuota_dosen', status_code=303)

@app.get('/admin/mahasiswa', name='admin_mahasiswa')
async def admin_mahasiswa(request: Request):
    if request.session.get('role') != 'admin':
        return RedirectResponse(url='/login', status_code=303)

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

    return templates.TemplateResponse(
        request=request, 
        name='admin_mahasiswa.html', 
        context={'mahasiswa': daftar_mahasiswa}
    )

@app.get('/admin/akun', name='admin_akun')
async def admin_akun_get(request: Request):
    if request.session.get('role') != 'admin':
        return RedirectResponse(url='/login', status_code=303)

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, nama, username, role FROM users ORDER BY role ASC, nama ASC")
        users = cursor.fetchall()
    conn.close()

    return templates.TemplateResponse(
        request=request, 
        name='admin_akun.html', 
        context={'users': users}
    )

@app.post('/admin/akun/tambah', name='admin_tambah_akun')
async def admin_tambah_akun(
    request: Request,
    nama: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...)
):
    if request.session.get('role') != 'admin':
        return RedirectResponse(url='/login', status_code=303)

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
        flash(request, "Akun baru berhasil ditambahkan!", "success")
    except Exception as e:
        flash(request, f"Gagal menambahkan akun: {e}", "danger")
    finally:
        conn.close()

    return RedirectResponse(url='/admin/akun', status_code=303)

@app.post('/admin/akun/edit/{id_user}', name='admin_edit_akun')
async def admin_edit_akun(
    request: Request,
    id_user: int,
    nama: str = Form(...),
    username: str = Form(...),
    role: str = Form(...),
    password: str = Form(None)
):
    if request.session.get('role') != 'admin':
        return RedirectResponse(url='/login', status_code=303)

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

    flash(request, "Data akun berhasil diperbarui!", "success")
    return RedirectResponse(url='/admin/akun', status_code=303)

@app.get('/admin/akun/hapus/{id_user}', name='admin_hapus_akun')
async def admin_hapus_akun(request: Request, id_user: int):
    if request.session.get('role') != 'admin':
        return RedirectResponse(url='/login', status_code=303)

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM dosen WHERE id_dosen = %s", (id_user,))
        cursor.execute("DELETE FROM users WHERE id = %s", (id_user,))
        conn.commit()
    conn.close()

    flash(request, "Akun berhasil dihapus dari sistem.", "success")
    return RedirectResponse(url='/admin/akun', status_code=303)

# --- ROUTE PROFIL PENGGUNA (MULTI-ROLE) ---

# ==========================================
# 1. RUTE MENAMPILKAN HALAMAN PROFIL (GET /profil)
# ==========================================
@app.get('/profil', name='profil_get')
async def profil_get(request: Request):
    if 'user_id' not in request.session:
        return RedirectResponse(url='/login', status_code=303)
        
    user_id = request.session['user_id']
    role = request.session.get('role', 'mahasiswa')
    
    conn = get_db_connection()
    user = None
    pengajuan_kp = None
    pengajuan_ta = None
    dosen_info = None

    try:
        with conn.cursor() as cursor:
            # 1. Ambil data user
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()

            if role == 'mahasiswa':
                # 2. Ambil data KP secara aman
                try:
                    cursor.execute("""
                        SELECT p.*, d1.nama AS nama_dosen_p1, d2.nama AS nama_dosen_p2 
                        FROM pengajuan_kp p
                        LEFT JOIN dosen d1 ON p.id_dosen_p1 = d1.id_dosen
                        LEFT JOIN dosen d2 ON p.id_dosen_p2 = d2.id_dosen
                        WHERE p.id_mahasiswa = %s
                    """, (user_id,))
                    pengajuan_kp = cursor.fetchone()
                except Exception:
                    # Jika tabel pengajuan_kp belum ada / nama beda, bypass tanpa melempar error
                    pengajuan_kp = None

                # 3. Ambil data TA secara aman
                try:
                    cursor.execute("""
                        SELECT t.*, d1.nama AS nama_dosen_p1, d2.nama AS nama_dosen_p2 
                        FROM pengajuan_ta t
                        LEFT JOIN dosen d1 ON t.id_dosen_p1 = d1.id_dosen
                        LEFT JOIN dosen d2 ON t.id_dosen_p2 = d2.id_dosen
                        WHERE t.id_mahasiswa = %s
                    """, (user_id,))
                    pengajuan_ta = cursor.fetchone()
                except Exception:
                    pengajuan_ta = None

            elif role == 'dosen':
                try:
                    cursor.execute("SELECT * FROM dosen WHERE id_dosen = %s", (user_id,))
                    dosen_info = cursor.fetchone()
                except Exception:
                    dosen_info = None

    except Exception as e:
        flash(request, f"Gagal memuat data profil: {e}", "danger")
    finally:
        conn.close()

    # Fallback jika user tidak ditemukan di DB
    if not user:
        user = {
            'id': user_id,
            'username': request.session.get('username', 'user'),
            'nama': request.session.get('nama', 'Pengguna'),
            'role': role,
            'email': '',
            'no_hp': '',
            'foto_profil': None
        }

    return templates.TemplateResponse(
        request=request, 
        name='profil.html', 
        context={
            'user': user,
            'pengajuan_kp': pengajuan_kp,
            'pengajuan_ta': pengajuan_ta,
            'dosen_info': dosen_info
        }
    )


# ==========================================
# 2. RUTE UPLOAD FOTO PROFIL (POST)
# ==========================================
@app.post('/profil/upload-foto')
async def profil_upload_foto(
    request: Request,
    foto_profil: UploadFile = File(...)
):
    if 'user_id' not in request.session:
        return RedirectResponse(url='/login', status_code=303)
        
    user_id = request.session['user_id']
    
    if foto_profil and foto_profil.filename:
        ext = foto_profil.filename.rsplit('.', 1)[-1].lower()
        if ext in {'png', 'jpg', 'jpeg'}:
            filename_foto = secure_filename(f"user_{user_id}_profile.{ext}")
            file_path = os.path.join(UPLOAD_PROFIL, filename_foto)
            
            # Simpan file ke folder uploads/profil
            with open(file_path, "wb") as buffer:
                buffer.write(await foto_profil.read())
            
            # Update database
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET foto_profil = %s WHERE id = %s", (filename_foto, user_id))
                conn.commit()
            conn.close()
            
            flash(request, "Foto profil berhasil diperbarui!", "success")
        else:
            flash(request, "Format file tidak didukung! Ganti ke JPG/PNG.", "danger")
            
    return RedirectResponse(url='/profil', status_code=303)


# ==========================================
# 3. RUTE UPDATE BIODATA TAB 1 (POST)
# ==========================================
@app.post('/profil/update-biodata')
async def profil_update_biodata(
    request: Request,
    nama: str = Form(...),
    email: str = Form(None),
    no_hp: str = Form(None),
    alamat: str = Form(None)
):
    if 'user_id' not in request.session:
        return RedirectResponse(url='/login', status_code=303)
        
    user_id = request.session['user_id']
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE users SET nama = %s, email = %s, no_hp = %s, alamat = %s WHERE id = %s
            """, (nama, email, no_hp, alamat, user_id))
            conn.commit()
            
        request.session['nama'] = nama
        flash(request, "Biodata berhasil diperbarui!", "success")
    except Exception as e:
        flash(request, f"Gagal memperbarui biodata: {e}", "danger")
    finally:
        conn.close()
        
    return RedirectResponse(url='/profil', status_code=303)


# ==========================================
# 4. RUTE UPDATE PASSWORD TAB 3 (POST)
# ==========================================
@app.post('/profil/update-password')
async def profil_update_password(
    request: Request,
    password_lama: str = Form(...),
    password_baru: str = Form(...),
    confirm_password: str = Form(...)
):
    if 'user_id' not in request.session:
        return RedirectResponse(url='/login', status_code=303)
        
    user_id = request.session['user_id']
    
    if password_baru != confirm_password:
        flash(request, "Konfirmasi password baru tidak cocok!", "danger")
        return RedirectResponse(url='/profil', status_code=303)
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT password FROM users WHERE id = %s", (user_id,))
            user_db = cursor.fetchone()
            
            if user_db and check_password_hash(user_db['password'], password_lama):
                hashed_new = generate_password_hash(password_baru)
                cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_new, user_id))
                conn.commit()
                flash(request, "Password berhasil diubah!", "success")
            else:
                flash(request, "Password lama yang Anda masukkan salah!", "danger")
    except Exception as e:
        flash(request, f"Gagal mengubah password: {e}", "danger")
    finally:
        conn.close()
        
    return RedirectResponse(url='/profil', status_code=303)


# --- JALANKAN SERVER ---
if __name__ == '__main__':
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)