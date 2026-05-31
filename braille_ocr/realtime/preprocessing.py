"""
preprocessing.py
-----------------
Illumination normalization and image preprocessing pipeline for Braille
dot detection.

Provides reusable functions that transform a raw camera frame into a
clean binary mask optimised for circular-blob extraction.  All heavy
lifting uses OpenCV-native operations for real-time performance.

Usage:
    from braille_ocr.realtime.preprocessing import (
        normalize_lighting,
        generate_binary_mask,
        enhance_contrast,
    )

    gray, enhanced = normalize_lighting(frame)
    binary = generate_binary_mask(enhanced)
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
class PreprocessConfig:
    """Tuneable parameters for illumination normalisation."""

    # CLAHE contrast-limited adaptive histogram equalisation
    clahe_clip_limit: float = 2.5
    clahe_tile_grid: Tuple[int, int] = (8, 8)

    # Gaussian blur kernel size (must be odd)
    blur_ksize: int = 5

    # Adaptive threshold parameters
    adaptive_block_size: int = 21
    adaptive_c: int = 5

    # Also try Otsu and combine results (good for high-contrast pages)
    use_otsu_combine: bool = True

    # Morphological closing after thresholding (fills gaps in hand-drawn dots)
    morph_close_ksize: int = 3

    # Optional bilateral filter for noise reduction while preserving edges
    use_bilateral: bool = False
    bilateral_d: int = 9
    bilateral_sigma_color: float = 75.0
    bilateral_sigma_space: float = 75.0

    # Background subtraction: divide by large-blur version to remove shadows
    use_background_division: bool = True
    bg_blur_ksize: int = 51


# Module-level default config
_DEFAULT_CFG = PreprocessConfig()


# ── Public API ────────────────────────────────────────────────────────────────

def enhance_contrast(
    gray: np.ndarray,
    config: Optional[PreprocessConfig] = None,
) -> np.ndarray:
    """
    Apply CLAHE contrast enhancement to a grayscale image.

    Parameters
    ----------
    gray   : single-channel uint8 image.
    config : optional tuning parameters.

    Returns
    -------
    Contrast-enhanced grayscale image (uint8).
    """
    cfg = config or _DEFAULT_CFG
    clahe = cv2.createCLAHE(
        clipLimit=cfg.clahe_clip_limit,
        tileGridSize=cfg.clahe_tile_grid,
    )
    return clahe.apply(gray)


def normalize_lighting(
    frame: np.ndarray,
    config: Optional[PreprocessConfig] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Full illumination-normalisation pipeline.

    1. Convert to grayscale (if BGR).
    2. Optionally remove uneven background via division normalisation.
    3. Apply CLAHE contrast enhancement.
    4. Apply Gaussian blur to reduce high-frequency noise.
    5. Optionally apply bilateral filter for edge-preserving smoothing.

    Parameters
    ----------
    frame  : BGR or grayscale image.
    config : optional tuning parameters.

    Returns
    -------
    (gray, enhanced)
        *gray*     – the grayscale conversion.
        *enhanced* – the fully normalised grayscale image, ready for
                     thresholding.
    """
    cfg = config or _DEFAULT_CFG

    # 1. Grayscale
    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame.copy()

    working = gray.copy()

    # 2. Background division — removes uneven illumination / shadows
    if cfg.use_background_division:
        bg = cv2.GaussianBlur(
            working,
            (cfg.bg_blur_ksize, cfg.bg_blur_ksize),
            0,
        )
        # Prevent divide-by-zero; normalise to ~mean brightness
        bg = bg.astype(np.float32)
        bg[bg == 0] = 1.0
        divided = (working.astype(np.float32) / bg) * 128.0
        working = np.clip(divided, 0, 255).astype(np.uint8)

    # 3. CLAHE
    working = enhance_contrast(working, cfg)

    # 4. Gaussian blur
    working = cv2.GaussianBlur(
        working, (cfg.blur_ksize, cfg.blur_ksize), 0
    )

    # 5. Optional bilateral
    if cfg.use_bilateral:
        working = cv2.bilateralFilter(
            working,
            cfg.bilateral_d,
            cfg.bilateral_sigma_color,
            cfg.bilateral_sigma_space,
        )

    return gray, working


def generate_binary_mask(
    enhanced: np.ndarray,
    config: Optional[PreprocessConfig] = None,
) -> np.ndarray:
    """
    Convert a normalised grayscale image into a binary mask where
    foreground (dots) are white (255) and background is black (0).

    Uses adaptive thresholding + optional Otsu combination for
    robustness across lighting conditions.

    Parameters
    ----------
    enhanced : normalised grayscale from :func:`normalize_lighting`.
    config   : optional tuning parameters.

    Returns
    -------
    Binary mask (uint8, values 0 or 255).
    """
    cfg = config or _DEFAULT_CFG

    # Adaptive threshold — handles local illumination variation
    adaptive = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=cfg.adaptive_block_size,
        C=cfg.adaptive_c,
    )

    if cfg.use_otsu_combine:
        # Otsu — good for high-contrast embossed Braille
        _, otsu = cv2.threshold(
            enhanced, 0, 255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
        )
        combined = cv2.bitwise_or(adaptive, otsu)
    else:
        combined = adaptive

    # Morphological closing — fill small gaps in hand-drawn dots
    if cfg.morph_close_ksize > 0:
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (cfg.morph_close_ksize, cfg.morph_close_ksize),
        )
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)

    return combined
