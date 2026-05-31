"""
dot_snapper.py
--------------
Snaps noisy detected dots into legal Braille slots.
Calculates slot confidence and spatial error.
"""

from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
import numpy as np
from braille_ocr.realtime.grid_estimator import BrailleGrid, GridCell

@dataclass
class SnappedCell:
    cell_id: int
    dots: List[int] # 6-element binary array [dot1, dot2, dot3, dot4, dot5, dot6]
    confidence: float
    snapped_coords: List[Tuple[float, float]] # coordinates for each of the 6 slots

def snap_dots_to_grid(dots: List[Tuple[int, int, int]], grid: BrailleGrid, med_r: float) -> List[SnappedCell]:
    """
    Maps detected dots to the 6 legal Braille slots in each cell.
    """
    if not grid or not grid.cells:
        return []

    snapped_cells = []
    snap_threshold = med_r * 2.0 # maximum distance to snap a dot

    for cell in grid.cells:
        # Define the 6 expected slot coordinates
        # 1 4
        # 2 5
        # 3 6
        expected_slots = [
            (cell.left_x, cell.row_centers[0]),  # dot 1
            (cell.left_x, cell.row_centers[1]),  # dot 2
            (cell.left_x, cell.row_centers[2]),  # dot 3
            (cell.right_x, cell.row_centers[0]), # dot 4
            (cell.right_x, cell.row_centers[1]), # dot 5
            (cell.right_x, cell.row_centers[2]), # dot 6
        ]
        
        binary_dots = [0] * 6
        total_error = 0.0
        snapped_count = 0
        
        for i, (ex, ey) in enumerate(expected_slots):
            best_dist = float('inf')
            # Find closest dot
            for cx, cy, r in dots:
                dist = np.hypot(cx - ex, cy - ey)
                if dist < best_dist:
                    best_dist = dist
                    
            if best_dist < snap_threshold:
                binary_dots[i] = 1
                total_error += best_dist
                snapped_count += 1
                
        # Confidence calculation
        avg_error = total_error / max(snapped_count, 1)
        # Normalize error to 0-1 confidence where 0 error = 1.0 confidence
        confidence = max(0.0, 1.0 - (avg_error / snap_threshold))
        
        # If no dots snapped, confidence is 0
        if snapped_count == 0:
            confidence = 0.0
            
        snapped_cells.append(SnappedCell(
            cell_id=cell.cell_id,
            dots=binary_dots,
            confidence=confidence,
            snapped_coords=expected_slots
        ))
        
    return snapped_cells
