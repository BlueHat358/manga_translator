"""
shutdown.py — Helper untuk shutdown otomatis setelah proses selesai.

Catatan:
  `shutdown now` di Linux modern (systemd) TIDAK butuh sudo untuk user
  yang sedang login di sesi aktif. systemd mengizinkan ini via polkit.

  Ollama tidak perlu di-stop manual — systemd akan stop semua service
  secara otomatis saat shutdown, termasuk ollama.service.

Cara pakai dari CLI:
  python main.py translate -i komik.pdf -o hasil.pdf --shutdown
  python main.py translate -i komik.pdf -o hasil.pdf --shutdown --shutdown-delay 3
"""

import subprocess
import time
import sys


def schedule_shutdown(delay_minutes: int = 1):
  """
  Shutdown PC setelah countdown.

  Args:
      delay_minutes : jeda sebelum shutdown dalam menit (default: 1)

  Catatan:
      Ollama tidak perlu di-stop manual — systemd stop semua service
      saat shutdown, termasuk ollama.service.
  """
  print(f"\n{'═' * 55}")
  print(f"  ⏻  Shutdown dalam {delay_minutes} menit...")
  print(f"  Tekan Ctrl+C untuk membatalkan.")
  print(f"{'═' * 55}")

  try:
    for remaining in range(delay_minutes * 60, 0, -1):
      mins, secs = divmod(remaining, 60)
      if sys.stdout.isatty():
        print(
          f"\r  Shutdown dalam {mins:02d}:{secs:02d} ...", end="", flush=True)
      else:
        if remaining % 60 == 0:
          print(f"  Shutdown dalam {mins:02d}:00 ...", flush=True)
      time.sleep(1)
  except KeyboardInterrupt:
    print("\n\n  ✗ Shutdown dibatalkan.")
    return

  print("\n  Menjalankan shutdown...")

  # shutdown now tidak butuh sudo untuk user login aktif di systemd
  methods = [
      ["shutdown", "now"],
      ["systemctl", "poweroff"],
  ]

  for cmd in methods:
    try:
      result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
      if result.returncode == 0:
        print(f"  ✓ Shutdown via: {' '.join(cmd)}")
        return
    except (subprocess.TimeoutExpired, FileNotFoundError):
      continue

  print("  ✗ Shutdown gagal. Jalankan manual: shutdown now")
