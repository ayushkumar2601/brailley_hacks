"""
segmentation.py
---------------
Image segmentation: locates every braille character in a scanned JPEG page
and returns its (x, y) bounding-box coordinates.

The page must be scanned in portrait mode at 300 dpi with the left margin
facing up so that dot shadows face the right margin when the page is viewed
in landscape orientation.
"""

import os
import cv2
import numpy as np

from braille_ocr.config import (
    X_MIN,
    CHARACTER_WIDTH,
    CHARACTER_HEIGHT,
    MAX_LINES_PER_PAGE,
    CHARS_PER_LINE,
    RECTANGLES_FOLDER,
)


def _find_optimal_cutoff(image_filtered: np.ndarray, imgheight: int) -> int:
    """
    Try cutoff values from 30 to 290 (step 10) and return the lowest one
    that still yields the maximum number of detected lines (≤ MAX_LINES_PER_PAGE).

    A higher cutoff means fewer y-coordinates pass the threshold, which can
    cause lines to be missed.  The lowest cutoff that still gives the most
    lines is therefore the best choice.
    """
    cutoff_results = []

    for cutoff in range(30, 300, 10):
        y_pixels = np.where(np.sum(image_filtered, axis=0) > cutoff)[0]
        lines = _detect_lines(y_pixels, imgheight)
        if len(lines) <= MAX_LINES_PER_PAGE:
            cutoff_results.append((len(lines), cutoff))

    if not cutoff_results:
        return 30  # fallback

    max_lines = max(r[0] for r in cutoff_results)
    # Pick the lowest cutoff that achieves the maximum line count.
    return next(r[1] for r in sorted(cutoff_results) if r[0] == max_lines)


def _detect_lines(y_pixels: np.ndarray, imgheight: int) -> list:
    """
    Given the y-pixel indices that exceed the non-white-pixel threshold,
    return a list of [y_min, y_max] pairs — one per detected braille line.
    """
    lines = []
    for k in range(len(y_pixels) - 1):
        # A gap > 15 px between consecutive y-pixels signals a new line.
        if y_pixels[k + 1] - y_pixels[k] > 15:
            y_min = y_pixels[k] - CHARACTER_HEIGHT
            y_max = y_pixels[k]

            # Skip lines that touch the page border.
            if y_min - CHARACTER_HEIGHT <= 0 or y_max + CHARACTER_HEIGHT >= imgheight:
                continue
            # Skip lines that overlap with the previous one.
            if lines and (y_min - lines[-1][0]) < CHARACTER_HEIGHT:
                continue

            lines.append([y_min, y_max])
    return lines


def _build_x_ranges() -> list:
    """
    Return the list of [x_min, x_max] pairs for all 41 character positions
    on a line, starting from X_MIN.
    """
    ranges = []
    x = X_MIN
    for _ in range(CHARS_PER_LINE):
        ranges.append([x, x + CHARACTER_WIDTH])
        x += CHARACTER_WIDTH + 12  # 12 px inter-cell gap
    return ranges


def get_character_coordinates(
    image_gray: np.ndarray,
    text_image_copy: np.ndarray,
    output_path: str,
    jpeg_stem: str,
) -> list:
    """
    Segment *image_gray* (grayscale, portrait-mode scan) and return a list of
    [[x_min, y_min], [x_max, y_max]] bounding boxes — one per braille cell,
    ordered top-to-bottom, left-to-right.

    Also writes a debug JPEG with green rectangles to *output_path*.

    Parameters
    ----------
    image_gray      : grayscale numpy array of the scanned page
    text_image_copy : colour copy used for drawing the debug rectangles
    output_path     : folder where the debug image is saved
    jpeg_stem       : base filename (without extension) for the debug image
    """
    # The page is written in landscape but scanned in portrait, so:
    #   axis-0 of the array  →  x-axis in landscape reading orientation
    #   axis-1 of the array  →  y-axis in landscape reading orientation
    imgheight = image_gray.shape[1]  # landscape width
    imgwidth  = image_gray.shape[0]  # landscape height

    # Convert: white pixels → 0, non-white → 1
    image_filtered = np.where(image_gray == 255, 0, 1)

    # ── Find the best cutoff and detect lines ─────────────────────────────────
    cutoff = _find_optimal_cutoff(image_filtered, imgheight)
    y_pixels = np.where(np.sum(image_filtered, axis=0) > cutoff)[0]
    lines_y_min_maxes = _detect_lines(y_pixels, imgheight)

    # ── Build x-coordinate ranges for all 41 character slots ─────────────────
    characters_x_min_maxes = _build_x_ranges()

    # ── Assemble bounding boxes and draw debug rectangles ────────────────────
    # Iterate in reverse because the image origin (0, 0) is at the bottom of
    # the page in portrait mode; reversing gives top-to-bottom reading order.
    coords = []
    for m in range(len(lines_y_min_maxes) - 1, -1, -1):
        y_min, y_max = lines_y_min_maxes[m]
        line_index = lines_y_min_maxes.index(lines_y_min_maxes[m])

        # Skip lines that touch the border or overlap with the previous one.
        if (y_min - CHARACTER_HEIGHT <= 0
                or y_max + CHARACTER_HEIGHT >= imgheight
                or (line_index > 0
                    and y_min - lines_y_min_maxes[line_index - 1][0] < CHARACTER_HEIGHT)):
            continue

        for x_min, x_max in characters_x_min_maxes:
            coords.append([[x_min, y_min], [x_max, y_max]])
            # Draw rectangle (note: cv2 uses (col, row) = (y, x) in portrait array)
            cv2.rectangle(text_image_copy, (y_min, x_min), (y_max, x_max), (0, 255, 0), 3)

    # ── Save debug image ──────────────────────────────────────────────────────
    os.makedirs(output_path, exist_ok=True)
    debug_path = os.path.join(output_path, f"{jpeg_stem} with character rectangles.jpg")
    cv2.imwrite(debug_path, text_image_copy)

    return coords
