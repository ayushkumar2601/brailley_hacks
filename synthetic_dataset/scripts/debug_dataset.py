"""
debug_dataset.py
----------------
Visual debugger for the dataset conversion pipeline.
Visualizes the original image, preprocessing, reconstructed lattice, 
and snapped dots for a single dataset image to ensure the geometry pipeline
is correctly aligned with the dataset image.
"""

import os
import cv2
import numpy as np
import sys
from pathlib import Path

# Import the existing inference pipeline modules
from braille_ocr.realtime.preprocessing import normalize_lighting, generate_binary_mask
from braille_ocr.realtime.blob_detector import detect_dots
from braille_ocr.realtime.grid_estimator import estimate_grid
from braille_ocr.realtime.dot_snapper import snap_dots_to_grid

def debug_image(image_path: str, out_path: str):
    """
    Runs the inference preprocessing pipeline and visualizes the results.
    """
    img = cv2.imread(image_path)
    if img is None:
        print(f"Failed to load {image_path}")
        return
        
    gray, enhanced = normalize_lighting(img)
    binary = generate_binary_mask(enhanced)
    
    dots, _ = detect_dots(binary)
    if not dots:
        print("No dots found.")
        return
        
    med_r = float(np.median([d[2] for d in dots])) if dots else 5.0
    grid = estimate_grid(dots, gray.shape)
    
    if not grid or not grid.cells:
        print("Failed to estimate grid.")
        return
        
    snapped_cells = snap_dots_to_grid(dots, grid, med_r)
    
    # Visualization
    vis_img = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    
    # Draw original detected dots in red
    for x, y, r in dots:
        cv2.circle(vis_img, (int(x), int(y)), int(r), (0, 0, 255), 1)
        
    # Draw grid and snapped cells
    for cell in snapped_cells:
        if cell.cell_id >= len(grid.cells):
            continue
            
        g_cell = grid.cells[cell.cell_id]
        
        # Draw bounding box
        x, y, w, h = g_cell.box
        cv2.rectangle(vis_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Draw cell ID and binary label
        binary_str = "".join(map(str, cell.dots))
        cv2.putText(vis_img, f"ID:{cell.cell_id}", (x, max(0, y - 5)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 100, 0), 1)
        cv2.putText(vis_img, binary_str, (x, y + h + 15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
                    
    cv2.imwrite(out_path, vis_img)
    print(f"Debug visualization saved to {out_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python debug_dataset.py <input_image> <output_image>")
    else:
        debug_image(sys.argv[1], sys.argv[2])
