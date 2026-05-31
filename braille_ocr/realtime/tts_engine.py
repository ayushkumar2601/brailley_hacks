"""
tts_engine.py
-------------
Thread-safe Text-to-Speech engine for the Braille OCR scanner.

Supports:
  - pyttsx3 (cross-platform, works offline)
  - macOS 'say' command (fallback)
  - Web Speech API hint (browser-side TTS, handled in JS)

The engine runs speech in a background thread so it never blocks the
Flask request handlers.
"""

import subprocess
import sys
import threading
import queue
import time
from typing import Optional


class TTSEngine:
    """
    Thread-safe TTS engine with a priority queue.

    Usage:
        tts = TTSEngine(rate=175, volume=1.0)
        tts.speak("Hello world")
        tts.speak("Urgent message", priority=True)
    """

    def __init__(self, rate: int = 175, volume: float = 1.0):
        self._rate   = max(80, min(300, rate))
        self._volume = max(0.0, min(1.0, volume))

        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._lock  = threading.Lock()
        self._seq   = 0          # tie-breaker for equal priorities
        self._engine = None      # pyttsx3 engine (lazy-init in worker thread)
        self._use_pyttsx3 = True

        # Worker thread
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    # ── Public API ─────────────────────────────────────────────────────────────

    def speak(self, text: str, priority: bool = False) -> None:
        """Queue *text* for speech. priority=True jumps the queue."""
        if not text or not text.strip():
            return
        with self._lock:
            self._seq += 1
            prio = 0 if priority else 1
            self._queue.put((prio, self._seq, text.strip()))

    def stop(self) -> None:
        """Drain the queue (does not interrupt current utterance)."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    # ── Internal ───────────────────────────────────────────────────────────────

    def _worker(self) -> None:
        """Background thread: drain the queue and speak each item."""
        # Try to init pyttsx3 once in this thread (required on some platforms)
        self._engine = self._init_pyttsx3()

        while True:
            try:
                _, _, text = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            self._say(text)

    def _init_pyttsx3(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate",   self._rate)
            engine.setProperty("volume", self._volume)
            print("✅ TTS Engine: pyttsx3 ready")
            return engine
        except Exception as e:
            print(f"⚠️  pyttsx3 unavailable ({e}), falling back to system TTS")
            self._use_pyttsx3 = False
            return None

    def _say(self, text: str) -> None:
        # Apply current rate/volume settings before each utterance
        if self._engine and self._use_pyttsx3:
            try:
                self._engine.setProperty("rate",   self._rate)
                self._engine.setProperty("volume", self._volume)
                self._engine.say(text)
                self._engine.runAndWait()
                return
            except Exception as e:
                print(f"⚠️  pyttsx3 speak error: {e}")
                self._use_pyttsx3 = False

        # macOS fallback
        if sys.platform == "darwin":
            try:
                safe = text.replace('"', '\\"').replace("$", "\\$")
                subprocess.run(
                    ["say", "-r", str(self._rate), safe],
                    check=True, timeout=30,
                )
                return
            except Exception as e:
                print(f"⚠️  macOS say error: {e}")

        # Last resort: just print
        print(f"📢 TTS (no engine): {text}")

    # ── Voice listing (for UI dropdown) ───────────────────────────────────────

    def get_voices(self) -> list:
        """Return list of available voice dicts: {id, name, lang}."""
        voices = []
        if self._engine and self._use_pyttsx3:
            try:
                for v in self._engine.getProperty("voices"):
                    voices.append({
                        "id":   v.id,
                        "name": v.name,
                        "lang": getattr(v, "languages", [""])[0] if hasattr(v, "languages") else "",
                    })
            except Exception:
                pass
        return voices

    def set_voice(self, voice_id: str) -> bool:
        """Set the TTS voice by ID. Returns True on success."""
        if self._engine and self._use_pyttsx3:
            try:
                self._engine.setProperty("voice", voice_id)
                return True
            except Exception:
                pass
        return False


# ── Convenience function ──────────────────────────────────────────────────────

def text_to_speech(text: str, rate: int = 175) -> bool:
    """One-shot TTS (blocking). Useful for scripts."""
    engine = TTSEngine(rate=rate)
    engine.speak(text)
    time.sleep(0.5)  # give the worker thread a moment to start
    return True


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing TTS Engine...")
    tts = TTSEngine(rate=175)
    tts.speak("Hello! Braille OCR is working.", priority=True)
    time.sleep(4)
    print("✅ TTS test complete")
