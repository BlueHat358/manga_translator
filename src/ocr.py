"""
ocr.py — OCR untuk teks CJK dalam speech bubble.

Mendukung:
- MangaOCR  : Jepang (ja)  — pakai ONNX internal, cepat di CPU
- PaddleOCR : China (ch) dan Korea (korean) — CPU mode + MKL-DNN
"""

import numpy as np
from PIL import Image

from .config import Config


class OCREngine:
    def __init__(self, cfg: Config):
        self.cfg  = cfg
        self.lang = cfg.source_lang
        self._manga_ocr  = None
        self._paddle_ocr = None
        self._load()

    def _load(self):
        if self.lang == "ja":
            self._load_manga_ocr()
        else:
            self._load_paddle_ocr()

    def _load_manga_ocr(self):
        from manga_ocr import MangaOcr
        print("[OCR] Loading MangaOCR (CPU)...")
        # MangaOCR sudah pakai ONNX secara internal — cukup cepat di CPU
        self._manga_ocr = MangaOcr(force_cpu=True)
        print("[OCR] MangaOCR siap.")

    def _load_paddle_ocr(self):
        from paddleocr import PaddleOCR
        print(f"[OCR] Loading PaddleOCR (lang={self.lang}, CPU)...")
        self._paddle_ocr = PaddleOCR(
            use_angle_cls=True,
            lang=self.lang,
            use_gpu=False,
            enable_mkldnn=True,  # MKL-DNN: percepat inferensi CPU
            cpu_threads=4,       # sesuai Ryzen 3200G (4 core)
            show_log=False,
        )
        print("[OCR] PaddleOCR siap.")

    def read(self, pil_image: Image.Image) -> str:
        """
        Baca teks dari cropped bubble (PIL Image).
        Return: string teks hasil OCR, atau "" jika gagal.
        """
        try:
            if self.lang == "ja":
                return self._read_manga(pil_image)
            else:
                return self._read_paddle(pil_image)
        except Exception as e:
            print(f"    [OCR] Error: {e}")
            return ""

    def _read_manga(self, pil_image: Image.Image) -> str:
        result = self._manga_ocr(pil_image)
        return result.strip() if result else ""

    def _read_paddle(self, pil_image: Image.Image) -> str:
        result = self._paddle_ocr.ocr(np.array(pil_image), cls=True)
        if result and result[0]:
            return " ".join([line[1][0] for line in result[0]]).strip()
        return ""

    def unload(self):
        """Bebaskan model dari RAM."""
        del self._manga_ocr, self._paddle_ocr
        self._manga_ocr  = None
        self._paddle_ocr = None
