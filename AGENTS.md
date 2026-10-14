# AGENTS.md

Panduan untuk agen yang bekerja di repo ini.

## Ringkasan proyek

CLI Python untuk **upload video masal ke TikTok Studio** (creator center) memakai
Playwright. Login dilakukan sekali secara manual, sesi disimpan sebagai
`storage_state`, lalu folder video diunggah satu per satu dengan caption, jadwal,
dan privasi.

## Perintah penting

```bash
pip install -r requirements.txt
python -m playwright install chromium   # sekali saja
python -m pytest -q                     # tes unit, tanpa browser
python -m tiktok_bulk --help
```

Jalankan modul dari root repo. Jika skrip di luar folder, set `PYTHONPATH` ke root.

## Arsitektur

- `tiktok_bulk/config.py` — **semua URL, selector DOM, dan waktu**. Ini titik
  pertama yang harus diperiksa saat TikTok mengubah halaman.
- `tiktok_bulk/manifest.py` — penemuan file + parsing manifest CSV/JSON.
- `tiktok_bulk/browser.py` — pembuatan context Playwright & persistensi sesi.
- `tiktok_bulk/auth.py` — login interaktif, cek cookie `sessionid`.
- `tiktok_bulk/uploader.py` — alur upload satu video (langkah UI terisolasi).
- `tiktok_bulk/cli.py` — subperintah `login`/`check`/`upload`.

## Konvensi

- Komentar dan pesan log berbahasa Indonesia.
- Selector memakai XPath Playwright, dikelompokkan per dataclass di `config.py`.
- Tes **tidak boleh** memakai browser atau kredensial nyata. Gunakan `FakePage`
  di `tests/conftest.py` untuk menguji alur.

## Jebakan yang diketahui

- **Tanpa sesi, halaman upload redirect ke `/login`.** Itu normal, bukan bug.
- **Mode headful gagal di server tanpa display** (`Missing X server`). Pakai
  `--headless` setelah login sekali di mesin berlayar.
- `session.json` berisi cookie rahasia; sudah di-`.gitignore`. Jangan pernah
  commit atau unggah keluar mesin.
- TikTok membulatkan jadwal ke kelipatan 5 menit dan menolak jadwal < 20 menit
  dari sekarang.
- Selector tidak dapat divalidasi tanpa sesi TikTok valid. Jika satu langkah
  gagal di akun nyata, perbaiki selector di `config.py` (bukan logika alur).
