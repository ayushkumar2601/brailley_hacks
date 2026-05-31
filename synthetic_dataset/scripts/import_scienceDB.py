import os
import json
import xml.etree.ElementTree as ET
import shutil
from pathlib import Path
from typing import Dict, List, Any

RAW_DATASET_PATH = Path("datasets/scienceDB")
PROCESSED_DATASET_PATH = Path("datasets/scienceDB_processed")

def setup_directories():
    """Create the necessary directory structure for the processed dataset."""
    dirs = [
        "raw",
        "normalized",
        "geometry_annotations",
        "segmentation_annotations",
        "labels",
        "metadata"
    ]
    for d in dirs:
        (PROCESSED_DATASET_PATH / d).mkdir(parents=True, exist_ok=True)

def parse_xml(xml_path: Path) -> Dict[str, Any]:
    """Parse VOC XML geometry annotations."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        bboxes = []
        for obj in root.findall('object'):
            bndbox = obj.find('bndbox')
            if bndbox is not None:
                bbox = {
                    'xmin': int(bndbox.find('xmin').text),
                    'ymin': int(bndbox.find('ymin').text),
                    'xmax': int(bndbox.find('xmax').text),
                    'ymax': int(bndbox.find('ymax').text)
                }
                bboxes.append(bbox)
        return {'bboxes': bboxes}
    except Exception as e:
        print(f"Error parsing XML {xml_path}: {e}")
        return {}

def parse_json(json_path: Path) -> Dict[str, Any]:
    """Parse segmentation JSON annotations."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error parsing JSON {json_path}: {e}")
        return {}

def parse_txt(txt_path: Path) -> str:
    """Parse character-level labels from TXT."""
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error parsing TXT {txt_path}: {e}")
        return ""

def process_dataset():
    """Main loop to parse all folders and extract metadata."""
    if not RAW_DATASET_PATH.exists():
        print(f"Error: {RAW_DATASET_PATH} does not exist.")
        return

    setup_directories()

    unified_metadata = []

    # Assuming common structure or recursive search
    # This searches for all images and tries to find corresponding annotations
    for img_path in RAW_DATASET_PATH.rglob('*.[jp][pn][g]'):
        if 'processed' in str(img_path):
            continue

        base_name = img_path.stem
        relative_parent = img_path.parent.relative_to(RAW_DATASET_PATH)
        
        # Determine train/test split from path
        split = 'test' if 'test' in str(relative_parent).lower() else 'train'

        # Look for annotations
        xml_path = img_path.with_suffix('.xml')
        json_path = img_path.with_suffix('.json')
        txt_path = img_path.with_suffix('.txt')

        record = {
            'image_id': base_name,
            'split': split,
            'original_path': str(img_path),
            'processed_image_path': str(PROCESSED_DATASET_PATH / "raw" / img_path.name),
            'annotations': {
                'geometry_present': xml_path.exists(),
                'segmentation_present': json_path.exists(),
                'labels_present': txt_path.exists()
            }
        }

        # Copy image
        shutil.copy2(img_path, PROCESSED_DATASET_PATH / "raw" / img_path.name)

        if xml_path.exists():
            xml_data = parse_xml(xml_path)
            out_xml = PROCESSED_DATASET_PATH / "geometry_annotations" / f"{base_name}.json"
            with open(out_xml, 'w') as f:
                json.dump(xml_data, f, indent=2)
            record['geometry'] = xml_data

        if json_path.exists():
            json_data = parse_json(json_path)
            out_json = PROCESSED_DATASET_PATH / "segmentation_annotations" / f"{base_name}.json"
            with open(out_json, 'w') as f:
                json.dump(json_data, f, indent=2)
            record['segmentation'] = json_data

        if txt_path.exists():
            txt_data = parse_txt(txt_path)
            out_txt = PROCESSED_DATASET_PATH / "labels" / f"{base_name}.txt"
            with open(out_txt, 'w') as f:
                f.write(txt_data)
            record['label'] = txt_data

        unified_metadata.append(record)

    # Save unified metadata
    metadata_out = PROCESSED_DATASET_PATH / "metadata" / "unified_metadata.json"
    with open(metadata_out, 'w') as f:
        json.dump(unified_metadata, f, indent=2)

    print(f"Processed {len(unified_metadata)} records.")
    print("Dataset import and normalization complete.")

if __name__ == "__main__":
    process_dataset()
