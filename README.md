# Sistem Informasi Perpustakaan Sekolah

Aplikasi pengelolaan perpustakaan sekolah berbasis Flask dan SQLite. Sistem menyediakan katalog publik untuk siswa serta panel untuk mengelola koleksi, anggota, sirkulasi, dan laporan.

## Fitur

### Layanan siswa

- **Katalog buku** (`/opac`): cari buku dan lihat kategori, ketersediaan, lokasi rak, serta rekomendasi.
- **E-book**: baca dan unduh berkas PDF yang disediakan perpustakaan.
- **Informasi perpustakaan** (`/informasi`): lihat profil, sejarah, visi, misi, dan struktur organisasi sekolah.
- **Akun anggota**: anggota dapat masuk menggunakan akun yang disiapkan petugas.

### Panel petugas dan admin

- OPAC Administrator (`/admin/opac`) untuk admin: cari koleksi buku, catat peminjaman menggunakan kamera atau scanner QR/barcode anggota dan buku maupun NIS/ISBN, proses pengembalian, serta mencatat kunjungan anggota menggunakan QR kartu, kamera, atau NIS. Satu kunjungan per anggota per hari.
- Dashboard dengan ringkasan koleksi, anggota, peminjaman, keterlambatan, dan denda.
- Kelola buku, anggota, rak, dan data referensi seperti kategori, jenis buku, kelas, jurusan, DDC, dan sumber buku.
- Proses peminjaman, perpanjangan, pengembalian, serta pembayaran denda.
- Cetak kartu anggota satuan maupun massal, dan cetak label QR buku.
- Impor dan ekspor data buku dan anggota melalui spreadsheet.
- Lihat laporan transaksi, denda, dan kunjungan.
- Kelola profil perpustakaan serta cadangkan dan pulihkan database beserta file unggahan.
- Pengingat pengembalian melalui WhatsApp tersedia jika integrasi Fonnte dikonfigurasi.

## Persyaratan

- Python 3.10 atau lebih baru
- pip
- Browser modern

Pemindaian menggunakan kamera memerlukan HTTPS dengan sertifikat tepercaya atau akses melalui `localhost`. Scanner QR USB yang berfungsi sebagai input keyboard dapat digunakan tanpa akses kamera.

## Menjalankan secara lokal

1. Buat dan aktifkan virtual environment (disarankan), lalu pasang dependensi:

   ```bash
   python -m venv .venv
   ```

   Windows PowerShell:

   ```powershell
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

   macOS/Linux:

   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Jalankan aplikasi:

   ```bash
   python app.py
   ```

   Saat dijalankan langsung, aplikasi membuat atau memperbarui skema database dan membuat akun admin awal jika belum tersedia.

3. Buka `http://localhost:5000`.

Untuk menyiapkan database sebelum menjalankan server WSGI atau deployment:

```bash
flask --app app init-db
```

Server produksi dapat dijalankan dengan Gunicorn, misalnya:

```bash
gunicorn --workers 3 --timeout 300 --bind 0.0.0.0:5000 app:app
```

## Menjalankan dengan Docker Compose

Docker Compose membangun image aplikasi, menginisialisasi database, lalu menjalankan Gunicorn. Port host bawaan adalah `6001`:

```bash
docker compose up --build -d
```

Buka `http://localhost:6001`. Database disimpan secara persisten di `data/perpustakaan.db`, sedangkan file unggahan berada di `static/uploads/`. Hentikan layanan dengan:

```bash
docker compose down
```

Sebelum deployment, ganti `SECRET_KEY` bawaan pada `docker-compose.yml` dengan nilai rahasia yang kuat dan unik. Jangan gunakan konfigurasi contoh untuk layanan publik.

## Konfigurasi

Aplikasi menerima konfigurasi berikut melalui environment:

| Variabel | Kegunaan | Nilai bawaan |
|---|---|---|
| `DATABASE_URL` | URI database SQLAlchemy | `sqlite:///perpustakaan.db` (SQLite di folder instance Flask) |
| `SECRET_KEY` | Kunci sesi dan QR kartu anggota | Kunci pengembangan bawaan; wajib diganti sebelum deployment |
| `FLASK_DEBUG` | Mengaktifkan mode debug saat menjalankan `python app.py` | `False` |
| `CORS_ORIGINS` | Asal yang diizinkan untuk API | `*` |
| `FONNTE_TOKEN` | Token API Fonnte untuk pengingat WhatsApp | Tidak diatur |

`docker-compose.yml` mengatur `DATABASE_URL` ke database di volume `./data` dan memetakan port `6001:5000`.

## Akun dan aturan sirkulasi

- Akun admin awal: **username `admin`**, **password `admin123`**. Segera ganti kata sandi setelah masuk pertama kali.
- Akun anggota dibuat atau dikelola oleh petugas; kata sandi awal anggota yang diimpor dapat menggunakan NIS.
- Maksimal 3 buku aktif per anggota. Anggota dengan pinjaman terlambat tidak dapat meminjam buku lain sampai keterlambatan diselesaikan.
- Jatuh tempo bawaan adalah 7 hari setelah tanggal pinjam; petugas dapat mengatur tanggal kembali pada transaksi.
- Denda keterlambatan adalah Rp1.000 per hari.

## Data dan keamanan

- Pada konfigurasi lokal bawaan, database SQLite berada di `instance/perpustakaan.db`.
- Gambar sampul, PDF e-book, dan logo sekolah disimpan di `static/uploads/`.
- Cadangan JSON memuat data database, termasuk data pribadi dan hash kata sandi, serta file unggahan. Simpan cadangan di lokasi yang aman dan pulihkan hanya file tepercaya. Pemulihan mengganti data aktif.
- Ganti `SECRET_KEY` dan kata sandi admin sebelum aplikasi diakses melalui jaringan publik. Batasi juga akses ke server dan file database/unggahan.

## Struktur proyek

```text
perpustakaan/
├── app.py                 # Aplikasi Flask, model database, dan API
├── update_db.py           # Utilitas pembaruan database
├── requirements.txt       # Dependensi Python
├── Dockerfile
├── docker-compose.yml
├── data/                  # Database persisten untuk Docker Compose
├── instance/              # Database lokal Flask
├── static/
│   ├── css/style.css
│   ├── js/                 # JavaScript dan pustaka pemindai QR
│   └── uploads/            # Sampul, e-book, dan logo sekolah
└── templates/              # Halaman katalog dan panel perpustakaan
```
