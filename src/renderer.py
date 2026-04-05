"""
renderer.py — Render teks terjemahan ke halaman PDF.

Tugas:
1. Render halaman PDF asli ke PIL Image
2. Hapus area bubble asli (fill putih)
3. Tulis teks terjemahan dengan auto word-wrap + posisi tengah
4. Simpan kembali ke PDF output

Tidak membutuhkan model AI apapun — hanya PIL + PyMuPDF.
"""

import gc
import os
import tempfile

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

from .config import Config


class PDFRenderer:
    def __init__(self, cfg: Config):
        self.cfg  = cfg
        self.font = self._load_font()

    def _load_font(self) -> ImageFont.FreeTypeFont:
        """Load font dengan fallback ke font sistem jika tidak ditemukan."""
        if os.path.exists(self.cfg.font_path):
            return ImageFont.truetype(self.cfg.font_path, self.cfg.font_size)

        for fp in self.cfg.font_fallbacks:
            if os.path.exists(fp):
                print(f"[FONT] Menggunakan font sistem: {fp}")
                return ImageFont.truetype(fp, self.cfg.font_size)

        print(f"[FONT] ⚠️  Font tidak ditemukan.")
        print(f"       Letakkan '{self.cfg.font_path}' di folder yang sama dengan script.")
        return ImageFont.load_default()

    def _wrap_text(self, text: str, max_width: int) -> list[str]:
        """Bagi teks menjadi beberapa baris agar muat dalam bubble."""
        words, lines, current = text.split(), [], ""
        for word in words:
            candidate = (current + " " + word).strip()
            if self.font.getbbox(candidate)[2] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def draw_text(self, draw: ImageDraw.Draw,
                  text: str, x1: int, y1: int, x2: int, y2: int):
        """
        Tulis teks terjemahan di dalam area bubble.
        Auto word-wrap dan diposisikan di tengah bubble.
        """
        if not text.strip():
            return

        max_w  = x2 - x1 - 10
        max_h  = y2 - y1 - 10
        lines  = self._wrap_text(text, max_w)

        if not lines:
            return

        line_h   = self.font.getbbox("Ag")[3] + 3
        total_h  = line_h * len(lines)
        y_cursor = y1 + 5 + max(0, (max_h - total_h) // 2)

        for line in lines:
            lw       = self.font.getbbox(line)[2]
            x_cursor = x1 + 5 + max(0, (max_w - lw) // 2)
            draw.text((x_cursor, y_cursor), line, fill="black", font=self.font)
            y_cursor += line_h

    def render_page(self, page, bubbles: list) -> Image.Image:
        """
        Render satu halaman PDF dengan teks terjemahan.

        Args:
            page    : fitz.Page object
            bubbles : list of dict {"box": [x1,y1,x2,y2], "translated_text": str}

        Return: PIL Image halaman yang sudah dirender
        """
        pix  = page.get_pixmap(dpi=self.cfg.render_dpi)
        img  = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        draw = ImageDraw.Draw(img)

        for bubble in bubbles:
            x1, y1, x2, y2 = bubble["box"]
            translated = bubble.get("translated_text", "").strip()
            if not translated:
                continue
            draw.rectangle([(x1, y1), (x2, y2)], fill="white")
            self.draw_text(draw, translated, x1, y1, x2, y2)

        return img

    def save_pdf(self, pages_images: list[Image.Image], output_path: str):
        """
        Gabungkan semua PIL Image menjadi satu file PDF.

        Args:
            pages_images : list PIL Image, satu per halaman
            output_path  : path file PDF output
        """
        output_doc = fitz.open()

        for img in pages_images:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                img.save(tmp.name, "PNG")
                tmp_path = tmp.name

            img_doc   = fitz.open(tmp_path)
            pdf_bytes = img_doc.convert_to_pdf()
            img_doc.close()
            os.unlink(tmp_path)

            with fitz.open("pdf", pdf_bytes) as page_pdf:
                output_doc.insert_pdf(page_pdf)

        output_doc.save(output_path, deflate=True)
        output_doc.close()
        print(f"[RENDER] PDF disimpan: {output_path}")
