"""
ocr.py
------
Optical Character Recognition (OCR) step.

Crops individual braille-cell images from a scanned page, runs them through
the pre-trained fastai CNN model, and returns the predicted character string
for that page.
"""

import os
import re

import cv2
import numpy as np
from fastai.vision.all import (
    DataBlock,
    ImageBlock,
    CategoryBlock,
    Normalize,
    get_image_files,
    load_learner,
)

from braille_ocr.config import (
    CHARACTER_HEIGHT,
    CHARACTER_WIDTH,
    CHARS_PER_LINE,
    INFERENCE_BATCH_SIZE,
    MODEL_FILENAME,
    RECTANGLES_FOLDER,
)
from braille_ocr.core.segmentation import get_character_coordinates


def load_model(cwd: str):
    """Load and return the fastai learner from *cwd*."""
    return load_learner(os.path.join(cwd, MODEL_FILENAME))


def _crop_and_save_characters(
    image_gray: np.ndarray,
    coords: list,
    output_dir: str,
) -> list:
    """
    Crop each bounding box from *image_gray*, save as a numbered JPEG in
    *output_dir*, and return the list of file paths.
    """
    paths = []
    for j, ((x_min, y_min), (x_max, y_max)) in enumerate(coords):
        crop = image_gray[x_min - 10 : x_max + 10, y_min - 10 : y_max + 10]
        path = os.path.join(output_dir, f"{j}.jpg")
        cv2.imwrite(path, crop)
        paths.append(path)
    return paths


def _predict_characters(learner, char_files: list) -> list:
    """
    Run the fastai model on *char_files* and return a list of predicted
    character labels (one per file).
    """
    # Build a minimal DataBlock so we can create a test DataLoader.
    data_block = DataBlock(
        blocks=(ImageBlock, CategoryBlock),
        get_items=get_image_files,
        batch_tfms=Normalize(),
    )
    dls = data_block.dataloaders(os.path.dirname(char_files[0]), bs=INFERENCE_BATCH_SIZE)
    dl = learner.dls.test_dl(char_files, shuffle=False)

    preds = learner.get_preds(dl=dl)[0].softmax(dim=1)
    preds_argmax = preds.argmax(dim=1).tolist()
    return [learner.dls.vocab[idx] for idx in preds_argmax]


def _clean_character_list(character_list: list) -> str:
    """
    Post-process the raw per-cell prediction list for one page:

    1. Replace the label "empty_braille_cell" with the actual Unicode
       empty braille cell character (U+2800).
    2. Strip trailing empty cells from each line (lines are 41 cells wide).
    3. Remove lines that are entirely empty cells.
    4. Remove typos (≥ 2 consecutive full braille cells ⠿).
    5. Replace line-continuation-with-space symbols (⠐⠐) with a space.
    """
    # 1. Normalise the empty-cell label.
    character_list = [
        "⠀" if ch == "empty_braille_cell" else ch
        for ch in character_list
    ]

    # 2 & 3. Strip trailing spaces from each line; skip all-empty lines.
    num_lines = int(len(character_list) / CHARS_PER_LINE)
    for i in range(num_lines - 1, -1, -1):
        idx = i * CHARS_PER_LINE - 2  # index of the last cell on line i
        line_slice = character_list[idx - 40 : idx + 1]
        if line_slice == CHARS_PER_LINE * ["⠀"]:
            continue  # all-empty line — leave for the join+replace below
        while idx >= 0 and character_list[idx] == "⠀" and character_list[idx + 1] == "⠀":
            character_list.pop(idx)
            idx -= 1

    page_string = "".join(character_list).replace(CHARS_PER_LINE * "⠀", "")

    # 4. Remove typos (two or more consecutive full braille cells).
    page_string = re.sub("⠿(⠿+)", "", page_string)

    # 5. Replace line-continuation-with-space symbols.
    page_string = page_string.replace("⠐⠐", "⠀")

    return page_string


def process_jpeg_pages(
    jpeg_file_names: list,
    cwd: str,
    learner,
    output_path: str,
    ocr_text_file_name: str,
    progress_bar,
) -> str:
    """
    Run the full OCR pipeline on every JPEG in *jpeg_file_names*.

    Returns the concatenated braille character string for the whole document
    and writes the raw OCR results to a .txt file in *output_path*.
    """
    raw_data_dir = os.path.join(cwd, "OCR Raw Data")
    rectangles_dir = os.path.join(cwd, RECTANGLES_FOLDER)
    txt_path = os.path.join(output_path, f"{ocr_text_file_name}-OCR results.txt")

    full_string = ""

    with open(txt_path, "a+") as f:
        for i, jpeg_name in enumerate(jpeg_file_names):
            # Insert page separator after the first page.
            if i > 0:
                f.write("\n\n")
                full_string += "⠀"

            # ── Load image ────────────────────────────────────────────────────
            img_path = os.path.join(raw_data_dir, jpeg_name)
            text_image = cv2.imread(img_path)
            text_image_copy = text_image.copy()
            text_image_gray = cv2.cvtColor(text_image, cv2.COLOR_BGR2GRAY)

            # ── Segment ───────────────────────────────────────────────────────
            coords = get_character_coordinates(
                text_image_gray,
                text_image_copy,
                rectangles_dir,
                jpeg_name[:-4],
            )

            # ── Crop & predict ────────────────────────────────────────────────
            char_files = _crop_and_save_characters(text_image_gray, coords, output_path)
            character_list = _predict_characters(learner, char_files)

            # ── Clean up temp crops ───────────────────────────────────────────
            for j in range(len(character_list)):
                temp = os.path.join(output_path, f"{j}.jpg")
                if os.path.exists(temp):
                    os.remove(temp)

            # ── Post-process ──────────────────────────────────────────────────
            page_string = _clean_character_list(character_list)
            full_string += page_string
            f.write(page_string)

            progress_bar()

    return full_string
