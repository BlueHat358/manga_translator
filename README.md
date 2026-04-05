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

```bash
# Terjemahkan manga Jepang
python main.py -i "komik.pdf" -o "komik_id.pdf"

# Terjemahkan manhua China
python main.py -i "manhua.pdf" -o "manhua_id.pdf" --lang ch

# Terjemahkan manhwa Korea
python main.py -i "manhwa.pdf" -o "manhwa_id.pdf" --lang korean

# Jalankan satu tahap saja (untuk resume jika terputus)
python main.py -i "komik.pdf" -o "hasil.pdf" --stage 1  # deteksi + OCR
python main.py -i "komik.pdf" -o "hasil.pdf" --stage 2  # terjemahan
python main.py -i "komik.pdf" -o "hasil.pdf" --stage 3  # render PDF
```

---

## Opsi CLI Lengkap

| Argumen            | Default                                  | Keterangan                                    |
| ------------------ | ---------------------------------------- | --------------------------------------------- |
| `--input / -i`     | —                                        | Path PDF input (wajib)                        |
| `--output / -o`    | —                                        | Path PDF output (wajib)                       |
| `--lang / -l`      | `ja`                                     | Bahasa sumber: `ja` / `ch` / `korean`         |
| `--stage / -s`     | semua                                    | Jalankan hanya tahap 1 / 2 / 3                |
| `--model / -m`     | `qwen3.5:2b`                             | Model Ollama                                  |
| `--font-size / -f` | `20`                                     | Ukuran font terjemahan                        |
| `--yolo`           | `comic-speech-bubble-detector-yolov8.pt` | Path YOLO model                               |
| `--font`           | `arial-unicode-ms.ttf`                   | Path font TTF                                 |
| `--dpi`            | `150`                                    | DPI render halaman                            |
| `--conf`           | `0.35`                                   | Confidence threshold YOLO                     |
| `--shutdown`       | `False`                                  | Shutdown PC otomatis setelah proses selesai   |
| `--shutdown-delay` | `1`                                      | Jeda waktu (dalam menit) sebelum PC dimatikan |

---

## Tips Performa (CPU-only)

- **Tutup browser** saat menjalankan tahap 1 (OCR) — butuh RAM paling banyak
- **Tahap 2** (Ollama) bisa jalan di background sambil melakukan hal lain
- Jika ingin lebih cepat: ganti `--dpi 100` (kualitas sedikit turun)
- File JSON antar tahap tersimpan — jika crash, lanjut dari tahap terakhir
- Untuk batch banyak komik, jalankan tahap 1 semua file dulu, baru tahap 2
