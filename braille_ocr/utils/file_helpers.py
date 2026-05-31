"""
file_helpers.py
---------------
Small file-system utilities shared across the pipeline.
"""

import os
import re


def extract_folder_name(filename: str) -> str:
    """
    Return the portion of *filename* up to (but not including) the last hyphen.

    Example: "Alice-0001.jpg" -> "Alice"
    """
    indices = [m.start() for m in re.finditer("-", filename)]
    if not indices:
        raise ValueError(
            f"Filename '{filename}' must contain at least one hyphen '-'."
        )
    return filename[: indices[-1]]


def collect_jpeg_names(directory: str) -> list:
    """Return a sorted list of .jpg filenames found in *directory*."""
    return sorted(f for f in os.listdir(directory) if f.lower().endswith(".jpg"))


def ensure_output_dirs(*paths: str) -> None:
    """Create each directory in *paths* if it does not already exist."""
    for path in paths:
        os.makedirs(path, exist_ok=True)
