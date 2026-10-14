# TikTok Bulk Upload

Upload video masal ke **TikTok Studio** (creator center) secara otomatis memakai
Playwright. Cocok untuk mengunggah puluhan sampai ratusan video dari sebuah
folder, lengkap dengan caption, hashtag, jadwal, dan pengaturan privasi.

Target halaman: <https://www.tiktok.com/tiktokstudio/upload?from=creator_center&tab=video>

## Cara kerja

1. `login` membuka browser dan Anda menyelesaikan login sekali secara manual
   (email/username, Google, atau QR). Sesi disimpan ke `~/.tiktok_bulk/session.json`.
2. `upload` memuat sesi itu, membuka halaman upload, lalu untuk setiap video:
   pilih file -> tunggu TikTok memproses -> isi caption -> atur privasi/jadwal ->
   klik Post -> tunggu konfirmasi.
3. Setiap video diberi jeda acak (default 5-15 detik) agar tidak terlihat seperti
   bot dan mengurangi risiko rate-limit.

## Instalasi

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

Opsional, install sebagai perintah:

```bash
pip install -e .
tiktok-bulk --help
```

## Pemakaian

### 1. Login sekali

```bash
python -m tiktok_bulk login
```

Jendela browser terbuka. Login seperti biasa, lalu tunggu sampai log menulis
"Login berhasil". Sesi tersimpan otomatis.

### 2. Cek sesi

```bash
python -m tiktok_bulk check
```

### 3. Upload masal

Semua video di folder, caption sama untuk semua:

```bash
python -m tiktok_bulk upload ./videos --caption "Konten harian #fyp"
```

Dengan manifest (caption/jadwal/privasi per video):

```bash
python -m tiktok_bulk upload ./videos --manifest ./videos/manifest.csv
```

Uji coba tanpa mem-publish (hanya mengisi form):

```bash
python -m tiktok_bulk upload ./videos --dry-run --limit 1
```

Upload headless (sesi harus sudah ada):

```bash
python -m tiktok_bulk upload ./videos --headless --delay 20
```

## Format manifest

CSV (kolom `file` wajib, sisanya opsional). Contoh ada di
[`examples/manifest.csv`](examples/manifest.csv):

```csv
file,caption,schedule,visibility,cover
promo1.mp4,"Promo spesial hari ini! #promo #diskon #fyp",2026-10-20 19:00,Public,
tips2.mp4,"3 tips cepat bikin konten #tips",,Public,
review3.mp4,"Review produk terbaru #review",,Friends,cover3.jpg
```

- `caption` (alias: `description`, `desc`) — teks postingan, maksimal 2200 karakter.
- `schedule` (alias: `jadwal`) — waktu lokal `YYYY-MM-DD HH:MM`, minimal 20 menit
  dari sekarang, dibulatkan ke kelipatan 5 menit. Kosongkan untuk posting langsung.
- `visibility` (alias: `privacy`) — `Public`, `Friends`, atau `Private`.
- `cover` — file gambar `.png/.jpg/.jpeg` untuk thumbnail.

JSON juga didukung: array objek dengan kunci yang sama.

File yang tidak ada di manifest tetap diunggah memakai caption default (`--caption`).

## Opsi penting

| Opsi | Keterangan |
| --- | --- |
| `--headless` | Tanpa jendela browser (wajib sudah login sebelumnya) |
| `--channel chrome` | Pakai Chrome terpasang, bukan Chromium bawaan Playwright |
| `--proxy http://host:port` | Jalur proxy untuk koneksi |
| `--recursive` | Telusuri subfolder |
| `--limit N` | Batasi jumlah video |
| `--delay N` | Jeda tetap antar video (detik) |
| `--report hasil.csv` | Tulis ringkasan hasil (berhasil/gagal/dilewati) |
| `-v` | Log detail untuk debugging |

## Catatan penting

- **Selector dapat berubah.** TikTok memperbarui DOM secara berkala. Semua selector
  terpusat di [`tiktok_bulk/config.py`](tiktok_bulk/config.py). Jika sebuah langkah
  gagal, perbarui nilai di sana; logika alur tidak perlu diubah.
- **Sesi berisi rahasia.** `session.json` memuat cookie login. File ini
  di-`.gitignore` dan sebaiknya tidak dibagikan.
- **Patuhi aturan TikTok.** Gunakan hanya untuk akun Anda sendiri, jangan spam,
  dan hormati batas unggah harian serta Community Guidelines. Alat ini melakukan
  jeda acak untuk mengurangi beban server, tetapi tanggung jawab kepatuhan tetap
  pada pengguna.
- **Verifikasi akun.** Akun baru atau tanpa verifikasi email/telepon mungkin
  hanya bisa memakai `Private`/`Friends`.

## Tes

```bash
python -m pytest -q
```

Tes berjalan tanpa browser (memakai page tiruan) dan tanpa kredensial.

## Struktur

```
tiktok_bulk/
  config.py    # URL, selector DOM, pengaturan waktu
  manifest.py  # pembacaan folder + manifest CSV/JSON
  browser.py   # Playwright context + persistensi sesi
  auth.py      # login interaktif & verifikasi sesi
  uploader.py  # alur upload satu video
  cli.py       # perintah login/check/upload
tests/         # tes unit tanpa browser
examples/      # contoh manifest
```
