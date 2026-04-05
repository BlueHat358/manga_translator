"""
merger.py — Gabungkan semua part PDF yang sudah diterjemahkan.

Alur:
  1. Cek semua part sudah selesai (stage2_translated.json ada semua)
  2. Render tiap part ke PDF (tahap 3 pipeline)
  3. Gabungkan semua PDF hasil render menjadi satu file output

Catatan:
  Merger tidak akan jalan jika ada part yang belum selesai diterjemahkan,
  kecuali dipaksa dengan force=True (part yang belum selesai dilewati).
"""

import fitz
from pathlib import Path

from .config   import Config
from .pipeline import render
from .splitter import PDFSplitter


class PDFMerger:
    def __init__(self, cfg: Config):
        self.cfg      = cfg
        self.splitter = PDFSplitter(cfg)

    def merge(self, input_path: str, output_path: str,
              font_size: int = 20, force: bool = False) -> bool:
        """
        Render semua part yang sudah selesai, lalu gabungkan jadi satu PDF.

        Args:
            input_path  : path PDF asli (untuk menemukan folder parts)
            output_path : path PDF output final
            font_size   : ukuran font terjemahan
            force       : jika True, lewati part yang belum selesai
                          (hasil tidak lengkap tapi tidak error)

        Return:
            True  jika semua part berhasil digabung
            False jika ada part yang belum selesai dan force=False
        """
        status = self.splitter.status(input_path)

        print(f"\n[MERGE] Status part:")
        print(f"        Total  : {status['total_parts']}")
        print(f"        Selesai: {len(status['done'])}")
        print(f"        Pending: {len(status['pending'])}")

        if status["pending"] and not force:
            print("\n[MERGE] ✗ Belum semua part selesai diterjemahkan:")
            for p in status["pending"]:
                print(f"          - {Path(p).name}")
            print("\n        Selesaikan semua part terlebih dahulu,")
            print("        atau gunakan --force untuk merge part yang sudah selesai saja.")
            return False

        # Tentukan part yang akan di-merge
        parts_to_merge = status["done"]
        if not parts_to_merge:
            print("[MERGE] Tidak ada part yang selesai untuk digabungkan.")
            return False

        if status["pending"] and force:
            print(f"\n[MERGE] ⚠ Mode force: {len(status['pending'])} part dilewati.")

        # Render tiap part ke PDF sementara
        rendered_paths = []
        parts_dir      = Path(input_path).parent / f"{Path(input_path).stem}_parts"
        render_dir     = parts_dir / "rendered"
        render_dir.mkdir(exist_ok=True)

        print(f"\n[MERGE] Render {len(parts_to_merge)} part...")

        for i, part_path in enumerate(sorted(parts_to_merge)):
            part_name    = Path(part_path).stem
            rendered_out = render_dir / f"{part_name}_rendered.pdf"

            if rendered_out.exists():
                print(f"  [{i+1}/{len(parts_to_merge)}] {part_name} — sudah dirender, skip")
            else:
                print(f"  [{i+1}/{len(parts_to_merge)}] Render {part_name}...")
                # Gunakan config dengan font_size yang diminta
                cfg_render = Config(
                    yolo_model   = self.cfg.yolo_model,
                    font_path    = self.cfg.font_path,
                    ollama_model = self.cfg.ollama_model,
                    source_lang  = self.cfg.source_lang,
                    font_size    = font_size,
                    render_dpi   = self.cfg.render_dpi,
                )
                render(cfg_render, part_path, str(rendered_out))

            rendered_paths.append(str(rendered_out))

        # Gabungkan semua PDF yang sudah dirender
        print(f"\n[MERGE] Menggabungkan {len(rendered_paths)} file PDF...")
        self._combine(rendered_paths, output_path)

        print(f"[MERGE] ✓ Selesai! Output: {output_path}")
        return True

    def _combine(self, pdf_paths: list[str], output_path: str):
        """Gabungkan daftar file PDF menjadi satu file."""
        output_doc = fitz.open()

        for path in sorted(pdf_paths):
            src = fitz.open(path)
            output_doc.insert_pdf(src)
            src.close()
            print(f"  + {Path(path).name} ({src.page_count if hasattr(src, 'page_count') else '?'} hal)")

        output_doc.save(output_path, deflate=True)
        output_doc.close()
        print(f"[MERGE] Tersimpan: {output_path}")
