"""
camera_loop.py
--------------
Real-time frame processing for the Braille scanner.

Supports:
  - OpenCV webcam (macOS will prompt for Camera if AVFOUNDATION_SKIP_AUTH is not set)
  - Browser webcam via POST /api/process_frame (permission in Chrome/Safari, not Terminal)
"""

import base64
import os
import threading
import time
from typing import Optional

import cv2
import numpy as np

from braille_ocr.realtime.braille_detector import (
    SPEAK_MIN_CHARS,
    detect_braille,
    braille_to_english,
    DotInfo,
)
from braille_ocr.realtime.frame_analyzer import analyze_frame
from braille_ocr.realtime.session import ScanSession
from braille_ocr.realtime.tts_engine import TTSEngine

_FEEDBACK_MESSAGES = {
    "TOO_DARK":    "The image is too dark. Please improve the lighting.",
    "TOO_BRIGHT":  "Too much glare. Try reducing the light source.",
    "BLURRY":      "Image is blurry. Hold the camera steady.",
    "MOVE_CLOSER": "Move the camera closer to the braille page.",
    "MOVE_BACK":   "Move the camera back a little.",
    "NO_BRAILLE":  "",
    "OK":          "",
}


class CameraLoop:
    def __init__(
        self,
        tts: TTSEngine,
        session: ScanSession,
        camera_index: int = 0,
        target_fps: int = 8,
    ):
        self.tts = tts
        self.session = session
        self.camera_index = camera_index
        self.target_fps = target_fps

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self._latest_jpeg: bytes = b""
        self._latest_status: dict = {
            "quality": "NO_CAMERA",
            "braille_detected": False,
            "dot_count": 0,
            "last_text": "",
            "confidence": 0.0,
            "camera_source": "none",
        }
        self.running = False
        self.browser_mode = False

    def start(self) -> bool:
        if self._thread and self._thread.is_alive():
            return True
        self.browser_mode = False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.running = True
        return True

    def stop(self) -> None:
        self._stop_event.set()
        self.running = False
        if self._thread:
            self._thread.join(timeout=3.0)

    def restart_opencv_camera(self) -> dict:
        """Stop and restart OpenCV capture (triggers macOS permission if needed)."""
        self.stop()
        time.sleep(0.3)
        self.start()
        with self._lock:
            quality = self._latest_status.get("quality", "STARTING")
        return {
            "ok": quality not in ("NO_CAMERA",),
            "quality": quality,
            "message": (
                "Camera opened."
                if quality not in ("NO_CAMERA",)
                else "Camera not available. Use the browser Allow Camera button."
            ),
        }

    def get_latest_frame_b64(self) -> str:
        with self._lock:
            data = self._latest_jpeg
        if not data:
            return ""
        return base64.b64encode(data).decode("utf-8")

    def get_status(self) -> dict:
        with self._lock:
            return dict(self._latest_status)

    def process_bgr_frame(self, frame: np.ndarray, source: str = "browser") -> dict:
        """Analyse one BGR frame; update shared JPEG buffer and status."""
        if self.session.is_paused:
            with self._lock:
                st = dict(self._latest_status)
                st["paused"] = True
            return st

        analysis = analyze_frame(frame)
        quality = analysis["quality"]
        annotated = analysis["annotated"]
        confidence = 0.0

        feedback_msg = _FEEDBACK_MESSAGES.get(quality, "")
        if feedback_msg and self.session.should_speak_feedback(quality):
            self.tts.speak(feedback_msg, priority=False)

        if quality in ("OK", "MOVE_CLOSER", "MOVE_BACK") and analysis["braille_detected"]:
            result = detect_braille(analysis["gray"], camera_mode=True)
            confidence = result.confidence

            # Draw per-dot coloured circles (green=good, yellow=ok, red=poor)
            for dot in result.dots:
                cv2.circle(annotated, (dot.x, dot.y), max(dot.r + 2, 5), dot.colour, 2)

            if result.valid:
                # Draw cell bounding boxes
                for i, (x, y, bw, bh) in enumerate(result.boxes):
                    conf_i = result.per_cell_conf[i] if i < len(result.per_cell_conf) else 0.5
                    box_colour = (
                        (0, 220, 100) if conf_i >= 0.7 else
                        (0, 200, 220) if conf_i >= 0.4 else
                        (60, 60, 220)
                    )
                    cv2.rectangle(annotated, (x, y), (x + bw, y + bh), box_colour, 2)

                english = braille_to_english(result.text)
                if english and len(english) >= SPEAK_MIN_CHARS:
                    cv2.putText(
                        annotated, f"Reading: {english}",
                        (12, annotated.shape[0] - 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 120), 2,
                    )
                    if self.session.add_text(english, confidence=confidence):
                        self.tts.speak(english)
            elif result.message == "low_confidence" and self.session.should_speak_feedback("HOLD_STEADY"):
                self.tts.speak("Hold steady over the braille.", priority=False)

        self.session.tick(analysis["braille_detected"])
        _, jpeg_buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
        status = {
            "quality":          quality,
            "braille_detected": analysis["braille_detected"],
            "dot_count":        analysis["dot_count"],
            "last_text":        self.session.last_text,
            "confidence":       round(confidence, 2),
            "camera_source":    source,
        }
        self._update_status(status, jpeg_buf.tobytes())
        return status

    def process_gray_frame(self, gray: np.ndarray, annotated_bgr: np.ndarray) -> dict:
        """Run detection on a single frame (demo endpoint)."""
        result = detect_braille(gray)
        conf = round(result.confidence, 2)
        if result.valid and result.boxes:
            for (x, y, bw, bh) in result.boxes:
                cv2.rectangle(annotated_bgr, (x, y), (x + bw, y + bh), (0, 220, 100), 2)
            english = braille_to_english(result.text)
            cv2.putText(
                annotated_bgr, f"{english} ({conf})",
                (12, annotated_bgr.shape[0] - 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 120), 2,
            )
            return {
                "text": english,
                "confidence": conf,
                "valid": True,
                "dot_count": result.dot_count,
                "annotated": annotated_bgr,
            }
        return {
            "text": "",
            "confidence": conf,
            "valid": False,
            "dot_count": result.dot_count,
            "message": result.message,
            "annotated": annotated_bgr,
        }

    def _loop(self) -> None:
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self._update_status({
                "quality": "NO_CAMERA",
                "braille_detected": False,
                "dot_count": 0,
                "last_text": self.session.last_text,
                "confidence": 0.0,
                "camera_source": "opencv",
            })
            self._push_placeholder(
                "No system camera.\nClick Allow Camera below\n(browser permission)."
            )
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        frame_interval = 1.0 / self.target_fps

        with self._lock:
            if self._latest_status.get("quality") == "NO_CAMERA":
                self.tts.speak("System camera active.", priority=False)

        while not self._stop_event.is_set():
            if self.browser_mode:
                time.sleep(0.2)
                continue

            t0 = time.time()
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            self.process_bgr_frame(frame, source="opencv")

            elapsed = time.time() - t0
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        cap.release()

    def _update_status(self, status: dict, jpeg: bytes = None) -> None:
        with self._lock:
            self._latest_status = status
            if jpeg is not None:
                self._latest_jpeg = jpeg

    def _push_placeholder(self, message: str) -> None:
        img = np.zeros((360, 640, 3), dtype=np.uint8)
        img[:] = (30, 30, 40)
        cv2.putText(img, "CAMERA", (250, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (120, 120, 140), 2)
        for i, line in enumerate(message.split("\n")):
            y = 200 + i * 28
            tw = len(line) * 9
            x = max(10, (640 - tw) // 2)
            cv2.putText(img, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 200), 1)
        _, jpeg_buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        with self._lock:
            self._latest_jpeg = jpeg_buf.tobytes()
