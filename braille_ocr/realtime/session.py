"""
session.py
----------
Manages the state of a live scanning session:
  - history of all recognised text segments
  - last spoken feedback message (to avoid repeating)
  - replay buffer
  - session statistics
"""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional


@dataclass
class TextSegment:
    text: str
    timestamp: float = field(default_factory=time.time)
    source: str = "camera"   # "camera" | "manual"


class ScanSession:
    """
    Holds all state for one live scanning session.

    Thread-safe for reads; writes should happen from the camera thread only.
    """

    MAX_HISTORY = 200

    def __init__(self):
        self.history: Deque[TextSegment] = deque(maxlen=self.MAX_HISTORY)
        self.last_feedback: str = ""
        self.last_feedback_time: float = 0.0
        self.feedback_cooldown: float = 3.0   # seconds between identical messages
        self.last_text: str = ""
        self.last_text_time: float = 0.0
        self.text_cooldown: float = 2.5       # seconds before re-reading same text
        self.frames_processed: int = 0
        self.braille_frames: int = 0
        self.session_start: float = time.time()
        self.is_paused: bool = False
        # Temporal confirmation: same reading N times before TTS
        self._pending_text: str = ""
        self._pending_count: int = 0
        self._pending_confidence: float = 0.0
        self.stable_frames_required: int = 2   # reduced: hand-drawn needs fewer confirmations
        self.min_confidence: float = 0.40   # reduced: hand-drawn grids score lower

    # ── Text history ──────────────────────────────────────────────────────────

    def add_text(self, text: str, source: str = "camera", confidence: float = 1.0) -> bool:
        """
        Add *text* to history.  Returns True if this is new text that should
        be spoken (i.e. not a duplicate within the cooldown window).

        Camera readings must appear stable_frames_required times with
        sufficient confidence before returning True.
        """
        now = time.time()
        cleaned = text.strip().lower()
        if not cleaned:
            self._reset_pending()
            return False

        if source == "camera":
            if confidence < self.min_confidence:
                self._reset_pending()
                return False
            if cleaned == self._pending_text:
                self._pending_count += 1
                self._pending_confidence = max(self._pending_confidence, confidence)
            else:
                self._pending_text = cleaned
                self._pending_count = 1
                self._pending_confidence = confidence
            if self._pending_count < self.stable_frames_required:
                return False
            cleaned = self._pending_text
            confidence = self._pending_confidence
            self._reset_pending()

        if (cleaned == self.last_text and
                now - self.last_text_time < self.text_cooldown):
            return False
        self.history.append(TextSegment(cleaned, now, source))
        self.last_text = cleaned
        self.last_text_time = now
        return True

    def _reset_pending(self) -> None:
        self._pending_text = ""
        self._pending_count = 0
        self._pending_confidence = 0.0

    def get_history(self, n: int = 20) -> List[TextSegment]:
        """Return the last *n* text segments."""
        items = list(self.history)
        return items[-n:]

    def get_full_text(self) -> str:
        """Return all history as a single space-joined string."""
        return " ".join(s.text for s in self.history)

    # ── Feedback ──────────────────────────────────────────────────────────────

    def should_speak_feedback(self, message: str) -> bool:
        """
        Return True if *message* should be spoken (not a recent duplicate).
        Automatically updates internal state.
        """
        now = time.time()
        if (message == self.last_feedback and
                now - self.last_feedback_time < self.feedback_cooldown):
            return False
        self.last_feedback = message
        self.last_feedback_time = now
        return True

    # ── Stats ─────────────────────────────────────────────────────────────────

    def tick(self, braille_found: bool) -> None:
        self.frames_processed += 1
        if braille_found:
            self.braille_frames += 1

    def stats(self) -> dict:
        elapsed = time.time() - self.session_start
        return {
            "elapsed_s":       round(elapsed, 1),
            "frames":          self.frames_processed,
            "braille_frames":  self.braille_frames,
            "history_count":   len(self.history),
        }

    def clear(self) -> None:
        self.history.clear()
        self.last_text = ""
        self.last_feedback = ""
