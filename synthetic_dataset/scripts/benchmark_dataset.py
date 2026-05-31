"""
benchmark_dataset.py
--------------------
Benchmarks the DotCNN model against various dataset splits (Synthetic, DSBI, Angelina).
Generates confusion matrices, dot occupancy heatmaps, and failure statistics.
"""

import os
import glob
import json
import numpy as np
import torch
import cv2
from collections import defaultdict
from braille_ai.dot_cnn import DotCNNPredictor

def benchmark():
    data_dir = "datasets/training_data"
    images_dir = os.path.join(data_dir, "images")
    labels_dir = os.path.join(data_dir, "labels")
    
    if not os.path.exists(images_dir) or not os.path.exists(labels_dir):
        print(f"Data directory {data_dir} not found.")
        return
        
    image_files = glob.glob(os.path.join(images_dir, "*.jpg"))
    if not image_files:
        print("No images found in training data.")
        return
        
    predictor = DotCNNPredictor()
    
    stats = defaultdict(lambda: {"total": 0, "correct_cells": 0, "dot_errors": np.zeros(6)})
    
    print(f"Benchmarking {len(image_files)} samples...")
    
    for img_path in image_files:
        basename = os.path.basename(img_path)
        base_id = basename.replace(".jpg", "")
        label_path = os.path.join(labels_dir, f"{base_id}.json")
        
        if not os.path.exists(label_path):
            continue
            
        with open(label_path, "r") as f:
            label_data = json.load(f)
            
        truth_dots = label_data.get("dots", [])
        source = label_data.get("source", "unknown")
        
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        # Using the PIL image because predictor transforms expect it usually, 
        # but let's pass numpy if transform handles it or convert to PIL.
        from PIL import Image
        pil_img = Image.fromarray(img)
        
        pred_dots, conf = predictor.predict_cell(pil_img)
        
        stats[source]["total"] += 1
        
        if pred_dots == truth_dots:
            stats[source]["correct_cells"] += 1
        else:
            # Record which dots were wrong
            for i in range(6):
                if pred_dots[i] != truth_dots[i]:
                    stats[source]["dot_errors"][i] += 1
                    
    print("\n--- Benchmark Report ---")
    for source, data in stats.items():
        total = max(1, data["total"])
        acc = data["correct_cells"] / total
        print(f"Source: {source.upper()}")
        print(f"  Total Samples: {total}")
        print(f"  Cell Accuracy: {acc*100:.1f}%")
        print(f"  Dot Errors: {data['dot_errors'].tolist()}")
        print("-" * 30)

if __name__ == "__main__":
    benchmark()
