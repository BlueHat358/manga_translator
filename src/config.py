"""
config.py — Semua konfigurasi terpusat di sini.
Ubah nilai di sini atau override via argumen CLI.
"""

from dataclasses import dataclass, field
from pathlib import Path


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

  # ── Nama bahasa (untuk prompt Ollama) ─────
  LANG_NAMES: dict = field(default_factory=lambda: {
      "ja": "Japanese",
      "ch": "Chinese",
      "korean": "Korean",
  })

  def lang_name(self) -> str:
    return self.LANG_NAMES.get(self.source_lang, self.source_lang)

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
