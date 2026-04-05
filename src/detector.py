"""
detector.py — Deteksi speech bubble menggunakan YOLOv8.

Optimasi CPU:
- Model .pt otomatis di-export ke ONNX saat pertama kali dijalankan
- ONNX runtime jauh lebih cepat dari PyTorch untuk inferensi CPU
- Export hanya dilakukan sekali, hasil disimpan di samping file .pt
"""

import os
from pathlib import Path

from .config import Config


class BubbleDetector:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.model = self._load()

    def _export_to_onnx(self, pt_path: str) -> str:
        """Export .pt ke ONNX. Hanya dilakukan sekali."""
        onnx_path = pt_path.replace(".pt", "_cpu.onnx")
        if os.path.exists(onnx_path):
            return onnx_path

        print("[YOLO] Export ke ONNX (pertama kali, mohon tunggu)...")
        from ultralytics import YOLO
        m = YOLO(pt_path)
        m.export(format="onnx", imgsz=640, simplify=True, opset=12)

        # Ultralytics menyimpan .onnx di direktori yang sama dengan .pt
        default_onnx = pt_path.replace(".pt", ".onnx")
        if os.path.exists(default_onnx):
            os.rename(default_onnx, onnx_path)

        print(f"[YOLO] ONNX tersimpan: {onnx_path}")
        return onnx_path

    def _load(self):
        from ultralytics import YOLO

        pt_path = self.cfg.yolo_model
        if not os.path.exists(pt_path):
            raise FileNotFoundError(
                f"YOLO model tidak ditemukan: {pt_path}\n"
                "Download: https://huggingface.co/ogkalu2/comic-speech-bubble-detector-yolov8m"
            )

        if pt_path.endswith(".pt"):
            try:
                onnx_path = self._export_to_onnx(pt_path)
                model = YOLO(onnx_path, task="detect")
                print("[YOLO] Loaded via ONNX (CPU optimized)")
                return model
            except Exception as e:
                print(f"[YOLO] ONNX gagal ({e}), fallback ke .pt")

        model = YOLO(pt_path)
        print("[YOLO] Loaded via PyTorch")
        return model

    def detect(self, image_np) -> list[list[int]]:
        """
        Deteksi bubble pada image numpy array.
        Return: list of [x1, y1, x2, y2]
        """
        results = self.model(image_np, conf=self.cfg.yolo_conf, verbose=False)
        boxes = results[0].boxes.xyxy.cpu().numpy().tolist()
        return [[int(x1), int(y1), int(x2), int(y2)] for x1, y1, x2, y2 in boxes]

    def unload(self):
        """Bebaskan model dari RAM."""
        del self.model
        self.model = None
