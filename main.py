#!/usr/bin/env python3
"""
main.py — Entry point CLI untuk Manga/Comic PDF Translator.

Subcommand:
    translate   Terjemahkan PDF (langsung atau per part)
    split       Pecah PDF besar menjadi part-part kecil
    merge       Gabungkan semua part yang sudah selesai
    status      Cek progress tiap part

Cara pakai:
    # Komik kecil — langsung terjemahkan
    python main.py translate -i komik.pdf -o hasil.pdf
    
    # Dengan jeda 3 menit sebelum shutdown
    python main.py translate -i komik.pdf -o hasil.pdf --shutdown --shutdown-delay 3

    # Komik besar — pecah dulu, terjemahkan part per part, lalu gabung
    python main.py split   -i komik.pdf --pages 50
    python main.py status  -i komik.pdf
    python main.py translate -i komik_parts/komik_part001.pdf -o /dev/null
    python main.py translate -i komik_parts/komik_part001.pdf -o /dev/null --shutdown
    python main.py translate -i komik_parts/komik_part002.pdf -o /dev/null
    python main.py merge   -i komik.pdf -o komik_id.pdf

    # Resume tahap tertentu pada satu part
    python main.py translate -i komik_parts/komik_part001.pdf -o /dev/null --stage 2
"""

import argparse
import sys
import pydoc

from src import pipeline
from src.config import Config
from src.splitter import PDFSplitter
from src.merger import PDFMerger
from src.shutdown import schedule_shutdown


# ─────────────────────────────────────────────
# Argumen yang dipakai di banyak subcommand
# ─────────────────────────────────────────────

def add_shutdown_args(parser: argparse.ArgumentParser):
  """Tambahkan argumen --shutdown ke subcommand."""
  parser.add_argument(
      "--shutdown", action="store_true",
      help="Shutdown PC otomatis setelah selesai"
  )
  parser.add_argument(
      "--shutdown-delay", type=int, default=1, metavar="MENIT",
      help="Jeda sebelum shutdown dalam menit (default: 1)"
  )


def maybe_shutdown(args):
  """Jalankan shutdown jika flag --shutdown aktif."""
  if getattr(args, "shutdown", False):
    schedule_shutdown(delay_minutes=args.shutdown_delay)


def add_common_args(parser: argparse.ArgumentParser):
  """Argumen konfigurasi yang dipakai oleh beberapa subcommand."""
  parser.add_argument("--lang", "-l", default="ja",
                      choices=["ja", "ch", "korean"],
                      help="Bahasa sumber: ja=Jepang, ch=China, korean=Korea (default: ja)")
  parser.add_argument("--model", "-m", default=Config.ollama_model,
                      help=f"Model Ollama (default: {Config.ollama_model})")
  parser.add_argument("--yolo", default=Config.yolo_model,
                      help=f"Path YOLO model .pt (default: {Config.yolo_model})")
  parser.add_argument("--font", default=Config.font_path,
                      help=f"Path font TTF (default: {Config.font_path})")
  parser.add_argument("--font-size", "-f", type=int, default=Config.font_size,
                      help=f"Ukuran font terjemahan (default: {Config.font_size})")
  parser.add_argument("--dpi", type=int, default=Config.render_dpi,
                      help=f"DPI render halaman (default: {Config.render_dpi})")
  parser.add_argument("--conf", type=float, default=Config.yolo_conf,
                      help=f"Confidence threshold YOLO (default: {Config.yolo_conf})")


def make_config(args) -> Config:
  """Bangun Config dari argumen yang sudah di-parse."""
  return Config(
      yolo_model=args.yolo,
      font_path=args.font,
      ollama_model=args.model,
      source_lang=args.lang,
      font_size=args.font_size,
      render_dpi=args.dpi,
      yolo_conf=args.conf,
  )


def print_header(cfg: Config, input_path: str, output_path: str = ""):
  print(f"\n{'═' * 55}")
  print(f"  Manga Translator")
  print(f"{'═' * 55}")
  print(f"  Input    : {input_path}")
  if output_path:
    print(f"  Output   : {output_path}")
  print(f"  Bahasa   : {cfg.source_lang} → {cfg.target_lang}")
  print(f"  Ollama   : {cfg.ollama_model}")
  print(f"{'═' * 55}")


# ─────────────────────────────────────────────
# Subcommand: translate
# ─────────────────────────────────────────────

def cmd_translate(args):
  """Terjemahkan satu file PDF (atau satu part)."""
  cfg = make_config(args)
  print_header(cfg, args.input, args.output)

  stage = args.stage  # 0 = semua tahap

  if stage in (0, 1):
    pipeline.detect_and_ocr(cfg, args.input)

  if stage in (0, 2):
    pipeline.translate(cfg, args.input)

  if stage in (0, 3):
    pipeline.render(cfg, args.input, args.output)

  if stage == 0:
    print(f"\n{'═' * 55}")
    print(f"  ✓ Selesai! Output: {args.output}")
    print(f"{'═' * 55}")


# ─────────────────────────────────────────────
# Subcommand: split
# ─────────────────────────────────────────────

def cmd_split(args):
  """Pecah PDF besar menjadi beberapa part."""
  cfg = make_config(args)
  splitter = PDFSplitter(cfg)
  parts = splitter.split(args.input, pages_per_part=args.pages)

  print(f"\n[SPLIT] {len(parts)} part siap di folder:")
  for p in parts:
    print(f"  {p}")

  print(f"\nLangkah selanjutnya:")
  print(f"  python main.py status -i {args.input}")
  for p in parts:
    print(
      f"  python main.py translate -i \"{p}\" -o /dev/null --lang {args.lang}")
  print(
    f"  python main.py merge -i \"{args.input}\" -o hasil_final.pdf --lang {args.lang}")


# ─────────────────────────────────────────────
# Subcommand: status
# ─────────────────────────────────────────────

def cmd_status(args):
  """Tampilkan progress tiap part."""
  cfg = make_config(args)
  splitter = PDFSplitter(cfg)
  status = splitter.status(args.input)

  print(f"\n{'═' * 55}")
  print(f"  Status: {args.input}")
  print(f"{'═' * 55}")
  print(f"  Total part : {status['total_parts']}")
  print(f"  Selesai    : {len(status['done'])}")
  print(f"  Pending    : {len(status['pending'])}")

  if status["done"]:
    print(f"\n  ✓ Selesai:")
    for p in status["done"]:
      print(f"    {p}")

  if status["pending"]:
    print(f"\n  ✗ Belum selesai:")
    for p in status["pending"]:
      print(f"    {p}")
    print(f"\n  Perintah untuk melanjutkan:")
    for p in status["pending"]:
      print(
        f"    python main.py translate -i \"{p}\" -o /dev/null --lang {args.lang}")

  if not status["pending"] and status["total_parts"] > 0:
    print(f"\n  Semua part selesai! Jalankan merge:")
    print(
      f"    python main.py merge -i \"{args.input}\" -o hasil_final.pdf --lang {args.lang}")


# ─────────────────────────────────────────────
# Subcommand: merge
# ─────────────────────────────────────────────

def cmd_merge(args):
  """Gabungkan semua part yang sudah selesai menjadi satu PDF."""
  cfg = make_config(args)
  merger = PDFMerger(cfg)
  print_header(cfg, args.input, args.output)

  ok = merger.merge(
      input_path=args.input,
      output_path=args.output,
      font_size=args.font_size,
      force=args.force,
  )

  if not ok:
    sys.exit(1)


# ─────────────────────────────────────────────
# Parser utama
# ─────────────────────────────────────────────

MAN_PAGE = """\
NAMA
       manga_translator - CLI untuk Manga/Comic PDF Translator (CPU Optimized + Ollama)

RINGKASAN
       python main.py <subcommand> [options]

DESKRIPSI
       Manga/Comic PDF Translator adalah alat CLI untuk menerjemahkan komik atau 
       manga dalam format PDF. Alat ini dioptimalkan untuk CPU menggunakan 
       deteksi teks dari YOLO dan terjemahan menggunakan mesin AI lokal (Ollama).

       Aplikasi ini dirancang mendukung mode per-part, sangat andal untuk
       memproses file komik berukuran besar tanpa memberatkan RAM berlebihan.

SUBCOMMANDS
       translate   Terjemahkan satu file PDF. Terdapat 3 tahapan operasi:
                   (1) Deteksi OCR (YOLO), (2) Translasi (Ollama), (3) Render PDF.

       split       Pecah file PDF besar menjadi beberapa bagian (part) kecil.

       status      Cek status progres penerjemahan dokumen yang telah dipecah.

       merge       Gabungkan semua part PDF yang selesai menjadi satu dokumen utuh.

OPSI UMUM (COMMON OPTIONS)
       Hampir seluruh subcommand mendukung argumen konfigurasi tambahan berikut:

       -l, --lang <bahasa>   Bahasa teks sumber komik (ja, ch, korean). Default: ja
       -m, --model <model>   Nama model Ollama yang digunakan.
       -f, --font-size <n>   Ukuran font teks terjemahan yang dirender.
       --font <path>         Path file font .ttf yang digunakan.
       --dpi <int>           DPI resolusi saat me-render halaman.
       --yolo <path>         Path file model YOLO (.pt) untuk deteksi bubble.
       --conf <float>        Confidence threshold YOLO untuk deteksi teks.

OPSI SHUTDOWN (Tidak tersedia di subcommand status)
       --shutdown            Shutdown PC otomatis setelah proses selesai.
       --shutdown-delay <n>  Jeda waktu (dalam menit) sebelum PC dimatikan (default: 1).

WORKFLOW KOMIK BESAR (Misal: 200 halaman)
       Hari 1 - Pecah dan mulai part pertama
         $ python main.py split -i komik.pdf --pages 50
         $ python main.py translate -i komik_parts/komik_part001.pdf -o /dev/null

       Hari 2 - Cek status bagian yang tertinggal dan lanjutkan part berikutnya
         $ python main.py status -i komik.pdf
         $ python main.py translate -i komik_parts/komik_part002.pdf -o /dev/null

       Selesai - Setelah status semua part '✓ Selesai', gabungkan kembali
         $ python main.py merge -i komik.pdf -o komik_ind.pdf
"""


class ManHelpAction(argparse.Action):
  def __init__(self, option_strings, dest=argparse.SUPPRESS, default=argparse.SUPPRESS, help=None):
    super().__init__(option_strings=option_strings,
                     dest=dest, default=default, nargs=0, help=help)

  def __call__(self, parser, namespace, values, option_string=None):
    pydoc.pager(parser.format_help())
    parser.exit()


def build_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
      prog="manga_translator",
      description=MAN_PAGE,
      formatter_class=argparse.RawDescriptionHelpFormatter,
      add_help=False
  )

  # Custom help argumen menyerupai man terminal
  parser.add_argument("-h", "--help", action=ManHelpAction,
                      help="Tampilkan halaman bantuan lengkap (man page) dan keluar")

  sub = parser.add_subparsers(dest="command", required=True)

  # ── translate ──────────────────────────────────────
  p_translate = sub.add_parser("translate",
                               help="Terjemahkan satu file PDF (atau satu part)",
                               )
  p_translate.add_argument(
      "--input", "-i", required=True, help="Path PDF input")
  p_translate.add_argument(
      "--output", "-o", required=True, help="Path PDF output")
  p_translate.add_argument("--stage", "-s", type=int, choices=[1, 2, 3], default=0,
                           help="Jalankan hanya tahap 1/2/3. Default: semua")
  add_common_args(p_translate)
  add_shutdown_args(p_translate)
  p_translate.set_defaults(func=cmd_translate)

  # ── split ──────────────────────────────────────────
  p_split = sub.add_parser("split",
                           help="Pecah PDF besar menjadi beberapa part",
                           )
  p_split.add_argument("--input", "-i", required=True, help="Path PDF input")
  p_split.add_argument("--pages", "-p", type=int, default=50,
                       help="Jumlah halaman per part (default: 50)")
  add_common_args(p_split)
  add_shutdown_args(p_split)
  p_split.set_defaults(func=cmd_split)

  # ── status ─────────────────────────────────────────
  p_status = sub.add_parser("status",
                            help="Cek progress tiap part",
                            )
  p_status.add_argument("--input", "-i", required=True, help="Path PDF asli")
  add_common_args(p_status)
  p_status.set_defaults(func=cmd_status)

  # ── merge ──────────────────────────────────────────
  p_merge = sub.add_parser("merge",
                           help="Gabungkan semua part selesai menjadi satu PDF",
                           )
  p_merge.add_argument("--input", "-i", required=True, help="Path PDF asli")
  p_merge.add_argument("--output", "-o", required=True,
                       help="Path PDF output final")
  p_merge.add_argument("--force", action="store_true",
                       help="Paksa merge meski ada part yang belum selesai")
  add_common_args(p_merge)
  add_shutdown_args(p_merge)
  p_merge.set_defaults(func=cmd_merge)

  return parser


def main():
  parser = build_parser()

  # Tampilkan help/man page jika tidak ada argumen sama sekali
  if len(sys.argv) == 1:
    pydoc.pager(parser.format_help())
    sys.exit(0)

  args = parser.parse_args()

  try:
    args.func(args)
  finally:
    maybe_shutdown(args)


if __name__ == "__main__":
  main()
