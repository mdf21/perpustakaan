import os
from datetime import datetime, timedelta, date
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import or_, and_

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///perpustakaan.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True
}

CORS(app, resources={r"/api/*": {"origins": os.getenv('CORS_ORIGINS', '*')}})

db = SQLAlchemy(app)

BUKU_DIKEMBALIKAN = 'Dikembalikan'
BUKU_DIPINJAM = 'Dipinjam'
BUKU_TERLAMBAT = 'Terlambat'

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

class Buku(db.Model):
    __tablename__ = 'buku'
    id = db.Column(db.Integer, primary_key=True)
    kode_buku = db.Column(db.String(50), unique=True, nullable=False)
    judul = db.Column(db.String(200), nullable=False)
    penulis = db.Column(db.String(150), nullable=False)
    penerbit = db.Column(db.String(150))
    tahun_terbit = db.Column(db.Integer)
    kategori = db.Column(db.String(100))
    isbn = db.Column(db.String(20))
    jumlah_halaman = db.Column(db.Integer)
    stok = db.Column(db.Integer, default=1)
    lokasi_rak = db.Column(db.String(50))
    deskripsi = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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

class Transaksi(db.Model):
    __tablename__ = 'transaksi'
    id = db.Column(db.Integer, primary_key=True)
    buku_id = db.Column(db.Integer, db.ForeignKey('buku.id'), nullable=False)
    anggota_id = db.Column(db.Integer, db.ForeignKey('anggota.id'), nullable=False)
    tanggal_pinjam = db.Column(db.Date, nullable=False, default=date.today)
    tanggal_jatuh_tempo = db.Column(db.Date, nullable=False)
    tanggal_kembali = db.Column(db.Date)
    status = db.Column(db.String(50), default=BUKU_DIPINJAM)
    denda = db.Column(db.Integer, default=0)
    catatan = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    buku = db.relationship('Buku', backref='transaksi_buku')
    anggota = db.relationship('Anggota', backref='transaksi_anggota')

@app.route('/')
def index():
    return render_template('dashboard.html', current_date=datetime.now().strftime('%d %B %Y'))

@app.route('/buku')
def buku_page():
    return render_template('books.html', current_date=datetime.now().strftime('%d %B %Y'))

@app.route('/anggota')
def anggota_page():
    return render_template('members.html', current_date=datetime.now().strftime('%d %B %Y'))

@app.route('/transaksi')
def transaksi_page():
    return render_template('transactions.html', current_date=datetime.now().strftime('%d %B %Y'))

@app.route('/laporan')
def laporan_page():
    return render_template('reports.html', current_date=datetime.now().strftime('%d %B %Y'))

# ===== DASHBOARD =====
@app.route('/api/dashboard/stats')
def dashboard_stats():
    total_buku = Buku.query.count()
    total_anggota = Anggota.query.count()
    total_transaksi = Transaksi.query.count()
    sedang_dipinjam = Transaksi.query.filter(Transaksi.status == BUKU_DIPINJAM).count()
    terlambat = Transaksi.query.filter(and_(
        Transaksi.status == BUKU_DIPINJAM,
        Transaksi.tanggal_jatuh_tempo < date.today()
    )).count()
    total_denda = db.session.query(db.func.sum(Transaksi.denda)).filter(
        Transaksi.status == BUKU_DIKEMBALIKAN
    ).scalar() or 0

    recent_transactions = Transaksi.query.order_by(Transaksi.created_at.desc()).limit(10).all()
    recent_data = []
    for t in recent_transactions:
        recent_data.append({
            'id': t.id,
            'nama_anggota': t.anggota.nama,
            'judul_buku': t.buku.judul,
            'tanggal_pinjam': t.tanggal_pinjam.strftime('%d-%m-%Y'),
            'status': t.status
        })

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
def get_buku():
    search = request.args.get('search', '')
    kategori = request.args.get('kategori', '')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    query = Buku.query
    if search:
        query = query.filter(or_(
            Buku.judul.contains(search),
            Buku.penulis.contains(search),
            Buku.kode_buku.contains(search)
        ))
    if kategori:
        query = query.filter(Buku.kategori == kategori)

    pagination = query.order_by(Buku.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    books = pagination.items
    result = []
    for b in books:
        result.append({
            'id': b.id,
            'kode_buku': b.kode_buku,
            'judul': b.judul,
            'penulis': b.penulis,
            'penerbit': b.penerbit,
            'tahun_terbit': b.tahun_terbit,
            'kategori': b.kategori,
            'isbn': b.isbn,
            'jumlah_halaman': b.jumlah_halaman,
            'stok': b.stok,
            'lokasi_rak': b.lokasi_rak,
            'deskripsi': b.deskripsi
        })
    return jsonify({
        'books': result,
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page
    })

@app.route('/api/buku', methods=['POST'])
def create_buku():
    data = request.json
    if not data or not data.get('kode_buku') or not data.get('judul') or not data.get('penulis'):
        return jsonify({'success': False, 'message': 'Kode buku, judul, dan penulis wajib diisi'}), 400
    buku = Buku(
        kode_buku=data.get('kode_buku'),
        judul=data.get('judul'),
        penulis=data.get('penulis'),
        penerbit=data.get('penerbit'),
        tahun_terbit=data.get('tahun_terbit'),
        kategori=data.get('kategori'),
        isbn=data.get('isbn'),
        jumlah_halaman=data.get('jumlah_halaman'),
        stok=data.get('stok', 1),
        lokasi_rak=data.get('lokasi_rak'),
        deskripsi=data.get('deskripsi')
    )
    db.session.add(buku)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Buku berhasil ditambahkan', 'id': buku.id})

@app.route('/api/buku/<int:id>', methods=['PUT'])
def update_buku(id):
    b = Buku.query.get_or_404(id)
    data = request.json
    if not data or not data.get('kode_buku') or not data.get('judul') or not data.get('penulis'):
        return jsonify({'success': False, 'message': 'Kode buku, judul, dan penulis wajib diisi'}), 400
    b.kode_buku = data.get('kode_buku', b.kode_buku)
    b.judul = data.get('judul', b.judul)
    b.penulis = data.get('penulis', b.penulis)
    b.penerbit = data.get('penerbit', b.penerbit)
    b.tahun_terbit = data.get('tahun_terbit', b.tahun_terbit)
    b.kategori = data.get('kategori', b.kategori)
    b.isbn = data.get('isbn', b.isbn)
    b.jumlah_halaman = data.get('jumlah_halaman', b.jumlah_halaman)
    b.stok = data.get('stok', b.stok)
    b.lokasi_rak = data.get('lokasi_rak', b.lokasi_rak)
    b.deskripsi = data.get('deskripsi', b.deskripsi)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Buku berhasil diperbarui'})

@app.route('/api/buku/<int:id>', methods=['DELETE'])
def delete_buku(id):
    b = Buku.query.get_or_404(id)
    has_transactions = Transaksi.query.filter_by(buku_id=id).first() is not None
    if has_transactions:
        return jsonify({'success': False, 'message': 'Tidak dapat menghapus buku yang memiliki riwayat transaksi'})
    db.session.delete(b)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Buku berhasil dihapus'})

@app.route('/api/kategori', methods=['GET'])
def get_kategori():
    categories = db.session.query(Buku.kategori).filter(
        Buku.kategori != None,
        Buku.kategori != ''
    ).distinct().all()
    return jsonify([c[0] for c in categories])

# ===== ANGGOTA CRUD =====
@app.route('/api/anggota', methods=['GET'])
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
        result.append({
            'id': a.id,
            'nis': a.nis,
            'nama': a.nama,
            'kelas': a.kelas,
            'jurusan': a.jurusan,
            'jenis_kelamin': a.jenis_kelamin,
            'no_telepon': a.no_telepon,
            'alamat': a.alamat,
            'status': a.status,
            'tanggal_bergabung': a.tanggal_bergabung.strftime('%d-%m-%Y') if a.tanggal_bergabung else ''
        })
    return jsonify({
        'anggota': result,
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page
    })

@app.route('/api/anggota', methods=['POST'])
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
    return jsonify({'success': True, 'message': 'Anggota berhasil ditambahkan', 'id': anggota.id})

@app.route('/api/anggota/<int:id>', methods=['PUT'])
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
def delete_anggota(id):
    a = Anggota.query.get_or_404(id)
    has_transactions = Transaksi.query.filter_by(anggota_id=id).first() is not None
    if has_transactions:
        return jsonify({'success': False, 'message': 'Tidak dapat menghapus anggota yang memiliki riwayat transaksi'})
    db.session.delete(a)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Anggota berhasil dihapus'})

@app.route('/api/kelas', methods=['GET'])
def get_kelas():
    classes = db.session.query(Anggota.kelas).filter(
        Anggota.kelas != None,
        Anggota.kelas != ''
    ).distinct().all()
    return jsonify([c[0] for c in classes])

# ===== TRANSAKSI CRUD =====
@app.route('/api/transaksi', methods=['GET'])
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
        result.append({
            'id': t.id,
            'buku_id': t.buku_id,
            'anggota_id': t.anggota_id,
            'nama_anggota': t.anggota.nama,
            'nis_anggota': t.anggota.nis,
            'kelas_anggota': t.anggota.kelas,
            'judul_buku': t.buku.judul,
            'kode_buku': t.buku.kode_buku,
            'tanggal_pinjam': t.tanggal_pinjam.strftime('%d-%m-%Y'),
            'tanggal_jatuh_tempo': t.tanggal_jatuh_tempo.strftime('%d-%m-%Y'),
            'tanggal_kembali': t.tanggal_kembali.strftime('%d-%m-%Y') if t.tanggal_kembali else None,
            'status': t.status,
            'denda': t.denda,
            'catatan': t.catatan
        })
    return jsonify({
        'transactions': result,
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page
    })

@app.route('/api/transaksi', methods=['POST'])
def create_transaksi():
    data = request.json
    if not data or not data.get('buku_id') or not data.get('anggota_id'):
        return jsonify({'success': False, 'message': 'Buku dan anggota wajib dipilih'}), 400
    buku = Buku.query.get(data.get('buku_id'))
    if not buku or buku.stok < 1:
        return jsonify({'success': False, 'message': 'Stok buku tidak tersedia'})
    anggota = Anggota.query.get(data.get('anggota_id'))
    if not anggota or anggota.status == 'Nonaktif':
        return jsonify({'success': False, 'message': 'Anggota tidak aktif'})
    active_borrows = Transaksi.query.filter(
        and_(Transaksi.anggota_id == anggota.id, Transaksi.status == BUKU_DIPINJAM)
    ).count()
    if active_borrows >= 3:
        return jsonify({'success': False, 'message': 'Maksimal 3 buku yang dapat dipinjam'})

    tanggal_jatuh_tempo = date.today() + timedelta(days=7)
    transaksi = Transaksi(
        buku_id=data.get('buku_id'),
        anggota_id=data.get('anggota_id'),
        tanggal_jatuh_tempo=tanggal_jatuh_tempo,
        catatan=data.get('catatan', '')
    )
    buku.stok -= 1
    db.session.add(transaksi)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Transaksi berhasil', 'id': transaksi.id})

@app.route('/api/transaksi/<int:id>', methods=['PUT'])
def update_transaksi(id):
    t = Transaksi.query.get_or_404(id)
    data = request.json
    if t.status == BUKU_DIKEMBALIKAN:
        return jsonify({'success': False, 'message': 'Transaksi sudah selesai'})
    action = data.get('action')
    if action == 'return':
        t.tanggal_kembali = date.today()
        t.status = BUKU_DIKEMBALIKAN
        if t.tanggal_kembali > t.tanggal_jatuh_tempo:
            t.status = BUKU_TERLAMBAT
            days_late = (t.tanggal_kembali - t.tanggal_jatuh_tempo).days
            t.denda = days_late * 1000
        t.buku.stok += 1
        t.catatan = data.get('catatan', t.catatan)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Buku berhasil dikembalikan'})
    elif action == 'extend':
        extend_days = data.get('extend_days', 7)
        if not isinstance(extend_days, int) or extend_days < 1:
            return jsonify({'success': False, 'message': 'Jumlah hari perpanjangan tidak valid'}), 400
        t.tanggal_jatuh_tempo = t.tanggal_jatuh_tempo + timedelta(days=extend_days)
        t.catatan = data.get('catatan', t.catatan)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Transaksi berhasil diperpanjang'})
    return jsonify({'success': False, 'message': 'Aksi tidak dikenali'}), 400

@app.route('/api/transaksi/<int:id>', methods=['DELETE'])
def delete_transaksi(id):
    t = Transaksi.query.get_or_404(id)
    if t.status == BUKU_DIPINJAM:
        t.buku.stok += 1
    db.session.delete(t)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Transaksi berhasil dihapus'})

# ===== LAPORAN =====
@app.route('/api/laporan/ringkasan')
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
        Buku.kategori, func.count(Buku.id).label('total')
    ).group_by(Buku.kategori).all()

    return jsonify({
        'monthly_borrowed': monthly_borrowed,
        'yearly_borrowed': yearly_borrowed,
        'total_returned': total_returned,
        'popular_books': [{'judul': b[0], 'total': b[1]} for b in popular_books],
        'top_members': [{'nama': m[0], 'total': m[1]} for m in top_members],
        'category_stats': [{'kategori': c[0] or 'Tidak Berkategori', 'total': c[1]} for c in category_stats]
    })

@app.route('/api/laporan/transaksi')
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
        result.append({
            'id': t.id,
            'nama_anggota': t.anggota.nama,
            'nis': t.anggota.nis,
            'kelas': t.anggota.kelas,
            'judul_buku': t.buku.judul,
            'tanggal_pinjam': t.tanggal_pinjam.strftime('%d-%m-%Y'),
            'tanggal_jatuh_tempo': t.tanggal_jatuh_tempo.strftime('%d-%m-%Y'),
            'tanggal_kembali': t.tanggal_kembali.strftime('%d-%m-%Y') if t.tanggal_kembali else '-',
            'status': t.status,
            'denda': t.denda
        })
    return jsonify(result)

# ===== INIT DB =====
@app.cli.command("init-db")
def init_db_command():
    with app.app_context():
        db.create_all()
    print("Database initialized successfully.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true', host='0.0.0.0', port=5000)
