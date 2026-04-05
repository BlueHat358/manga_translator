"""
translator.py — Terjemahan teks via Ollama (local LLM).

Menggunakan library native `ollama` (bukan openai) sehingga:
- Parameter think=False berfungsi dengan benar untuk menonaktifkan
  thinking mode pada model seperti Qwen3.5
- Tidak ada overhead parsing response OpenAI-compatible
- Akses langsung ke fitur Ollama seperti think, options, dll.

Install: pip install ollama
"""

import ollama

from .config import Config


class OllamaTranslator:
  def __init__(self, cfg: Config):
    self.cfg = cfg
    self.client = self._connect()

  def _connect(self) -> ollama.Client:
    # Ambil host dari URL, buang path /v1 jika ada
    host = self.cfg.ollama_url.replace("/v1", "")
    print(f"[OLLAMA] Menghubungi {host}  model={self.cfg.ollama_model}")

    client = ollama.Client(host=host)
    self._test_connection(client)
    return client

  def _test_connection(self, client: ollama.Client):
    """Kirim teks pendek untuk verifikasi koneksi dan model tersedia."""
    test_texts = {"ja": "テスト", "ch": "测试", "korean": "테스트"}
    test_src = test_texts.get(self.cfg.source_lang, "test")
    try:
      result = self._call(client, test_src)
      print(f"[OLLAMA] OK → '{test_src}' = '{result}'")
    except ollama.ResponseError as e:
      raise ConnectionError(
          f"Model tidak ditemukan atau error: {e}\n"
          f"Jalankan: ollama pull {self.cfg.ollama_model}"
      )
    except Exception as e:
      raise ConnectionError(
          f"Tidak bisa terhubung ke Ollama: {e}\n"
          f"Pastikan Ollama berjalan: sudo systemctl start ollama\n"
          f"Dan model tersedia: ollama pull {self.cfg.ollama_model}"
      )

  def _build_messages(self, text: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                f"You are a manga/comic translator. "
                f"Translate from {self.cfg.lang_name()} to {self.cfg.target_lang}. "
                f"Output ONLY the translated text, no explanation, no quotes."
            ),
        },
        {
            "role": "user",
            # /no_think sebagai fallback tambahan untuk model yang
            # belum mendukung parameter think=False via API
            "content": f"{text} /no_think",
        },
    ]

  def _call(self, client: ollama.Client, text: str) -> str:
    resp = client.chat(
        model=self.cfg.ollama_model,
        messages=self._build_messages(text),
        think=False,   # nonaktifkan thinking mode (Qwen3.x, DeepSeek-R1, dll)
        options={
            "temperature": 0.3,   # rendah = konsisten, tidak terlalu kreatif
            "num_predict": 256,   # max token output
        },
    )
    return resp.message.content.strip()

  def translate(self, text: str) -> str:
    """
    Terjemahkan satu string teks.
    Return teks asli jika Ollama gagal merespons.
    """
    if not text.strip():
      return ""
    try:
      return self._call(self.client, text)
    except Exception as e:
      print(f"    [TRANSLATE] Error: {e}")
      return text  # fallback: kembalikan teks asli
