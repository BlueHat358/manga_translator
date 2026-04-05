# Manga/Comic PDF Translator

Terjemahkan komik CJK (Jepang/China/Korea) dalam format PDF ke Bahasa Indonesia,
berjalan sepenuhnya **lokal** menggunakan Ollama — tanpa biaya API.

Dioptimasi untuk **CPU-only** (AMD Ryzen 3200G, 16GB RAM single channel).

---

## Struktur Proyek

```
manga_translator/
├── main.py                      ← Entry point CLI
├── requirements.txt
└── src/
    ├── __init__.py
    ├── config.py                ← Semua konfigurasi terpusat
    ├── detector.py              ← Deteksi bubble (YOLO + ONNX)
    ├── ocr.py                   ← OCR teks CJK (MangaOCR / PaddleOCR)
    ├── translator.py            ← Terjemahan via Ollama
    ├── renderer.py              ← Render teks ke PDF
    └── pipeline.py              ← Orkestrasi 3 tahap
```

---

## Pipeline — 3 Tahap

```
TAHAP 1 — Deteksi & OCR
  [YOLO] + [MangaOCR / PaddleOCR]
  → simpan hasil ke <nama>_translate_work/stage1_ocr.json
  → model di-unload dari RAM

TAHAP 2 — Terjemahan
  [Ollama lokal]  ← hanya ini yang aktif
  → simpan ke <nama>_translate_work/stage2_translated.json

TAHAP 3 — Render PDF
  [PIL + PyMuPDF]  ← tanpa model AI
  → simpan PDF output final
```

Setiap tahap hanya memuat model yang dibutuhkan sehingga RAM tidak pernah
tertekan oleh dua model besar sekaligus.

---

## Instalasi

```bash
# 1. Clone / download proyek
cd manga_translator

# 2. Install dependencies utama
pip install -r requirements.txt

# 3. Install OCR sesuai bahasa komik
# Jepang:
pip install git+https://github.com/kha-white/manga-ocr.git

# China / Korea:
pip install paddlepaddle paddleocr

# 4. Download YOLO model bubble detector
# Letakkan file .pt di folder yang sama dengan main.py
# https://huggingface.co/ogkalu2/comic-speech-bubble-detector-yolov8m

# 5. Siapkan font unicode (untuk render teks Indonesia)
# Download arial-unicode-ms.ttf dan letakkan di folder yang sama dengan main.py
# Atau gunakan font sistem — script akan auto-detect

# 6. Pastikan Ollama berjalan
sudo systemctl start ollama
ollama pull qwen3.5:2b
```

---

## Cara Pakai

Manga Translator menggunakan sistem **subcommand** (`translate`, `split`, `merge`, `status`) untuk mendukung skenario pemrosesan komik kecil hingga sangat besar (dipecah per bagian).

### 1. Terjemahkan Langsung (Komik Ringan)

```bash
# Terjemahkan manga Jepang
python main.py translate -i "komik.pdf" -o "komik_id.pdf"

# Terjemahkan manhua China
python main.py translate -i "manhua.pdf" -o "manhua_id.pdf" --lang ch

# Terjemahkan manhwa Korea
python main.py translate -i "manhwa.pdf" -o "manhwa_id.pdf" --lang korean

# Jalankan satu tahap saja (untuk resume jika terputus)
python main.py translate -i "komik.pdf" -o "hasil.pdf" --stage 1  # deteksi + OCR
python main.py translate -i "komik.pdf" -o "hasil.pdf" --stage 2  # terjemahan
python main.py translate -i "komik.pdf" -o "hasil.pdf" --stage 3  # render PDF
```

### 2. Workflow Part per Part (Komik Besar)

Jika komik sangat panjang, memori akan cepat penuh. Maka manfaatkan pecah per-part:

```bash
# a. Pecah komik besar menjadi part-part kecil (misal: per 50 halaman)
python main.py split -i "komik.pdf" --pages 50

# b. Terjemahkan dari salah satu file part
# (simpan sementara ke null/bebas asal nama output tersedia, krn merge membaca part yg sudah ditranslate)
python main.py translate -i "komik_parts/komik_part001.pdf" -o /dev/null

# c. Cek progres semua part pengerjaan komik
python main.py status -i "komik.pdf"

# d. Gabungkan semua PDF part yang sudah sukses
python main.py merge -i "komik.pdf" -o "komik_id.pdf"
```

---

## Opsi CLI Lengkap

Sistem ini memiliki 4 subcommand utama. Anda dapat memanggil bantuan detail fitur via `python main.py --help`.

| Subcommand  | Fungsi                                                                           |
| ----------- | -------------------------------------------------------------------------------- |
| `translate` | Menerjemahkan sebuah dokumen atau part PDF melalui 3 tahap (OCR, Ollama, Render) |
| `split`     | Memecah dokumen PDF besar menjadi potongan (part) kecil untuk diterjemahkan      |
| `status`    | Mengecek status keseluruhan part PDF, yang sudah selesai maupun yang belum       |
| `merge`     | Menyatukan semua part hasil terjemahan menjadi dokumen konsekutif                |

### Opsi Umum (Muncul di Beberapa Subcommand)

| Argumen            | Default                | Keterangan                                               |
| ------------------ | ---------------------- | -------------------------------------------------------- |
| `--lang / -l`      | `ja`                   | Bahasa sumber teks asli: `ja` / `ch` / `korean`          |
| `--model / -m`     | `qwen3.5:2b`           | Nama model terjemahan Ollama yang dijalankan lokal       |
| `--font-size / -f` | `20`                   | Ukuran font yang dipakai selama render text balon kata   |
| `--font`           | `arial-unicode-ms.ttf` | Path lokasi custom font `TTF` sistem                     |
| `--dpi`            | `150`                  | Nilai DPI ketajaman PDF ke Raster Image yang diproses    |
| `--yolo`           | `comic-speech-...`     | Path file detektor text bubble YOLO `.pt`                |
| `--conf`           | `0.35`                 | Confidence score YOLO dalam mendeteksi kotak balon komik |

### Opsi Khusus Subcommand

**`translate`**

- `--input / -i` : Path PDF original yang diproses (wajib)
- `--output / -o` : Path output yang di-generate (wajib)
- `--stage / -s` : Jalankan salah satu stage (`1`, `2`, `3`). Tanpa parameter berarti semua tahap tereksekusi.
- `--shutdown` : Mematikan PC seketika proses selesai
- `--shutdown-delay` : Mengatur delay (dalam hitungan menit) sebelum PC shutdown (default: 1)

**`split`**

- `--input / -i` : Path PDF untuk dipotong (wajib)
- `--pages / -p` : Panjang batas jumlah halaman per part (default: 50)
- `--shutdown`, `--shutdown-delay` : Dapat dipakai untuk otomasi

**`merge`**

- `--input / -i` : Path nama file referensi utama/asal komik awal (wajib)
- `--output / -o` : Path target untuk dijadikan file jadi (wajib)
- `--force` : Tetap nekat menyatukan dokumen meskipun beberapa halaman/part belum tuntas terjemahan
- `--shutdown`, `--shutdown-delay`

**`status`**

- `--input / -i` : Path file sumber asli PDF (wajib)

---

## Tips Performa (CPU-only)

- **Tutup browser** saat menjalankan tahap 1 (OCR) — butuh RAM paling banyak
- **Tahap 2** (Ollama) bisa jalan di background sambil melakukan hal lain
- Jika ingin lebih cepat: ganti `--dpi 100` (kualitas sedikit turun)
- File JSON antar tahap tersimpan — jika crash, lanjut dari tahap terakhir
- Untuk batch banyak komik, jalankan tahap 1 semua file dulu, baru tahap 2
