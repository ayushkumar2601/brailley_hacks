"""
blob_detector.py
-----------------
Robust Braille dot detection using ``cv2.SimpleBlobDetector``.

Replaces the legacy contour-based dot finder with a purpose-tuned blob
detector that filters by area, circularity, convexity, and inertia ratio.
This dramatically reduces false-positive detections from paper texture,
shadows, and camera noise.

Usage:
    from braille_ocr.realtime.blob_detector import (
        detect_braille_blobs,
        BlobConfig,
    )

    accepted, rejected = detect_braille_blobs(binary_mask)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ── Configuration ─────────────────────────────────────────────────────────────

@dataclass
class BlobConfig:
    """
    Tuneable parameters for ``cv2.SimpleBlobDetector``.

    All ranges are *inclusive*.  Set a ``filter_by_*`` flag to ``False``
    to disable that filter entirely.

    Tuning guide
    ------------
    * **Area** – reject noise (tiny) and non-dot regions (huge).
      Typical embossed Braille dots: 50-3000 px².
      Hand-drawn pen dots: 30-5000 px².
    * **Circularity** – 4π·area / perimeter².  Perfect circle = 1.0.
      Braille dots ≥ 0.5 is a safe starting point.
    * **Convexity** – area / convex-hull area.  Rejects irregular shapes.
    * **Inertia** – elongation ratio.  Circle = 1.0, line = 0.0.
      Braille dots should be ≥ 0.4.
    """

    # ── Colour / polarity ─────────────────────────────────────────────────
    # Detect dark blobs on a light background (the binary mask is inverted,
    # so dots are white — set blob_color = 255 to detect them).
    filter_by_color: bool = True
    blob_color: int = 255

    # ── Area filter ───────────────────────────────────────────────────────
    filter_by_area: bool = True
    min_area: float = 30.0
    max_area: float = 8000.0

    # ── Circularity filter ────────────────────────────────────────────────
    filter_by_circularity: bool = True
    min_circularity: float = 0.50
    max_circularity: float = 1.0

    # ── Convexity filter ──────────────────────────────────────────────────
    filter_by_convexity: bool = True
    min_convexity: float = 0.60
    max_convexity: float = 1.0

    # ── Inertia filter ────────────────────────────────────────────────────
    filter_by_inertia: bool = True
    min_inertia_ratio: float = 0.40
    max_inertia_ratio: float = 1.0

    # ── Thresholds for SimpleBlobDetector internal binarisation ────────────
    min_threshold: float = 10.0
    max_threshold: float = 220.0
    threshold_step: float = 10.0

    # ── Distance-deduplication ────────────────────────────────────────────
    min_dist_between_blobs: float = 8.0

    # ── Repeatability ─────────────────────────────────────────────────────
    min_repeatability: int = 2

    # ── Post-filter: size uniformity ──────────────────────────────────────
    # After detection, keep only blobs whose radius is within this fraction
    # of the median radius.  Set to 0 to disable.
    size_uniformity_tolerance: float = 0.70


# Module-level default
_DEFAULT_CFG = BlobConfig()

# Cache the detector to avoid re-creating every frame
_cached_detector: Optional[cv2.SimpleBlobDetector] = None
_cached_cfg_id: Optional[int] = None


# ── Public API ────────────────────────────────────────────────────────────────

def create_blob_detector(config: Optional[BlobConfig] = None) -> cv2.SimpleBlobDetector:
    """
    Build a ``cv2.SimpleBlobDetector`` from the given configuration.

    The detector is cached module-wide; it is only re-created when the
    config object changes.
    """
    global _cached_detector, _cached_cfg_id
    cfg = config or _DEFAULT_CFG

    cfg_id = id(cfg)
    if _cached_detector is not None and _cached_cfg_id == cfg_id:
        return _cached_detector

    params = cv2.SimpleBlobDetector_Params()

    # Thresholds
    params.minThreshold = cfg.min_threshold
    params.maxThreshold = cfg.max_threshold
    params.thresholdStep = cfg.threshold_step

    # Colour
    params.filterByColor = cfg.filter_by_color
    params.blobColor = cfg.blob_color

    # Area
    params.filterByArea = cfg.filter_by_area
    params.minArea = cfg.min_area
    params.maxArea = cfg.max_area

    # Circularity
    params.filterByCircularity = cfg.filter_by_circularity
    params.minCircularity = cfg.min_circularity

    # Convexity
    params.filterByConvexity = cfg.filter_by_convexity
    params.minConvexity = cfg.min_convexity

    # Inertia
    params.filterByInertia = cfg.filter_by_inertia
    params.minInertiaRatio = cfg.min_inertia_ratio

    # Distance
    params.minDistBetweenBlobs = cfg.min_dist_between_blobs

    # Repeatability
    params.minRepeatability = cfg.min_repeatability

    detector = cv2.SimpleBlobDetector_create(params)
    _cached_detector = detector
    _cached_cfg_id = cfg_id

    logger.debug("SimpleBlobDetector created with area=[%.0f, %.0f], circ>=%.2f",
                 cfg.min_area, cfg.max_area, cfg.min_circularity)
    return detector


def detect_braille_blobs(
    binary_or_gray: np.ndarray,
    config: Optional[BlobConfig] = None,
) -> Tuple[List[Tuple[int, int, int]], List[Tuple[int, int, int]]]:
    """
    Detect Braille dot candidates using ``cv2.SimpleBlobDetector``.

    Parameters
    ----------
    binary_or_gray : either the binary mask from ``generate_binary_mask``
                     or a normalised grayscale image.
    config         : optional blob-detector tuning.

    Returns
    -------
    (accepted, rejected)
        Each is a list of ``(cx, cy, radius)`` tuples.
        *accepted* dots pass all filters including size uniformity.
        *rejected* dots failed the post-filter (useful for debug overlay).
    """
    cfg = config or _DEFAULT_CFG
    detector = create_blob_detector(cfg)

    # SimpleBlobDetector expects the image in the correct polarity.
    # If we receive a binary mask (dots=255), we invert so dots become dark
    # blobs on a white background (the detector's default expectation when
    # blobColor=255 is "detect bright blobs").  Actually, when blobColor=255,
    # the detector looks for white blobs — so if dots are white in the mask,
    # we can pass it directly.
    keypoints = detector.detect(binary_or_gray)

    if not keypoints:
        return [], []

    # Convert keypoints to (cx, cy, radius) tuples
    all_dots = [
        (int(kp.pt[0]), int(kp.pt[1]), max(1, int(kp.size / 2)))
        for kp in keypoints
    ]

    # ── Post-filter: size uniformity ──────────────────────────────────────
    if cfg.size_uniformity_tolerance > 0 and len(all_dots) >= 2:
        accepted, rejected = filter_blob_candidates(all_dots, cfg)
    else:
        accepted = all_dots
        rejected = []

    logger.debug(
        "Blob detection: %d keypoints → %d accepted, %d rejected",
        len(keypoints), len(accepted), len(rejected),
    )
    return accepted, rejected


def filter_blob_candidates(
    dots: List[Tuple[int, int, int]],
    config: Optional[BlobConfig] = None,
) -> Tuple[List[Tuple[int, int, int]], List[Tuple[int, int, int]]]:
    """
    Post-filter detected blobs for size uniformity.

    Real Braille dots on the same page have approximately uniform size.
    Blobs whose radius deviates too far from the median are rejected.

    Returns
    -------
    (accepted, rejected)
    """
    cfg = config or _DEFAULT_CFG
    if not dots:
        return [], []

    radii = [d[2] for d in dots]
    med = float(np.median(radii))
    tol = cfg.size_uniformity_tolerance
    lo = med * (1.0 - tol)
    hi = med * (1.0 + tol)

    accepted = []
    rejected = []
    for d in dots:
        if lo <= d[2] <= hi:
            accepted.append(d)
        else:
            rejected.append(d)

    return accepted, rejected


def draw_blob_debug(
    frame: np.ndarray,
    accepted: List[Tuple[int, int, int]],
    rejected: Optional[List[Tuple[int, int, int]]] = None,
    show_ids: bool = False,
) -> np.ndarray:
    """
    Draw accepted (green) and rejected (red) dot circles on *frame*.

    Parameters
    ----------
    frame    : BGR image to draw on (will be copied).
    accepted : dots that passed all filters.
    rejected : dots that failed post-filter.
    show_ids : if True, draw a small numeric label next to each dot.

    Returns
    -------
    Annotated BGR image.
    """
    vis = frame.copy()

    # Rejected — red
    if rejected:
        for i, (cx, cy, r) in enumerate(rejected):
            cv2.circle(vis, (cx, cy), max(r + 2, 5), (0, 0, 220), 2)
            if show_ids:
                cv2.putText(vis, f"R{i}", (cx + r + 3, cy - 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 200), 1)

    # Accepted — green
    for i, (cx, cy, r) in enumerate(accepted):
        cv2.circle(vis, (cx, cy), max(r + 2, 5), (0, 220, 100), 2)
        if show_ids:
            cv2.putText(vis, str(i), (cx + r + 3, cy - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 200, 80), 1)

    # Summary text
    cv2.putText(
        vis,
        f"Blobs: {len(accepted)} accepted, {len(rejected or [])} rejected",
        (8, vis.shape[0] - 8),
        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 200), 1,
    )

    return vis


def blobs_to_legacy_format(
    accepted: List[Tuple[int, int, int]],
) -> List[Tuple[int, int, int]]:
    """
    Convert accepted blobs to the ``(cx, cy, radius)`` format expected
    by the existing ``braille_detector.py`` pipeline.

    This is an identity transform — the format already matches — but
    exists as a named bridge for clarity.
    """
    return list(accepted)
