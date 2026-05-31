"""
convert_dataset.py
------------------
The MOST IMPORTANT script in the Dataset Conversion Pipeline.
Converts raw dataset images (DSBI/Angelina) into normalized, training-ready
64x64 cell tensors with corresponding binary labels.

CRITICAL: Uses the EXACT same preprocessing chain as live OCR inference
to guarantee zero train/inference mismatch:
  normalize_lighting → generate_binary_mask → detect_braille_blobs
  → estimate_grid → snap_dots_to_grid → extract cell patch
"""

import os
import cv2
import json
import glob
import uuid
import logging
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np

# ── Import the identical inference pipeline modules ────────────────────────────
from braille_ocr.realtime.preprocessing import normalize_lighting, generate_binary_mask
from braille_ocr.realtime.blob_detector import detect_braille_blobs
from braille_ocr.realtime.grid_estimator import estimate_grid
from braille_ocr.realtime.dot_snapper import snap_dots_to_grid
from synthetic_dataset.scripts.augment_realism import RealismAugmentor

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

PATCH_SIZE = 64  # px — must match DotCNN input size
AUGMENT_PROB = 0.5  # probability of applying realism augmentation per cell


def extract_cell_patch(
    image: np.ndarray,
    cell_box: Tuple[int, int, int, int],
    patch_size: int = PATCH_SIZE,
) -> np.ndarray:
    """Extract and resize a single Braille cell region from the image."""
    x, y, w, h = cell_box
    margin = max(int(min(w, h) * 0.1), 2)
    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(image.shape[1], x + w + margin)
    y2 = min(image.shape[0], y + h + margin)

    patch = image[y1:y2, x1:x2]
    if patch.size == 0:
        return np.zeros((patch_size, patch_size), dtype=np.uint8)
    return cv2.resize(patch, (patch_size, patch_size), interpolation=cv2.INTER_AREA)


def convert_image(
    image_path: str,
    source: str,
    out_images_dir: str,
    out_labels_dir: str,
    augmentor: Optional[RealismAugmentor] = None,
) -> int:
    """
    Run the full inference-identical preprocessing pipeline on one image.
    Extracts cells and saves 64x64 patches + JSON labels.
    Returns the number of cells extracted.
    """
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        log.warning("Cannot read: %s", image_path)
        return 0

    # ── Step 1: Illumination normalisation (identical to inference) ─────────────
    gray, enhanced = normalize_lighting(img_bgr)

    # ── Step 2: Binary mask ─────────────────────────────────────────────────────
    binary = generate_binary_mask(enhanced)

    # ── Step 3: Blob detection (identical to inference) ────────────────────────
    accepted, _ = detect_braille_blobs(binary)
    dots = accepted  # list of (cx, cy, radius)

    if not dots:
        log.debug("No blobs in %s", os.path.basename(image_path))
        return 0

    # ── Step 4: Grid reconstruction ─────────────────────────────────────────────
    grid = estimate_grid(dots, gray.shape)
    if not grid or not grid.cells:
        log.debug("No grid in %s", os.path.basename(image_path))
        return 0

    # ── Step 5: Dot snapping ────────────────────────────────────────────────────
    med_r = float(np.median([d[2] for d in dots]))
    snapped_cells = snap_dots_to_grid(dots, grid, med_r)

    if not snapped_cells:
        return 0

    count = 0
    for cell in snapped_cells:
        if cell.cell_id >= len(grid.cells):
            continue

        g_cell = grid.cells[cell.cell_id]

        # ── Step 6: Cell extraction ─────────────────────────────────────────────
        patch = extract_cell_patch(enhanced, g_cell.box)

        # ── Step 7: Augmentation (optional) ────────────────────────────────────
        apply_aug = augmentor is not None and augmentor._apply(AUGMENT_PROB)
        if apply_aug:
            patch = augmentor.augment_all(patch)

        # ── Step 8: Save sample ─────────────────────────────────────────────────
        uid = uuid.uuid4().hex[:8]
        patch_filename = f"{source}_cell_{uid}.jpg"
        meta_filename = f"{source}_cell_{uid}.json"

        cv2.imwrite(
            os.path.join(out_images_dir, patch_filename),
            patch,
            [int(cv2.IMWRITE_JPEG_QUALITY), 95],
        )

        label_data = {
            "dots": cell.dots,           # [1,0,1,0,0,1] from dot_snapper
            "char": "?",                 # unknown without ground-truth annotation
            "confidence": round(cell.confidence, 4),
            "source": source,
            "augmented": apply_aug,
            "cell_position": [g_cell.cell_id, 0],
        }
        with open(os.path.join(out_labels_dir, meta_filename), "w") as f:
            json.dump(label_data, f, indent=2)

        count += 1

    return count


def process_all(out_dir: str = "datasets/training_data") -> dict:
    """Run conversion on all imported dataset images."""
    out_images = os.path.join(out_dir, "images")
    out_labels = os.path.join(out_dir, "labels")
    os.makedirs(out_images, exist_ok=True)
    os.makedirs(out_labels, exist_ok=True)

    augmentor = RealismAugmentor(p=AUGMENT_PROB)
    stats = {"dsbi": 0, "angelina": 0, "sciencedb": 0, "total": 0}

    # DSBI
    dsbi_files = sorted(glob.glob("datasets/dsbi/raw/*.jpg"))
    log.info("Found %d DSBI images to convert.", len(dsbi_files))
    for i, f in enumerate(dsbi_files):
        n = convert_image(f, "dsbi", out_images, out_labels, augmentor)
        stats["dsbi"] += n
        if (i + 1) % 10 == 0:
            log.info("  DSBI: %d/%d images processed, %d cells so far",
                     i + 1, len(dsbi_files), stats["dsbi"])

    # Angelina
    angel_files = sorted(glob.glob("datasets/angelina/raw/*.jpg"))
    log.info("Found %d Angelina images to convert.", len(angel_files))
    for i, f in enumerate(angel_files):
        n = convert_image(f, "angelina", out_images, out_labels, augmentor)
        stats["angelina"] += n
        if (i + 1) % 10 == 0:
            log.info("  Angelina: %d/%d images processed, %d cells so far",
                     i + 1, len(angel_files), stats["angelina"])

    # ScienceDB
    sciencedb_files = sorted(glob.glob("datasets/scienceDB_processed/raw/*.jpg"))
    log.info("Found %d ScienceDB images to convert.", len(sciencedb_files))
    for i, f in enumerate(sciencedb_files):
        n = convert_image(f, "scienceDB", out_images, out_labels, augmentor)
        stats["sciencedb"] += n
        if (i + 1) % 10 == 0:
            log.info("  ScienceDB: %d/%d images processed, %d cells so far",
                     i + 1, len(sciencedb_files), stats["sciencedb"])

    stats["total"] = stats["dsbi"] + stats["angelina"] + stats["sciencedb"]
    return stats


if __name__ == "__main__":
    print("=" * 60)
    print("  BrailleScan Dataset Conversion Pipeline")
    print("=" * 60)
    result = process_all()
    print(f"\n--- Conversion Summary ---")
    print(f"  DSBI cells extracted:    {result['dsbi']}")
    print(f"  Angelina cells extracted:{result['angelina']}")
    print(f"  ScienceDB cells extracted:{result['sciencedb']}")
    print(f"  TOTAL:                   {result['total']}")
    if result["total"] == 0:
        print("\n⚠️  No cells extracted. Run import_datasets.py first.")
    else:
        print(f"\n✅  Training data saved to datasets/training_data/")
