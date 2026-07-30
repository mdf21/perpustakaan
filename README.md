# Aplikasi Perpustakaan SMA

Aplikasi perpustakaan profesional lengkap untuk sekolah, dibangun dengan Python Flask dan SQLite.

## Fitur

- **Dashboard**: Ringkasan statistik perpustakaan
- **Manajemen Buku**: CRUD data buku dengan pencarian dan filter kategori
- **Manajemen Anggota**: CRUD data anggota dengan status aktif/nonaktif
- **Peminjaman**: Transaksi peminjaman dan pengembalian buku
- **Laporan**: Ringkasan, buku populer, anggota aktif, dan laporan transaksi

## Instalasi & Menjalankan

1. Install dependensi:
   ```bash
   pip install -r requirements.txt
   ```

2. Jalankan aplikasi:
   ```bash
   python app.py
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

- **Admin**: Akses penuh ke semua fitur
- Username default: admin (diakses langsung dari browser)

## Catatan

- Database SQLite akan dibuat otomatis saat pertama kali menjalankan aplikasi
- Maksimal pinjam: 3 buku per anggota
- Durasi pinjam: 7 hari
- Denda keterlambatan: Rp 1.000/hari
