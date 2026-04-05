"""
config.py — Semua konfigurasi terpusat di sini.
Ubah nilai di sini atau override via argumen CLI.
"""

from dataclasses import dataclass, field
from pathlib import Path


# Bahasa sumber yang didukung beserta engine OCR-nya
# Format: "kode_paddleocr": "Nama Tampilan"
# Referensi lengkap: https://paddlepaddle.github.io/PaddleOCR/ppocr/blog/multi_languages.html
SUPPORTED_LANGS = {
    # ── Pakai MangaOCR (lebih akurat untuk font komik stylized) ──
    "ja": "Japanese",

    # ── Pakai PaddleOCR (80+ bahasa) ──
    "ch": "Chinese (Simplified)",
    "chinese_cht": "Chinese (Traditional)",
    "korean": "Korean",
    "en": "English",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "es": "Spanish",
    "pt": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
    "hi": "Hindi",
    "th": "Thai",
    "vi": "Vietnamese",
    "id": "Indonesian",
}

# Bahasa yang pakai MangaOCR (bukan PaddleOCR)
MANGA_OCR_LANGS = {"ja"}


@dataclass
class Config:
  # ── Path ──────────────────────────────────
  yolo_model: str = "comic-speech-bubble-detector.pt"
  font_path: str = "arial-unicode-ms-regular.ttf"

  # ── Ollama ────────────────────────────────
  ollama_url: str = "http://localhost:11434/v1"
  ollama_model: str = "qwen3.5:2b-q4_K_M"
  target_lang: str = "English"

  # ── Pipeline ──────────────────────────────
  source_lang: str = "ja"          # ja | ch | korean
  force_paddle: bool = False         # paksa PaddleOCR meski source_lang =
  font_size: int = 24
  render_dpi: int = 150           # 150 cukup untuk komik
  yolo_conf: float = 0.35

  # ── Font fallback (sistem) ─────────────────
  font_fallbacks: list = field(default_factory=lambda: [
      "/usr/share/fonts/TTF/DejaVuSans.ttf",
      "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
      "/usr/share/fonts/noto/NotoSans-Regular.ttf",
      "/usr/share/fonts/TTF/NotoSansCJK-Regular.ttc",
  ])

  def lang_name(self) -> str:
    """Nama panjang bahasa sumber untuk prompt Ollama."""
    return SUPPORTED_LANGS.get(self.source_lang, self.source_lang)

  def use_manga_ocr(self) -> bool:
    """True jika harus pakai MangaOCR, False jika PaddleOCR."""
    return self.source_lang in MANGA_OCR_LANGS and not self.force_paddle

  def work_dir(self, input_path: str) -> Path:
    """Folder kerja JSON antar tahap. Contoh: komik.pdf → komik_translate_work/"""
    base = Path(input_path).stem
    work = Path(input_path).parent / f"{base}_translate_work"
    work.mkdir(exist_ok=True)
    return work

  def stage1_json(self, input_path: str) -> Path:
    return self.work_dir(input_path) / "stage1_ocr.json"

  def stage2_json(self, input_path: str) -> Path:
    return self.work_dir(input_path) / "stage2_translated.json"
