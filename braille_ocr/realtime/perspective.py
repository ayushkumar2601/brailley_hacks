"""
perspective.py
--------------
Perspective correction for Braille page scanning.

Detects the paper/document boundary in a camera frame and applies a
homography transform to produce a flat, top-down view of the page.
This eliminates perspective distortion that breaks dot-spacing geometry.

Usage:
    from braille_ocr.realtime.perspective import correct_perspective
    flat, contour = correct_perspective(frame)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ── Configuration ─────────────────────────────────────────────────────────────

@dataclass
class PerspectiveConfig:
    """Tuneable parameters for page detection and warping."""

    # Gaussian blur kernel size applied before edge detection
    blur_ksize: int = 5

    # Canny edge-detection thresholds
    canny_low: int = 50
    canny_high: int = 150

    # Morphological kernel size for closing gaps in edges
    morph_ksize: int = 5

    # Minimum fraction of image area a contour must cover to be
    # considered a page candidate (prevents picking tiny rectangles)
    min_area_ratio: float = 0.15

    # Maximum fraction of image area (rejects full-frame contours)
    max_area_ratio: float = 0.98

    # Epsilon multiplier for cv2.approxPolyDP arc-length approximation
    approx_epsilon: float = 0.02

    # Output width/height for the warped image (0 = auto-derive)
    output_width: int = 0
    output_height: int = 0


# Module-level default config
_DEFAULT_CFG = PerspectiveConfig()


# ── Public API ────────────────────────────────────────────────────────────────

def correct_perspective(
    frame: np.ndarray,
    config: Optional[PerspectiveConfig] = None,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Detect the Braille page in *frame* and return a flattened top-down image.

    Returns
    -------
    (warped, contour)
        *warped*  – the flattened page image, or *frame* unchanged if no
                    document was found.
        *contour* – the 4-point document contour (Nx1x2 int32 array), or
                    ``None`` if detection failed.
    """
    cfg = config or _DEFAULT_CFG
    contour = find_document_contour(frame, cfg)
    if contour is None:
        return frame, None
    warped = warp_document(frame, contour, cfg)
    return warped, contour


def find_document_contour(
    frame: np.ndarray,
    config: Optional[PerspectiveConfig] = None,
) -> Optional[np.ndarray]:
    """
    Find the largest quadrilateral contour likely to be the Braille page.

    Returns a (4, 2) int32 array of corner points ordered
    [top-left, top-right, bottom-right, bottom-left], or ``None``.
    """
    cfg = config or _DEFAULT_CFG
    h, w = frame.shape[:2]
    img_area = h * w

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

    # ── Pre-processing ────────────────────────────────────────────────────
    blurred = cv2.GaussianBlur(gray, (cfg.blur_ksize, cfg.blur_ksize), 0)
    edges = cv2.Canny(blurred, cfg.canny_low, cfg.canny_high)

    # Close small gaps so the page boundary forms a continuous contour
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (cfg.morph_ksize, cfg.morph_ksize)
    )
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    # Dilate slightly to connect nearby edge fragments
    edges = cv2.dilate(edges, kernel, iterations=1)

    # ── Contour search ────────────────────────────────────────────────────
    contours, _ = cv2.findContours(
        edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return None

    # Sort by area descending – the page is usually the largest quad
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        area_ratio = area / img_area

        if area_ratio < cfg.min_area_ratio or area_ratio > cfg.max_area_ratio:
            continue

        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, cfg.approx_epsilon * peri, True)

        if len(approx) == 4:
            pts = approx.reshape(4, 2).astype(np.float32)
            ordered = _order_points(pts)
            logger.debug(
                "Document contour found: area=%.0f (%.1f%% of frame)",
                area,
                area_ratio * 100,
            )
            return ordered.astype(np.int32)

    return None


def warp_document(
    frame: np.ndarray,
    points: np.ndarray,
    config: Optional[PerspectiveConfig] = None,
) -> np.ndarray:
    """
    Apply a perspective warp so the quadrilateral defined by *points*
    becomes a top-down rectangle.

    Parameters
    ----------
    frame   : source BGR image.
    points  : (4, 2) array ordered [TL, TR, BR, BL].
    config  : optional tuning parameters.

    Returns
    -------
    The warped (flattened) image.
    """
    cfg = config or _DEFAULT_CFG
    pts = points.astype(np.float32).reshape(4, 2)

    # Derive output dimensions from the quadrilateral side lengths
    tl, tr, br, bl = pts
    width_top = float(np.linalg.norm(tr - tl))
    width_bot = float(np.linalg.norm(br - bl))
    height_left = float(np.linalg.norm(bl - tl))
    height_right = float(np.linalg.norm(br - tr))

    out_w = cfg.output_width or int(max(width_top, width_bot))
    out_h = cfg.output_height or int(max(height_left, height_right))

    # Clamp to reasonable size
    out_w = max(100, min(out_w, 2000))
    out_h = max(100, min(out_h, 2000))

    dst = np.array(
        [[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]],
        dtype=np.float32,
    )

    M = cv2.getPerspectiveTransform(pts, dst)
    warped = cv2.warpPerspective(
        frame, M, (out_w, out_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return warped


# ── Helpers ───────────────────────────────────────────────────────────────────

def _order_points(pts: np.ndarray) -> np.ndarray:
    """
    Order four 2-D points as [top-left, top-right, bottom-right, bottom-left].

    Uses sum (x+y) to find TL/BR and difference (y-x) to find TR/BL.
    """
    rect = np.zeros((4, 2), dtype=np.float32)

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # top-left has smallest x+y
    rect[2] = pts[np.argmax(s)]   # bottom-right has largest x+y

    d = np.diff(pts, axis=1).ravel()
    rect[1] = pts[np.argmin(d)]   # top-right has smallest y-x
    rect[3] = pts[np.argmax(d)]   # bottom-left has largest y-x

    return rect
