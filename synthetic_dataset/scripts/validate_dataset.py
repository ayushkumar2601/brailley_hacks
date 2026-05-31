"""
validate_dataset.py
-------------------
Validates the generated training data.
- Checks image dimensions (must be 64x64 or 32x32)
- Verifies binary vector length and type
- Detects corrupt labels or empty images
- Identifies gross class imbalance in dot occupancy
"""

import os
import glob
import json
import cv2

def validate_training_data(data_dir: str = "datasets/training_data"):
    images_dir = os.path.join(data_dir, "images")
    labels_dir = os.path.join(data_dir, "labels")
    
    if not os.path.exists(images_dir) or not os.path.exists(labels_dir):
        print(f"Data directory {data_dir} not found.")
        return
        
    image_files = glob.glob(os.path.join(images_dir, "*.jpg"))
    
    total_images = len(image_files)
    invalid_images = 0
    invalid_labels = 0
    
    # Track dot occupancy across the dataset
    dot_counts = [0] * 6
    
    print(f"Validating {total_images} training samples...")
    
    for img_path in image_files:
        basename = os.path.basename(img_path)
        base_id = basename.replace(".jpg", "")
        label_path = os.path.join(labels_dir, f"{base_id}.json")
        
        # 1. Image Validation
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"CORRUPT IMAGE: {basename}")
            invalid_images += 1
            continue
            
        h, w = img.shape
        if (w, h) not in [(32, 32), (64, 64)]:
            print(f"INVALID DIMENSIONS {w}x{h}: {basename}")
            invalid_images += 1
            continue
            
        # 2. Label Validation
        if not os.path.exists(label_path):
            print(f"MISSING LABEL: {basename}")
            invalid_labels += 1
            continue
            
        try:
            with open(label_path, "r") as f:
                label_data = json.load(f)
                
            dots = label_data.get("dots", [])
            if len(dots) != 6 or not all(d in [0, 1] for d in dots):
                print(f"INVALID DOT VECTOR {dots}: {basename}")
                invalid_labels += 1
                continue
                
            for i, d in enumerate(dots):
                dot_counts[i] += d
                
        except json.JSONDecodeError:
            print(f"CORRUPT LABEL JSON: {basename}")
            invalid_labels += 1
            
    # Report
    print("\n--- Validation Report ---")
    print(f"Total Samples: {total_images}")
    print(f"Invalid Images: {invalid_images}")
    print(f"Invalid Labels: {invalid_labels}")
    print("Dot Occupancy (Total occurrences across dataset):")
    for i, c in enumerate(dot_counts):
        percentage = (c / max(1, total_images)) * 100
        print(f"  Dot {i+1}: {c} ({percentage:.1f}%)")
        
    if invalid_images == 0 and invalid_labels == 0:
        print("\n✅ Dataset validation passed!")
    else:
        print("\n⚠️ Dataset validation failed!")

if __name__ == "__main__":
    validate_training_data()
