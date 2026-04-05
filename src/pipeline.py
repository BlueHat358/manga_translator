"""
pipeline.py — Orkestrasi 3 tahap pipeline terjemahan.

TAHAP 1 — detect_and_ocr()
    Load YOLO + OCR → proses semua halaman → simpan JSON → unload model

TAHAP 2 — translate()
    Load Ollama client → terjemahkan semua bubble → simpan JSON

TAHAP 3 — render()
    Baca JSON → render PDF baru → tidak butuh model AI

Strategi RAM:
    Setiap tahap hanya memuat model yang dibutuhkan.
    Model di-unload sebelum tahap berikutnya dimulai.
    gc.collect() dipanggil eksplisit setelah unload.
"""

import gc
import json
import sys
import time

import fitz
import numpy as np
from PIL import Image

from .config import Config
from .detector import BubbleDetector
from .ocr import OCREngine
from .renderer import PDFRenderer
from .translator import OllamaTranslator


def _header(title: str):
    print("\n" + "═" * 55)
    print(f"  {title}")
    print("═" * 55)


def _elapsed(start: float) -> str:
    return f"{(time.time() - start) / 60:.1f} menit"


# ───────────────────────────────────────────────────────
# TAHAP 1
# ───────────────────────────────────────────────────────

def detect_and_ocr(cfg: Config, input_path: str) -> bool:
    """
    Tahap 1: PDF → deteksi bubble → OCR → simpan JSON.

    Format JSON output (stage1_ocr.json):
    [
      {
        "page":    0,
        "width":   1200,
        "height":  1800,
        "bubbles": [
          {"box": [x1, y1, x2, y2], "ocr_text": "テスト"},
          ...
        ]
      },
      ...
    ]

    Return True jika selesai, False jika di-skip (sudah ada).
    """
    out_path = cfg.stage1_json(input_path)

    if out_path.exists():
        print(f"[TAHAP 1] File sudah ada: {out_path}")
        print("          Hapus file tersebut jika ingin mengulang tahap ini.")
        return False

    _header("TAHAP 1: Deteksi Bubble + OCR")

    detector = BubbleDetector(cfg)
    ocr      = OCREngine(cfg)

    doc       = fitz.open(input_path)
    total     = len(doc)
    all_pages = []
    start     = time.time()

    for page_num in range(total):
        print(f"\n  Halaman {page_num + 1}/{total}")

        page   = doc.load_page(page_num)
        pix    = page.get_pixmap(dpi=cfg.render_dpi)
        img    = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img_np = np.array(img)

        detections = detector.detect(img_np)
        print(f"  Ditemukan {len(detections)} bubble")

        bubbles = []
        for i, (x1, y1, x2, y2) in enumerate(detections):
            cropped = img.crop((x1, y1, x2, y2))
            text    = ocr.read(cropped)

            if text:
                preview = text[:70] + ("..." if len(text) > 70 else "")
                print(f"    [{i+1}] {preview}")

            bubbles.append({"box": [x1, y1, x2, y2], "ocr_text": text})

        all_pages.append({
            "page":    page_num,
            "width":   pix.width,
            "height":  pix.height,
            "bubbles": bubbles,
        })

        # Bebaskan memori halaman segera
        del img_np, img
        gc.collect()

    doc.close()

    # Unload model sebelum tahap berikutnya
    detector.unload()
    ocr.unload()
    gc.collect()

    # Simpan JSON
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_pages, f, ensure_ascii=False, indent=2)

    total_bubbles = sum(len(p["bubbles"]) for p in all_pages)
    print(f"\n[TAHAP 1] Selesai dalam {_elapsed(start)}")
    print(f"          Total bubble: {total_bubbles}")
    print(f"          Hasil: {out_path}")
    return True


# ───────────────────────────────────────────────────────
# TAHAP 2
# ───────────────────────────────────────────────────────

def translate(cfg: Config, input_path: str) -> bool:
    """
    Tahap 2: JSON OCR → terjemahkan via Ollama → simpan JSON baru.

    Format JSON output (stage2_translated.json):
    Sama dengan stage1, ditambah field "translated_text" di tiap bubble.

    Return True jika selesai, False jika di-skip.
    """
    in_path  = cfg.stage1_json(input_path)
    out_path = cfg.stage2_json(input_path)

    if not in_path.exists():
        print(f"[ERROR] Hasil tahap 1 tidak ditemukan: {in_path}")
        print("        Jalankan tahap 1 terlebih dahulu.")
        sys.exit(1)

    if out_path.exists():
        print(f"[TAHAP 2] File sudah ada: {out_path}")
        print("          Hapus file tersebut jika ingin mengulang tahap ini.")
        return False

    _header("TAHAP 2: Terjemahan via Ollama")

    try:
        translator = OllamaTranslator(cfg)
    except ConnectionError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    with open(in_path, encoding="utf-8") as f:
        pages = json.load(f)

    total_bubbles    = sum(len(p["bubbles"]) for p in pages)
    translated_count = 0
    start            = time.time()

    print(f"\n  Total bubble: {total_bubbles}")

    for page_data in pages:
        page_num = page_data["page"]
        bubbles  = page_data["bubbles"]
        print(f"\n  Halaman {page_num + 1} ({len(bubbles)} bubble)")

        for i, bubble in enumerate(bubbles):
            ocr_text = bubble.get("ocr_text", "").strip()

            if not ocr_text:
                bubble["translated_text"] = ""
                continue

            translated = translator.translate(ocr_text)
            bubble["translated_text"] = translated
            translated_count += 1
            print(f"    [{i+1}] {ocr_text[:35]:35s} → {translated[:35]}")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)

    print(f"\n[TAHAP 2] Selesai dalam {_elapsed(start)}")
    print(f"          Diterjemahkan: {translated_count}/{total_bubbles}")
    print(f"          Hasil: {out_path}")
    return True


# ───────────────────────────────────────────────────────
# TAHAP 3
# ───────────────────────────────────────────────────────

def render(cfg: Config, input_path: str, output_path: str) -> bool:
    """
    Tahap 3: PDF asli + JSON terjemahan → PDF baru.
    Tidak butuh model AI — hanya PIL + PyMuPDF.

    Return True jika selesai.
    """
    in_path = cfg.stage2_json(input_path)

    if not in_path.exists():
        print(f"[ERROR] Hasil tahap 2 tidak ditemukan: {in_path}")
        print("        Jalankan tahap 2 terlebih dahulu.")
        sys.exit(1)

    _header("TAHAP 3: Render PDF")

    with open(in_path, encoding="utf-8") as f:
        pages = json.load(f)

    renderer = PDFRenderer(cfg)
    doc      = fitz.open(input_path)
    start    = time.time()

    rendered_pages = []

    for page_data in pages:
        page_num = page_data["page"]
        bubbles  = page_data["bubbles"]
        print(f"  Render halaman {page_num + 1}/{len(pages)} ({len(bubbles)} bubble)")

        page = doc.load_page(page_num)
        img  = renderer.render_page(page, bubbles)
        rendered_pages.append(img)

        gc.collect()

    doc.close()
    renderer.save_pdf(rendered_pages, output_path)

    print(f"\n[TAHAP 3] Selesai dalam {_elapsed(start)}")
    print(f"          Output: {output_path}")
    return True
