"""
splitter.py — Pecah PDF besar menjadi beberapa part kecil.

Alasan:
  Dengan PC yang hanya menyala 3 jam/hari, komik tebal (100+ halaman)
  tidak mungkin selesai dalam satu sesi. Dengan memecah per 50 halaman,
  setiap sesi bisa menyelesaikan 1-2 part, lalu keesokan harinya lanjut
  ke part berikutnya. Setelah semua part selesai, digabung ulang.

Strategi resume:
  Part yang sudah punya stage2_translated.json di work_dir-nya
  dianggap SELESAI dan dilewati saat translate berjalan.
  Sehingga aman untuk menjalankan ulang pipeline tanpa mengulang
  part yang sudah beres.

Format nama file part:
  komik.pdf → komik_part001.pdf, komik_part002.pdf, dst.
  Disimpan di subfolder: komik_parts/
"""

import fitz
from pathlib import Path

from .config import Config


class PDFSplitter:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def split(self, input_path: str, pages_per_part: int = 50) -> list[str]:
        """
        Pecah PDF menjadi beberapa file part.

        Args:
            input_path     : path file PDF asli
            pages_per_part : jumlah halaman per part (default: 50)

        Return:
            list of str — path tiap file part yang dihasilkan.
            Jika PDF sudah kecil (<= pages_per_part), kembalikan [input_path]
            tanpa memecah.
        """
        doc        = fitz.open(input_path)
        total      = len(doc)
        input_path = Path(input_path)

        # Tidak perlu dipecah
        if total <= pages_per_part:
            print(f"[SPLIT] PDF hanya {total} halaman, tidak perlu dipecah.")
            doc.close()
            return [str(input_path)]

        # Folder output untuk part-part
        parts_dir = input_path.parent / f"{input_path.stem}_parts"
        parts_dir.mkdir(exist_ok=True)

        parts      = []
        part_num   = 1
        start_page = 0

        print(f"[SPLIT] {total} halaman → dipecah per {pages_per_part} halaman")
        print(f"[SPLIT] Folder part: {parts_dir}")

        while start_page < total:
            end_page = min(start_page + pages_per_part, total)
            out_name = f"{input_path.stem}_part{part_num:03d}.pdf"
            out_path = parts_dir / out_name

            if out_path.exists():
                print(f"  [SKIP] {out_name} sudah ada")
            else:
                part_doc = fitz.open()
                part_doc.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
                part_doc.save(str(out_path))
                part_doc.close()
                print(f"  Part {part_num:03d}: halaman {start_page+1}–{end_page} → {out_name}")

            parts.append(str(out_path))
            start_page += pages_per_part
            part_num   += 1

        doc.close()
        total_parts = len(parts)
        print(f"[SPLIT] Selesai: {total_parts} part")
        return parts

    def get_existing_parts(self, input_path: str) -> list[str]:
        """
        Kembalikan daftar part yang sudah ada di folder parts,
        diurutkan berdasarkan nomor part.
        Berguna untuk resume tanpa perlu split ulang.
        """
        input_path = Path(input_path)
        parts_dir  = input_path.parent / f"{input_path.stem}_parts"

        if not parts_dir.exists():
            return []

        parts = sorted(parts_dir.glob(f"{input_path.stem}_part*.pdf"))
        return [str(p) for p in parts]

    def status(self, input_path: str) -> dict:
        """
        Cek status tiap part: sudah selesai diterjemahkan atau belum.

        Return dict:
        {
          "total_parts": 3,
          "done": ["komik_part001.pdf", ...],
          "pending": ["komik_part002.pdf", ...],
        }
        """
        parts    = self.get_existing_parts(input_path)
        done     = []
        pending  = []

        for part_path in parts:
            stage2 = self.cfg.stage2_json(part_path)
            if stage2.exists():
                done.append(part_path)
            else:
                pending.append(part_path)

        return {
            "total_parts": len(parts),
            "done":        done,
            "pending":     pending,
        }
