"""
manga_translator — Paket terjemahan komik CJK PDF (CPU Optimized)

Ekspor publik:
    Config           — konfigurasi terpusat
    BubbleDetector   — deteksi speech bubble (YOLO + ONNX)
    OCREngine        — baca teks CJK (MangaOCR / PaddleOCR)
    OllamaTranslator — terjemahan via Ollama lokal
    PDFRenderer      — render teks ke PDF
    PDFSplitter      — pecah PDF besar per N halaman
    PDFMerger        — gabung semua part hasil terjemahan
    schedule_shutdown — shutdown otomatis setelah selesai
    pipeline         — orkestrasi 3-tahap
"""

from .config import Config
from .detector import BubbleDetector
from .ocr import OCREngine
from .translator import OllamaTranslator
from .renderer import PDFRenderer
from .splitter import PDFSplitter
from .merger import PDFMerger
from .shutdown import schedule_shutdown
from . import pipeline

__all__ = [
    "Config",
    "BubbleDetector",
    "OCREngine",
    "OllamaTranslator",
    "PDFRenderer",
    "PDFSplitter",
    "PDFMerger",
    "schedule_shutdown",
    "pipeline",
]
