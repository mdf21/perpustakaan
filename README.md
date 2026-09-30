# Aplikasi Perpustakaan SMA

Aplikasi perpustakaan profesional lengkap untuk sekolah, dibangun dengan Python Flask dan SQLite.

## Fitur

- **Layanan siswa** (`/opac`): Cari buku, pengarang, kategori DDC, ketersediaan, dan lokasi rak tanpa login
- **Informasi perpustakaan** (`/informasi`): Sejarah, visi, misi, dan struktur organisasi yang dikelola petugas
- **Absensi kunjungan** (`/kunjungan`): Pindai QR kartu anggota dengan kamera atau pemindai QR USB; satu kunjungan per anggota per hari
- **Panel petugas**: Dashboard, CRUD buku/anggota/rak, master jenis buku/kategori/jurusan/kelas/DDC/sumber, peminjaman dan pengembalian, serta laporan transaksi dan kas denda
- **Kartu anggota**: Cetak kartu siswa dengan QR bertanda tangan dari halaman Data Anggota
- **Label buku**: Cetak barcode buku dari halaman Data Buku

## Instalasi & Menjalankan

1. Install dependensi:

   ```bash
   pip install -r requirements.txt
   ```

2. Jalankan aplikasi:

   ```bash
   python app.py
   ```

   Untuk deployment Gunicorn/Docker atau database yang sudah ada, jalankan inisialisasi skema satu kali sebelum server:

   ```bash
   flask --app app init-db
   ```

3. Buka browser dan akses:
   ```
   http://localhost:5000
   ```

## Struktur Proyek

```
perpustakaan/
├── app.py                 # Backend Flask + API
├── requirements.txt       # Dependensi Python
├── perpustakaan.db        # Database SQLite (dibuat otomatis)
├── static/
│   ├── css/style.css      # Styling
│   └── js/app.js          # JavaScript
└── templates/
    ├── base.html          # Template dasar
    ├── dashboard.html     # Halaman dashboard
    ├── books.html         # Halaman daftar buku
    ├── members.html       # Halaman daftar anggota
    ├── transactions.html  # Halaman peminjaman
    └── reports.html       # Halaman laporan
```

## Hak Akses

- **Siswa**: Katalog, informasi perpustakaan, dan absensi kunjungan tanpa login petugas
- **Petugas/Admin**: Pengelolaan koleksi, anggota, rak, transaksi, laporan, informasi perpustakaan, dan kartu anggota
- Akun awal: `admin` / `admin123`; segera ganti kredensial dan `SECRET_KEY` sebelum deployment publik

## Catatan

- Database SQLite akan dibuat otomatis saat pertama kali menjalankan aplikasi
- Maksimal pinjam: 3 buku per anggota
- Durasi pinjam: 7 hari
- Denda keterlambatan: Rp 1.000/hari
- Lengkapi sejarah, visi, misi, dan struktur sekolah dari menu **Informasi Perpustakaan** agar tampil untuk siswa.
