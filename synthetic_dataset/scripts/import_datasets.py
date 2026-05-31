"""
import_datasets.py
------------------
Imports and organizes raw datasets (DSBI, AngelinaDataset) into the standardized
BrailleScan directory structure. Generates initial metadata manifests for each image.
"""

import os
import shutil
import json
from pathlib import Path


def process_dsbi(src_dir: str, dest_dir: str) -> int:
    """
    Import images from the DSBI raw repository into dest_dir/raw/.
    Returns count of imported images.
    """
    print(f"Processing DSBI dataset from {src_dir} to {dest_dir}...")
    src_path = Path(src_dir).resolve()
    dest_path = (Path(dest_dir) / "raw").resolve()
    annot_path = (Path(dest_dir) / "annotations").resolve()
    dest_path.mkdir(parents=True, exist_ok=True)
    annot_path.mkdir(parents=True, exist_ok=True)

    image_files = []
    for ext in ("*.jpg", "*.png", "*.JPG", "*.PNG"):
        image_files.extend(src_path.rglob(ext))

    count = 0
    for img_file in image_files:
        new_name = f"dsbi_{count:04d}_{img_file.name}"
        dest_file = dest_path / new_name

        shutil.copy2(img_file, dest_file)

        # Generate metadata
        try:
            rel = img_file.relative_to(src_path)
        except ValueError:
            rel = img_file.name

        metadata = {
            "source": "dsbi",
            "filename": new_name,
            "original_path": str(rel),
            "dataset_type": "real_scanned",
            "contains_perspective_distortion": False,
            "contains_shadow": False,
        }

        meta_file = annot_path / f"{new_name}.json"
        with open(meta_file, "w") as f:
            json.dump(metadata, f, indent=2)

        count += 1

    print(f"  ✅ Imported {count} DSBI images.")
    return count


def process_angelina(src_dir: str, dest_dir: str) -> int:
    """
    Import AngelinaDataset images into dest_dir/raw/.
    Returns count of imported images.
    """
    print(f"Processing AngelinaDataset from {src_dir} to {dest_dir}...")
    src_path = Path(src_dir).resolve()

    if not src_path.exists():
        print(f"  ⚠️  AngelinaDataset not found at {src_dir}. Skipping.")
        return 0

    dest_path = (Path(dest_dir) / "raw").resolve()
    label_path = (Path(dest_dir) / "labels").resolve()
    dest_path.mkdir(parents=True, exist_ok=True)
    label_path.mkdir(parents=True, exist_ok=True)

    image_files = []
    for ext in ("*.jpg", "*.JPG", "*.png", "*.PNG"):
        image_files.extend(src_path.rglob(ext))

    count = 0
    for img_file in image_files:
        new_name = f"angel_{count:04d}_{img_file.name}"
        dest_file = dest_path / new_name
        shutil.copy2(img_file, dest_file)

        try:
            rel = img_file.relative_to(src_path)
        except ValueError:
            rel = img_file.name

        metadata = {
            "source": "angelina",
            "filename": new_name,
            "original_path": str(rel),
            "dataset_type": "real_photographed",
            "contains_perspective_distortion": True,
            "contains_shadow": True,
        }

        meta_file = label_path / f"{new_name}.json"
        with open(meta_file, "w") as f:
            json.dump(metadata, f, indent=2)

        count += 1

    print(f"  ✅ Imported {count} Angelina images.")
    return count


if __name__ == "__main__":
    total = 0
    dsbi_src = "datasets/dsbi/raw_repo"
    if os.path.exists(dsbi_src):
        total += process_dsbi(dsbi_src, "datasets/dsbi")
    else:
        print("DSBI repo not found. Clone it first with:")
        print("  git clone https://github.com/yeluo1994/DSBI.git datasets/dsbi/raw_repo")

    angelina_src = "datasets/angelina/raw_repo"
    total += process_angelina(angelina_src, "datasets/angelina")

    print(f"\nTotal images imported: {total}")
