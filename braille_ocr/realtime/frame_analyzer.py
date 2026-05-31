"""
frame_analyzer.py
-----------------
Analyses a single camera frame for:
  1. Image quality (brightness, blur)
  2. Perspective correction (page flattening)
  3. Illumination normalisation
  4. Robust blob-based dot detection
  5. Distance hint (move closer / move back)

Phase 1 Vision Stabilization refactor:
  - Replaced ad-hoc CLAHE + contour logic with the dedicated
    ``preprocessing``, ``blob_detector``, and ``perspective`` modules.
  - Added optional ``DebugVisualizer`` integration.
"""

import cv2
import numpy as np

from braille_ocr.realtime.perspective import (
    PerspectiveConfig,
    correct_perspective,
)
from braille_ocr.realtime.preprocessing import (
    PreprocessConfig,
    normalize_lighting,
    generate_binary_mask,
)
from braille_ocr.realtime.blob_detector import (
    BlobConfig,
    detect_braille_blobs,
    draw_blob_debug,
)
from braille_ocr.realtime.debug_visualizer import DebugVisualizer


# ── Thresholds ────────────────────────────────────────────────────────────────
BRIGHTNESS_LOW        = 30     # mean pixel value → too dark
BRIGHTNESS_HIGH       = 235    # mean pixel value → too bright
BLUR_THRESHOLD        = 12.0   # Laplacian variance → blurry (relaxed for paper + hand-drawn)
MIN_DOTS_FOR_BRAILLE  = 3      # minimum dots to consider braille present
IDEAL_DOT_COUNT_LOW   = 3
IDEAL_DOT_COUNT_HIGH  = 300

# ── Module-level configs (can be replaced at runtime) ─────────────────────────
perspective_config = PerspectiveConfig()
preprocess_config  = PreprocessConfig()
blob_config        = BlobConfig()

# ── Debug visualizer (disabled by default; toggled via /api/debug) ────────────
debug_visualizer = DebugVisualizer(enabled=False, save_to_disk=False)


def analyze_frame(frame: np.ndarray) -> dict:
    """
    Analyse *frame* (BGR numpy array) and return::

        {
          "quality":          str,   # OK | TOO_DARK | TOO_BRIGHT | BLURRY
                                     #   | MOVE_CLOSER | MOVE_BACK | NO_BRAILLE
          "braille_detected": bool,
          "dot_count":        int,
          "dot_regions":      list,  # [(x,y,w,h), ...]
          "annotated":        np.ndarray,
          "gray":             np.ndarray,
        }
    """
    dbg = debug_visualizer
    dbg.reset()
    dbg.set_raw(frame)

    annotated = frame.copy()

    # ── 0. Quick quality gate (on raw frame) ──────────────────────────────
    gray_raw = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_brightness = float(np.mean(gray_raw))

    if mean_brightness < BRIGHTNESS_LOW:
        _draw_overlay(annotated, "TOO_DARK", (0, 0, 200))
        return _result("TOO_DARK", False, 0, [], annotated, gray_raw)
    if mean_brightness > BRIGHTNESS_HIGH:
        _draw_overlay(annotated, "TOO_BRIGHT", (0, 200, 200))
        return _result("TOO_BRIGHT", False, 0, [], annotated, gray_raw)

    lap_var = float(cv2.Laplacian(gray_raw, cv2.CV_64F).var())
    if lap_var < BLUR_THRESHOLD:
        _draw_overlay(annotated, "BLURRY", (0, 120, 255))
        return _result("BLURRY", False, 0, [], annotated, gray_raw)

    # ── 1. Perspective correction ─────────────────────────────────────────
    warped, contour = correct_perspective(frame, perspective_config)
    dbg.set_perspective(warped, contour)

    # Use the warped frame for all subsequent processing
    working_frame = warped
    annotated = working_frame.copy()

    # ── 2. Illumination normalisation ─────────────────────────────────────
    gray, enhanced = normalize_lighting(working_frame, preprocess_config)

    # ── 3. Binary mask ────────────────────────────────────────────────────
    binary = generate_binary_mask(enhanced, preprocess_config)
    dbg.set_preprocessing(gray, enhanced, binary)

    # ── 4. Blob-based dot detection ───────────────────────────────────────
    accepted, rejected = detect_braille_blobs(binary, blob_config)
    dbg.set_blobs(working_frame, accepted, rejected)

    # Convert accepted blobs to bounding-box regions for backward compat
    dot_regions = []
    for cx, cy, r in accepted:
        x = max(0, cx - r)
        y_pos = max(0, cy - r)
        w = r * 2
        h = r * 2
        dot_regions.append((x, y_pos, w, h))

    # Draw blob overlay on the annotated frame
    annotated = draw_blob_debug(annotated, accepted, rejected)

    dot_count = len(accepted)
    braille_detected = dot_count >= MIN_DOTS_FOR_BRAILLE

    # ── 5. Quality / distance hint ────────────────────────────────────────
    if not braille_detected:
        quality = "NO_BRAILLE"
        colour  = (120, 120, 120)
    elif dot_count < IDEAL_DOT_COUNT_LOW:
        quality = "MOVE_CLOSER"
        colour  = (0, 165, 255)
    elif dot_count > IDEAL_DOT_COUNT_HIGH:
        quality = "MOVE_BACK"
        colour  = (0, 165, 255)
    else:
        quality = "OK"
        colour  = (0, 220, 0)

    _draw_overlay(annotated, quality, colour,
                  dot_count=dot_count, brightness=mean_brightness, blur=lap_var)

    # We don't have DetectionResult here, it's called from braille_detector.
    # To pass grid/snapped info to visualizer, we can either call braille_detector from here 
    # or let the caller update the visualizer. In app.py, `detect_braille` is called after `analyze_frame`.
    # Let's just return quality here.

    return _result(quality, braille_detected, dot_count, dot_regions, annotated, gray)


def _result(quality, detected, count, regions, annotated, gray):
    return {
        "quality":          quality,
        "braille_detected": detected,
        "dot_count":        count,
        "dot_regions":      regions,
        "annotated":        annotated,
        "gray":             gray,
    }


def _draw_overlay(frame, quality, colour, dot_count=0, brightness=0.0, blur=0.0):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 52), (15, 15, 20), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    labels = {
        "OK":          "✓ Braille detected — scanning",
        "TOO_DARK":    "⚠ Too dark — improve lighting",
        "TOO_BRIGHT":  "⚠ Too bright — reduce glare",
        "BLURRY":      "⚠ Blurry — hold camera steady",
        "MOVE_CLOSER": "→ Move closer to the page",
        "MOVE_BACK":   "← Move back a little",
        "NO_BRAILLE":  "  Scanning — no braille detected",
    }
    label = labels.get(quality, quality)
    cv2.putText(frame, label, (12, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.75, colour, 2)
    if dot_count or brightness:
        info = f"dots:{dot_count}  brightness:{brightness:.0f}  sharpness:{blur:.0f}"
        cv2.putText(frame, info, (12, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (140, 140, 160), 1)
