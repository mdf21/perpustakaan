import os
from datetime import datetime, timedelta, date
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import or_, and_, func
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///perpustakaan.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True
}
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'perpustakaan-secret-key-change-in-production')

CORS(app, resources={r"/api/*": {"origins": os.getenv('CORS_ORIGINS', '*')}}, supports_credentials=True)

db = SQLAlchemy(app)

BUKU_DIKEMBALIKAN = 'Dikembalikan'
BUKU_DIPINJAM = 'Dipinjam'
BUKU_TERLAMBAT = 'Terlambat'

# Fine configuration
DENDA_PER_HARI = 1000
MAX_PINJAM_PER_ANGGOTA = 3

@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Data tidak ditemukan'}), 404
    return render_template('dashboard.html', current_date=datetime.now().strftime('%d %B %Y')), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Terjadi kesalahan server'}), 500
    return render_template('dashboard.html', current_date=datetime.now().strftime('%d %B %Y')), 500

# ===== DATABASE MODELS =====
class User(db.Model):
    """Users table for authentication (Petugas/Admin/Anggota)"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nama = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), default='anggota')  # admin, petugas, anggota
    status = db.Column(db.String(20), default='aktif')  # aktif, nonaktif
    anggota_id = db.Column(db.Integer, db.ForeignKey('anggota.id'), nullable=True)  # Link to anggota if role is anggota
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'nama': self.nama,
            'role': self.role,
            'status': self.status,
            'anggota_id': self.anggota_id
        }

class Rak(db.Model):
    """Rak/Lokasi buku dengan kategori DDC"""
    __tablename__ = 'raks'
    id = db.Column(db.Integer, primary_key=True)
    nama_rak = db.Column(db.String(100), nullable=False)
    kategori_ddc = db.Column(db.String(100))  # Dewey Decimal Classification
    deskripsi = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    buku = db.relationship('Buku', backref='rak', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'nama_rak': self.nama_rak,
            'kategori_ddc': self.kategori_ddc,
            'deskripsi': self.deskripsi
        }

class Buku(db.Model):
    __tablename__ = 'buku'
    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(20), unique=True)
    judul = db.Column(db.String(200), nullable=False)
    pengarang = db.Column(db.String(150), nullable=False)
    penerbit = db.Column(db.String(150))
    tahun_terbit = db.Column(db.Integer)
    stok_total = db.Column(db.Integer, default=1)
    stok_tersedia = db.Column(db.Integer, default=1)
    rak_id = db.Column(db.Integer, db.ForeignKey('raks.id'))
    deskripsi = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transaksi = db.relationship('Transaksi', backref='buku', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'isbn': self.isbn,
            'judul': self.judul,
            'pengarang': self.pengarang,
            'penerbit': self.penerbit,
            'tahun_terbit': self.tahun_terbit,
            'stok_total': self.stok_total,
            'stok_tersedia': self.stok_tersedia,
            'rak_id': self.rak_id,
            'rak_nama': self.rak.nama_rak if self.rak else None,
            'kategori_ddc': self.rak.kategori_ddc if self.rak else None,
            'deskripsi': self.deskripsi
        }

class Anggota(db.Model):
    __tablename__ = 'anggota'
    id = db.Column(db.Integer, primary_key=True)
    nis = db.Column(db.String(50), unique=True, nullable=False)
    nama = db.Column(db.String(150), nullable=False)
    kelas = db.Column(db.String(50), nullable=False)
    jurusan = db.Column(db.String(100))
    jenis_kelamin = db.Column(db.String(20))
    no_telepon = db.Column(db.String(20))
    alamat = db.Column(db.Text)
    status = db.Column(db.String(20), default='Aktif')
    tanggal_bergabung = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transaksi = db.relationship('Transaksi', backref='anggota', lazy=True)
    user = db.relationship('User', backref='anggota', uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'nis': self.nis,
            'nama': self.nama,
            'kelas': self.kelas,
            'jurusan': self.jurusan,
            'jenis_kelamin': self.jenis_kelamin,
            'no_telepon': self.no_telepon,
            'alamat': self.alamat,
            'status': self.status,
            'tanggal_bergabung': self.tanggal_bergabung.strftime('%d-%m-%Y') if self.tanggal_bergabung else ''
        }

class Transaksi(db.Model):
    __tablename__ = 'transaksi'
    id = db.Column(db.Integer, primary_key=True)
    buku_id = db.Column(db.Integer, db.ForeignKey('buku.id'), nullable=False)
    anggota_id = db.Column(db.Integer, db.ForeignKey('anggota.id'), nullable=False)
    tanggal_pinjam = db.Column(db.Date, nullable=False, default=date.today)
    tanggal_kembali_seharusnya = db.Column(db.Date, nullable=False)
    tanggal_dikembalikan = db.Column(db.Date)
    status = db.Column(db.String(50), default=BUKU_DIPINJAM)  # Dipinjam, Dikembalikan, Terlambat
    denda = db.Column(db.Integer, default=0)
    catatan = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    denda_record = db.relationship('Denda', backref='transaksi', uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'buku_id': self.buku_id,
            'anggota_id': self.anggota_id,
            'nama_anggota': self.anggota.nama if self.anggota else None,
            'nis_anggota': self.anggota.nis if self.anggota else None,
            'kelas_anggota': self.anggota.kelas if self.anggota else None,
            'judul_buku': self.buku.judul if self.buku else None,
            'kode_buku': self.buku.isbn if self.buku else None,
            'tanggal_pinjam': self.tanggal_pinjam.strftime('%d-%m-%Y') if self.tanggal_pinjam else None,
            'tanggal_kembali_seharusnya': self.tanggal_kembali_seharusnya.strftime('%d-%m-%Y') if self.tanggal_kembali_seharusnya else None,
            'tanggal_dikembalikan': self.tanggal_dikembalikan.strftime('%d-%m-%Y') if self.tanggal_dikembalikan else None,
            'status': self.status,
            'denda': self.denda,
            'catatan': self.catatan
        }

class Denda(db.Model):
    """Denda/Fines table"""
    __tablename__ = 'denda'
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('transaksi.id'), unique=True, nullable=False)
    jumlah_denda = db.Column(db.Integer, default=0)
    status_pembayaran = db.Column(db.String(20), default='belum')  # lunas, belum
    tanggal_denda = db.Column(db.Date, default=date.today)
    tanggal_bayar = db.Column(db.Date)
    catatan = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'loan_id': self.loan_id,
            'jumlah_denda': self.jumlah_denda,
            'status_pembayaran': self.status_pembayaran,
            'tanggal_denda': self.tanggal_denda.strftime('%d-%m-%Y') if self.tanggal_denda else None,
            'tanggal_bayar': self.tanggal_bayar.strftime('%d-%m-%Y') if self.tanggal_bayar else None,
            'catatan': self.catatan
        }

# ===== AUTHENTICATION DECORATORS =====
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Login required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'message': 'Login required'}), 401
                return redirect(url_for('login'))
            user = User.query.get(session['user_id'])
            if not user or user.role not in roles:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'message': 'Access denied'}), 403
                return render_template('dashboard.html', current_date=datetime.now().strftime('%d %B %Y')), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# ===== AUTH ROUTES =====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.status == 'aktif':
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_name'] = user.nama
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Login berhasil', 'user': user.to_dict()})
            return redirect(url_for('index'))
        
        if request.is_json:
            return jsonify({'success': False, 'message': 'Username/password salah atau akun tidak aktif'}), 401
        return render_template('login.html', error='Username/password salah atau akun tidak aktif')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/auth/me')
@login_required
def auth_me():
    user = get_current_user()
    return jsonify({'success': True, 'user': user.to_dict() if user else None})

# ===== DEFAULT ROUTES =====
@app.route('/')
@login_required
def index():
    return render_template('dashboard.html', current_date=datetime.now().strftime('%d %B %Y'), user=get_current_user())

@app.route('/buku')
@login_required
def buku_page():
    return render_template('books.html', current_date=datetime.now().strftime('%d %B %Y'), user=get_current_user())

@app.route('/anggota')
@login_required
def anggota_page():
    return render_template('members.html', current_date=datetime.now().strftime('%d %B %Y'), user=get_current_user())

@app.route('/transaksi')
@login_required
def transaksi_page():
    return render_template('transactions.html', current_date=datetime.now().strftime('%d %B %Y'), user=get_current_user())

@app.route('/laporan')
@login_required
def laporan_page():
    return render_template('reports.html', current_date=datetime.now().strftime('%d %B %Y'), user=get_current_user())

# ===== OPAC (Public Catalog - No Login Required) =====
@app.route('/opac')
def opac_page():
    return render_template('opac.html', current_date=datetime.now().strftime('%d %B %Y'))

@app.route('/api/opac/buku', methods=['GET'])
def opac_get_buku():
    """Public catalog search - no login required"""
    search = request.args.get('search', '')
    kategori = request.args.get('kategori', '')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 12, type=int), 50)

    query = Buku.query.filter(Buku.stok_tersedia > 0)
    if search:
        query = query.filter(or_(
            Buku.judul.contains(search),
            Buku.pengarang.contains(search),
            Buku.isbn.contains(search)
        ))
    if kategori:
        query = query.join(Rak).filter(Rak.kategori_ddc == kategori)

    pagination = query.order_by(Buku.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    books = pagination.items
    result = []
    for b in books:
        result.append(b.to_dict())
    return jsonify({
        'books': result,
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page
    })

@app.route('/api/opac/kategori', methods=['GET'])
def opac_get_kategori():
    """Get categories for OPAC filter"""
    categories = db.session.query(Rak.kategori_ddc).filter(
        Rak.kategori_ddc != None,
        Rak.kategori_ddc != ''
    ).distinct().all()
    return jsonify([c[0] for c in categories])

# ===== DASHBOARD =====
@app.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    total_buku = Buku.query.count()
    total_anggota = Anggota.query.count()
    total_transaksi = Transaksi.query.count()
    sedang_dipinjam = Transaksi.query.filter(Transaksi.status == BUKU_DIPINJAM).count()
    terlambat = Transaksi.query.filter(and_(
        Transaksi.status == BUKU_DIPINJAM,
        Transaksi.tanggal_kembali_seharusnya < date.today()
    )).count()
    total_denda = db.session.query(db.func.sum(Transaksi.denda)).filter(
        Transaksi.status.in_([BUKU_DIKEMBALIKAN, BUKU_TERLAMBAT])
    ).scalar() or 0

    recent_transactions = Transaksi.query.order_by(Transaksi.created_at.desc()).limit(10).all()
    recent_data = []
    for t in recent_transactions:
        recent_data.append(t.to_dict())

    return jsonify({
        'total_buku': total_buku,
        'total_anggota': total_anggota,
        'total_transaksi': total_transaksi,
        'sedang_dipinjam': sedang_dipinjam,
        'terlambat': terlambat,
        'total_denda': int(total_denda),
        'recent_transactions': recent_data
    })

# ===== BUKU CRUD =====
@app.route('/api/buku', methods=['GET'])
@login_required
def get_buku():
    search = request.args.get('search', '')
    kategori = request.args.get('kategori', '')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    query = Buku.query
    if search:
        query = query.filter(or_(
            Buku.judul.contains(search),
            Buku.pengarang.contains(search),
            Buku.isbn.contains(search)
        ))
    if kategori:
        query = query.join(Rak).filter(Rak.kategori_ddc == kategori)

    pagination = query.order_by(Buku.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    books = pagination.items
    result = []
    for b in books:
        result.append(b.to_dict())
    return jsonify({
        'books': result,
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page
    })

@app.route('/api/buku', methods=['POST'])
@role_required('admin', 'petugas')
def create_buku():
    data = request.json
    if not data or not data.get('isbn') or not data.get('judul') or not data.get('pengarang'):
        return jsonify({'success': False, 'message': 'ISBN, judul, dan pengarang wajib diisi'}), 400
    buku = Buku(
        isbn=data.get('isbn'),
        judul=data.get('judul'),
        pengarang=data.get('pengarang'),
        penerbit=data.get('penerbit'),
        tahun_terbit=data.get('tahun_terbit'),
        stok_total=data.get('stok_total', 1),
        stok_tersedia=data.get('stok_tersedia', 1),
        rak_id=data.get('rak_id'),
        deskripsi=data.get('deskripsi')
    )
    db.session.add(buku)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Buku berhasil ditambahkan', 'id': buku.id})

@app.route('/api/buku/<int:id>', methods=['PUT'])
@role_required('admin', 'petugas')
def update_buku(id):
    b = Buku.query.get_or_404(id)
    data = request.json
    if not data or not data.get('isbn') or not data.get('judul') or not data.get('pengarang'):
        return jsonify({'success': False, 'message': 'ISBN, judul, dan pengarang wajib diisi'}), 400
    b.isbn = data.get('isbn', b.isbn)
    b.judul = data.get('judul', b.judul)
    b.pengarang = data.get('pengarang', b.pengarang)
    b.penerbit = data.get('penerbit', b.penerbit)
    b.tahun_terbit = data.get('tahun_terbit', b.tahun_terbit)
    b.stok_total = data.get('stok_total', b.stok_total)
    b.stok_tersedia = data.get('stok_tersedia', b.stok_tersedia)
    b.rak_id = data.get('rak_id', b.rak_id)
    b.deskripsi = data.get('deskripsi', b.deskripsi)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Buku berhasil diperbarui'})

@app.route('/api/buku/<int:id>', methods=['DELETE'])
@role_required('admin')
def delete_buku(id):
    b = Buku.query.get_or_404(id)
    has_transactions = Transaksi.query.filter_by(buku_id=id).first() is not None
    if has_transactions:
        return jsonify({'success': False, 'message': 'Tidak dapat menghapus buku yang memiliki riwayat transaksi'})
    db.session.delete(b)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Buku berhasil dihapus'})

# ===== RAK CRUD =====
@app.route('/api/raks', methods=['GET'])
@login_required
def get_raks():
    raks = Rak.query.order_by(Rak.nama_rak).all()
    return jsonify([r.to_dict() for r in raks])

@app.route('/api/raks', methods=['POST'])
@role_required('admin', 'petugas')
def create_rak():
    data = request.json
    if not data or not data.get('nama_rak'):
        return jsonify({'success': False, 'message': 'Nama rak wajib diisi'}), 400
    rak = Rak(
        nama_rak=data.get('nama_rak'),
        kategori_ddc=data.get('kategori_ddc'),
        deskripsi=data.get('deskripsi')
    )
    db.session.add(rak)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Rak berhasil ditambahkan', 'id': rak.id})

@app.route('/api/raks/<int:id>', methods=['PUT'])
@role_required('admin', 'petugas')
def update_rak(id):
    r = Rak.query.get_or_404(id)
    data = request.json
    if not data or not data.get('nama_rak'):
        return jsonify({'success': False, 'message': 'Nama rak wajib diisi'}), 400
    r.nama_rak = data.get('nama_rak', r.nama_rak)
    r.kategori_ddc = data.get('kategori_ddc', r.kategori_ddc)
    r.deskripsi = data.get('deskripsi', r.deskripsi)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Rak berhasil diperbarui'})

@app.route('/api/raks/<int:id>', methods=['DELETE'])
@role_required('admin')
def delete_rak(id):
    r = Rak.query.get_or_404(id)
    has_books = Buku.query.filter_by(rak_id=id).first() is not None
    if has_books:
        return jsonify({'success': False, 'message': 'Tidak dapat menghapus rak yang masih memiliki buku'})
    db.session.delete(r)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Rak berhasil dihapus'})

# ===== ANGGOTA CRUD =====
@app.route('/api/anggota', methods=['GET'])
@login_required
def get_anggota():
    search = request.args.get('search', '')
    kelas = request.args.get('kelas', '')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    query = Anggota.query
    if search:
        query = query.filter(or_(
            Anggota.nama.contains(search),
            Anggota.nis.contains(search),
            Anggota.kelas.contains(search)
        ))
    if kelas:
        query = query.filter(Anggota.kelas == kelas)

    pagination = query.order_by(Anggota.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    members = pagination.items
    result = []
    for a in members:
        result.append(a.to_dict())
    return jsonify({
        'anggota': result,
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page
    })

@app.route('/api/anggota', methods=['POST'])
@role_required('admin', 'petugas')
def create_anggota():
    data = request.json
    if not data or not data.get('nis') or not data.get('nama') or not data.get('kelas'):
        return jsonify({'success': False, 'message': 'NIS, nama, dan kelas wajib diisi'}), 400
    anggota = Anggota(
        nis=data.get('nis'),
        nama=data.get('nama'),
        kelas=data.get('kelas'),
        jurusan=data.get('jurusan'),
        jenis_kelamin=data.get('jenis_kelamin'),
        no_telepon=data.get('no_telepon'),
        alamat=data.get('alamat'),
        status=data.get('status', 'Aktif')
    )
    db.session.add(anggota)
    db.session.commit()
    
    # Auto-create user account for anggota
    user = User(
        username=data.get('nis'),
        nama=data.get('nama'),
        role='anggota',
        status='aktif',
        anggota_id=anggota.id
    )
    user.set_password(data.get('nis'))  # Default password is NIS
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Anggota berhasil ditambahkan', 'id': anggota.id})

@app.route('/api/anggota/<int:id>', methods=['PUT'])
@role_required('admin', 'petugas')
def update_anggota(id):
    a = Anggota.query.get_or_404(id)
    data = request.json
    if not data or not data.get('nis') or not data.get('nama') or not data.get('kelas'):
        return jsonify({'success': False, 'message': 'NIS, nama, dan kelas wajib diisi'}), 400
    a.nis = data.get('nis', a.nis)
    a.nama = data.get('nama', a.nama)
    a.kelas = data.get('kelas', a.kelas)
    a.jurusan = data.get('jurusan', a.jurusan)
    a.jenis_kelamin = data.get('jenis_kelamin', a.jenis_kelamin)
    a.no_telepon = data.get('no_telepon', a.no_telepon)
    a.alamat = data.get('alamat', a.alamat)
    a.status = data.get('status', a.status)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Anggota berhasil diperbarui'})

@app.route('/api/anggota/<int:id>', methods=['DELETE'])
@role_required('admin')
def delete_anggota(id):
    a = Anggota.query.get_or_404(id)
    has_transactions = Transaksi.query.filter_by(anggota_id=id).first() is not None
    if has_transactions:
        return jsonify({'success': False, 'message': 'Tidak dapat menghapus anggota yang memiliki riwayat transaksi'})
    # Delete associated user if exists
    user = User.query.filter_by(anggota_id=id).first()
    if user:
        db.session.delete(user)
    db.session.delete(a)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Anggota berhasil dihapus'})

@app.route('/api/kelas', methods=['GET'])
@login_required
def get_kelas():
    classes = db.session.query(Anggota.kelas).filter(
        Anggota.kelas != None,
        Anggota.kelas != ''
    ).distinct().all()
    return jsonify([c[0] for c in classes])

# ===== TRANSAKSI CRUD =====
@app.route('/api/transaksi', methods=['GET'])
@login_required
def get_transaksi():
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    query = Transaksi.query
    if status_filter:
        query = query.filter(Transaksi.status == status_filter)
    if search:
        query = query.join(Anggota).join(Buku).filter(or_(
            Anggota.nama.contains(search),
            Anggota.nis.contains(search),
            Buku.judul.contains(search)
        ))

    pagination = query.order_by(Transaksi.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    transactions = pagination.items
    result = []
    for t in transactions:
        result.append(t.to_dict())
    return jsonify({
        'transactions': result,
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page
    })

@app.route('/api/transaksi', methods=['POST'])
@role_required('admin', 'petugas')
def create_transaksi():
    data = request.json
    if not data or not data.get('buku_id') or not data.get('anggota_id'):
        return jsonify({'success': False, 'message': 'Buku dan anggota wajib dipilih'}), 400
    buku = Buku.query.get(data.get('buku_id'))
    if not buku or buku.stok_tersedia < 1:
        return jsonify({'success': False, 'message': 'Stok buku tidak tersedia'})
    anggota = Anggota.query.get(data.get('anggota_id'))
    if not anggota or anggota.status == 'Nonaktif':
        return jsonify({'success': False, 'message': 'Anggota tidak aktif'})
    
    # Check for overdue loans
    overdue_loans = Transaksi.query.filter(
        and_(Transaksi.anggota_id == anggota.id, Transaksi.status == BUKU_TERLAMBAT)
    ).count()
    if overdue_loans > 0:
        return jsonify({'success': False, 'message': 'Anggota memiliki buku yang terlambat dikembalikan'})
    
    # Check max quota
    active_borrows = Transaksi.query.filter(
        and_(Transaksi.anggota_id == anggota.id, Transaksi.status == BUKU_DIPINJAM)
    ).count()
    if active_borrows >= MAX_PINJAM_PER_ANGGOTA:
        return jsonify({'success': False, 'message': f'Maksimal {MAX_PINJAM_PER_ANGGOTA} buku yang dapat dipinjam'})

    tanggal_kembali_seharusnya = date.today() + timedelta(days=7)
    transaksi = Transaksi(
        buku_id=data.get('buku_id'),
        anggota_id=data.get('anggota_id'),
        tanggal_kembali_seharusnya=tanggal_kembali_seharusnya,
        catatan=data.get('catatan', '')
    )
    buku.stok_tersedia -= 1
    db.session.add(transaksi)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Transaksi berhasil', 'id': transaksi.id})

@app.route('/api/transaksi/<int:id>', methods=['PUT'])
@role_required('admin', 'petugas')
def update_transaksi(id):
    t = Transaksi.query.get_or_404(id)
    data = request.json
    if t.status in [BUKU_DIKEMBALIKAN, BUKU_TERLAMBAT]:
        return jsonify({'success': False, 'message': 'Transaksi sudah selesai'})
    action = data.get('action')
    if action == 'return':
        t.tanggal_dikembalikan = date.today()
        t.status = BUKU_DIKEMBALIKAN
        
        # Calculate fine if overdue
        denda_amount = 0
        if t.tanggal_dikembalikan > t.tanggal_kembali_seharusnya:
            t.status = BUKU_TERLAMBAT
            days_late = (t.tanggal_dikembalikan - t.tanggal_kembali_seharusnya).days
            denda_amount = days_late * DENDA_PER_HARI
            t.denda = denda_amount
            
            # Create denda record
            denda = Denda(
                loan_id=t.id,
                jumlah_denda=denda_amount,
                status_pembayaran='belum',
                tanggal_denda=date.today()
            )
            db.session.add(denda)
        
        t.buku.stok_tersedia += 1
        t.catatan = data.get('catatan', t.catatan)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Buku berhasil dikembalikan', 'denda': denda_amount})
    elif action == 'extend':
        extend_days = data.get('extend_days', 7)
        if not isinstance(extend_days, int) or extend_days < 1:
            return jsonify({'success': False, 'message': 'Jumlah hari perpanjangan tidak valid'}), 400
        t.tanggal_kembali_seharusnya = t.tanggal_kembali_seharusnya + timedelta(days=extend_days)
        t.catatan = data.get('catatan', t.catatan)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Transaksi berhasil diperpanjang'})
    return jsonify({'success': False, 'message': 'Aksi tidak dikenali'}), 400

@app.route('/api/transaksi/<int:id>', methods=['DELETE'])
@role_required('admin')
def delete_transaksi(id):
    t = Transaksi.query.get_or_404(id)
    if t.status == BUKU_DIPINJAM:
        t.buku.stok_tersedia += 1
    # Delete associated denda if exists
    denda = Denda.query.filter_by(loan_id=id).first()
    if denda:
        db.session.delete(denda)
    db.session.delete(t)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Transaksi berhasil dihapus'})

# ===== DENDA CRUD =====
@app.route('/api/denda', methods=['GET'])
@login_required
def get_denda():
    status = request.args.get('status', '')
    query = Denda.query.join(Transaksi).join(Anggota)
    if status:
        query = query.filter(Denda.status_pembayaran == status)
    denda_list = query.order_by(Denda.created_at.desc()).all()
    return jsonify([d.to_dict() for d in denda_list])

@app.route('/api/denda/<int:id>/bayar', methods=['PUT'])
@role_required('admin', 'petugas')
def bayar_denda(id):
    denda = Denda.query.get_or_404(id)
    if denda.status_pembayaran == 'lunas':
        return jsonify({'success': False, 'message': 'Denda sudah lunas'})
    denda.status_pembayaran = 'lunas'
    denda.tanggal_bayar = date.today()
    db.session.commit()
    return jsonify({'success': True, 'message': 'Denda berhasil dibayar', 'denda': denda.to_dict()})

# ===== DENDA CRUD =====
@app.route('/api/denda', methods=['GET'])
@login_required
def get_denda():
    status = request.args.get('status', '')
    query = Denda.query.join(Transaksi).join(Anggota)
    if status:
        query = query.filter(Denda.status_pembayaran == status)
    denda_list = query.order_by(Denda.created_at.desc()).all()
    return jsonify([d.to_dict() for d in denda_list])

@app.route('/api/denda/<int:id>/bayar', methods=['PUT'])
@role_required('admin', 'petugas')
def bayar_denda(id):
    denda = Denda.query.get_or_404(id)
    if denda.status_pembayaran == 'lunas':
        return jsonify({'success': False, 'message': 'Denda sudah lunas'})
    denda.status_pembayaran = 'lunas'
    denda.tanggal_bayar = date.today()
    db.session.commit()
    return jsonify({'success': True, 'message': 'Denda berhasil dibayar', 'denda': denda.to_dict()})

# ===== LAPORAN =====
@app.route('/api/laporan/ringkasan')
@login_required
def laporan_ringkasan():
    from sqlalchemy import func
    now = datetime.utcnow()
    month_start = date(now.year, now.month, 1)
    year_start = date(now.year, 1, 1)

    monthly_borrowed = Transaksi.query.filter(
        Transaksi.tanggal_pinjam >= month_start
    ).count()
    yearly_borrowed = Transaksi.query.filter(
        Transaksi.tanggal_pinjam >= year_start
    ).count()
    total_returned = Transaksi.query.filter(
        Transaksi.status.in_([BUKU_DIKEMBALIKAN, BUKU_TERLAMBAT])
    ).count()

    popular_books = db.session.query(
        Buku.judul, func.count(Transaksi.id).label('total')
    ).join(Transaksi).group_by(Buku.id).order_by(func.count(Transaksi.id).desc()).limit(5).all()

    top_members = db.session.query(
        Anggota.nama, func.count(Transaksi.id).label('total')
    ).join(Transaksi).group_by(Anggota.id).order_by(func.count(Transaksi.id).desc()).limit(5).all()

    category_stats = db.session.query(
        Rak.kategori_ddc, func.count(Buku.id).label('total')
    ).join(Buku, Buku.rak_id == Rak.id).group_by(Rak.kategori_ddc).all()

    return jsonify({
        'monthly_borrowed': monthly_borrowed,
        'yearly_borrowed': yearly_borrowed,
        'total_returned': total_returned,
        'popular_books': [{'judul': b[0], 'total': b[1]} for b in popular_books],
        'top_members': [{'nama': m[0], 'total': m[1]} for m in top_members],
        'category_stats': [{'kategori': c[0] or 'Tidak Berkategori', 'total': c[1]} for c in category_stats]
    })

@app.route('/api/laporan/transaksi')
@login_required
def laporan_transaksi():
    start_date = request.args.get('start', '')
    end_date = request.args.get('end', '')
    query = Transaksi.query
    if start_date:
        query = query.filter(Transaksi.tanggal_pinjam >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(Transaksi.tanggal_pinjam <= datetime.strptime(end_date, '%Y-%m-%d').date())
    transactions = query.order_by(Transaksi.tanggal_pinjam.desc()).all()
    result = []
    for t in transactions:
        result.append(t.to_dict())
    return jsonify(result)

@app.route('/api/laporan/denda')
@login_required
def laporan_denda():
    """Laporan denda"""
    start_date = request.args.get('start', '')
    end_date = request.args.get('end', '')
    query = Denda.query.join(Transaksi).join(Anggota)
    if start_date:
        query = query.filter(Denda.tanggal_denda >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(Denda.tanggal_denda <= datetime.strptime(end_date, '%Y-%m-%d').date())
    denda_list = query.order_by(Denda.tanggal_denda.desc()).all()
    
    total_denda = sum(d.jumlah_denda for d in denda_list)
    total_lunas = sum(d.jumlah_denda for d in denda_list if d.status_pembayaran == 'lunas')
    total_belum = total_denda - total_lunas
    
    result = []
    for d in denda_list:
        t = d.transaksi
        result.append({
            'id': d.id,
            'nama_anggota': t.anggota.nama if t.anggota else '-',
            'nis': t.anggota.nis if t.anggota else '-',
            'judul_buku': t.buku.judul if t.buku else '-',
            'tanggal_denda': d.tanggal_denda.strftime('%d-%m-%Y'),
            'jumlah_denda': d.jumlah_denda,
            'status_pembayaran': d.status_pembayaran,
            'tanggal_bayar': d.tanggal_bayar.strftime('%d-%m-%Y') if d.tanggal_bayar else '-'
        })
    
    return jsonify({
        'total_denda': total_denda,
        'total_lunas': total_lunas,
        'total_belum': total_belum,
        'denda_list': result
    })

# ===== WA GATEWAY INTEGRATION (Placeholder) =====
def send_wa_notification(phone_number, message):
    """
    Placeholder for WhatsApp Gateway integration.
    Replace with actual WA Gateway API (e.g., Fonnte, Wablas, etc.)
    """
    # TODO: Implement actual WA Gateway API call
    # Example:
    # import requests
    # response = requests.post(
    #     'https://api.fonnte.com/send',
    #     headers={'Authorization': 'YOUR_TOKEN'},
    #     data={'target': phone_number, 'message': message}
    # )
    # return response.json()
    
    print(f"[WA NOTIFICATION] To: {phone_number}, Message: {message}")
    return {'success': True, 'message': 'Notification queued (simulated)'}

@app.route('/api/wa/notify-return-reminder', methods=['POST'])
@role_required('admin', 'petugas')
def notify_return_reminder():
    """Send return reminder notifications for books due tomorrow"""
    tomorrow = date.today() + timedelta(days=1)
    due_transactions = Transaksi.query.filter(
        and_(
            Transaksi.status == BUKU_DIPINJAM,
            Transaksi.tanggal_kembali_seharusnya == tomorrow
        )
    ).all()
    
    results = []
    for t in due_transactions:
        if t.anggota and t.anggota.no_telepon:
            message = f"Halo {t.anggota.nama}, ini adalah pengingat bahwa buku '{t.buku.judul}' harus dikembalikan besok ({t.tanggal_kembali_seharusnya.strftime('%d-%m-%Y')}). Terima kasih."
            result = send_wa_notification(t.anggota.no_telepon, message)
            results.append({
                'anggota': t.anggota.nama,
                'buku': t.buku.judul,
                'phone': t.anggota.no_telepon,
                'result': result
            })
    
    return jsonify({'success': True, 'notifications_sent': len(results), 'details': results})

# ===== INIT DB =====
@app.cli.command("init-db")
def init_db_command():
    with app.app_context():
        db.create_all()
        # Create default admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', nama='Administrator', role='admin', status='aktif')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Default admin user created: admin/admin123")
    print("Database initialized successfully.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create default admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', nama='Administrator', role='admin', status='aktif')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Default admin user created: admin/admin123")
    app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true', host='0.0.0.0', port=5000)
