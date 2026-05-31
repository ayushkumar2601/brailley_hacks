"""
grid_estimator.py
-----------------
Global Braille grid estimation. Infers the invisible Braille lattice from detected blob positions.
Estimates spacing, rows, columns, line positions, and cell boundaries.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

@dataclass
class GridCell:
    cell_id: int
    left_x: float
    right_x: float
    row_centers: List[float]  # [row1_y, row2_y, row3_y]
    box: Tuple[int, int, int, int]

@dataclass
class BrailleGrid:
    rows: List[float]
    columns: List[float]
    cells: List[GridCell]
    row_spacing: float
    col_spacing: float
    inter_cell_spacing: float
    line_spacing: float
    confidence: float

def _cluster_1d(values: List[float], threshold: float) -> List[float]:
    if not values:
        return []
    sorted_vals = sorted(values)
    clusters = [[sorted_vals[0]]]
    for v in sorted_vals[1:]:
        if v - clusters[-1][-1] <= threshold:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return [float(np.mean(c)) for c in clusters]

def estimate_grid(dots: List[Tuple[int, int, int]], img_shape: Tuple[int, int]) -> Optional[BrailleGrid]:
    """
    Infers the Braille grid lattice from dot coordinates.
    Input: list of (x, y, radius)
    """
    if len(dots) < 2:
        return None

    radii = [d[2] for d in dots]
    med_r = float(np.median(radii))
    min_gap = med_r * 1.5

    # 1. Spacing Analysis
    ys = sorted(set(d[1] for d in dots))
    xs = sorted(set(d[0] for d in dots))
    
    y_gaps = [ys[i] - ys[i - 1] for i in range(1, len(ys)) if ys[i] - ys[i - 1] > min_gap]
    x_gaps = [xs[i] - xs[i - 1] for i in range(1, len(xs)) if xs[i] - xs[i - 1] > min_gap]
    
    row_spacing = float(np.median(y_gaps)) if y_gaps else med_r * 2.5
    if x_gaps:
        x_gaps_sorted = sorted(x_gaps)
        col_spacing = float(x_gaps_sorted[0])
        if len(x_gaps_sorted) > 1 and x_gaps_sorted[-1] / max(x_gaps_sorted[0], 1) < 1.5:
            col_spacing = float(np.median(x_gaps))
    else:
        col_spacing = med_r * 3.5

    row_spacing = max(row_spacing, med_r * 1.5)
    col_spacing = max(col_spacing, med_r * 1.5)
    inter_cell_spacing = max(col_spacing * 2.0, med_r * 4.0)
    line_spacing = row_spacing * 3.2

    # 2. Coordinate Clustering
    all_ys = [d[1] for d in dots]
    all_xs = [d[0] for d in dots]
    
    # Cluster into Braille lines (groups of 3 rows)
    y_min = min(all_ys)
    line_groups: dict[int, list] = {}
    for d in dots:
        line_idx = int((d[1] - y_min) / max(line_spacing, 1))
        line_groups.setdefault(line_idx, []).append(d)

    grid_cells: List[GridCell] = []
    global_rows: List[float] = []
    global_cols: List[float] = []
    cell_counter = 0

    img_h = img_shape[0] if img_shape and img_shape[0] > 0 else 0

    for line_idx in sorted(line_groups.keys()):
        line_dots = line_groups[line_idx]
        if not line_dots:
            continue
            
        line_ys = [d[1] for d in line_dots]
        y_clusters = _cluster_1d(line_ys, row_spacing * 0.5)
        
        # Infer the 3 rows
        if len(y_clusters) == 0:
            base = img_h * 0.2 if img_h > 0 else 0.0
            r1, r2, r3 = base, base + row_spacing, base + row_spacing * 2
        elif len(y_clusters) == 1:
            y0 = y_clusters[0]
            if img_h > 0:
                rel = y0 / img_h
                if rel < 0.35: r1, r2, r3 = y0, y0 + row_spacing, y0 + row_spacing * 2
                elif rel < 0.65: r1, r2, r3 = y0 - row_spacing, y0, y0 + row_spacing
                else: r1, r2, r3 = y0 - row_spacing * 2, y0 - row_spacing, y0
            else:
                r1, r2, r3 = y0, y0 + row_spacing, y0 + row_spacing * 2
        elif len(y_clusters) == 2:
            y0, y1 = y_clusters[0], y_clusters[1]
            gap = y1 - y0
            if gap > row_spacing * 1.4:
                r1, r2, r3 = y0, (y0 + y1) / 2, y1
            else:
                r1, r2, r3 = y0, y1, y1 + row_spacing
        else:
            r1, r2, r3 = y_clusters[0], y_clusters[1], y_clusters[2]
            
        global_rows.extend([r1, r2, r3])

        line_xs = [d[0] for d in line_dots]
        col_centers = _cluster_1d(line_xs, col_spacing * 0.8)
        global_cols.extend(col_centers)
        
        # Pair columns into cells
        i = 0
        while i < len(col_centers):
            lx = col_centers[i]
            if i + 1 < len(col_centers):
                rx = col_centers[i + 1]
                gap = rx - lx
                if gap <= col_spacing * 1.8:
                    rx = col_centers[i + 1]
                    i += 2
                else:
                    rx = lx + col_spacing * 0.8
                    i += 1
            else:
                rx = lx + col_spacing * 0.8
                i += 1
                
            box_x = max(0, int(lx) - int(med_r))
            box_y = max(0, int(r1) - int(med_r))
            box_w = int(rx - lx) + int(med_r * 2)
            box_h = int(r3 - r1) + int(med_r * 2)
                
            cell = GridCell(
                cell_id=cell_counter,
                left_x=lx,
                right_x=rx,
                row_centers=[r1, r2, r3],
                box=(box_x, box_y, box_w, box_h)
            )
            grid_cells.append(cell)
            cell_counter += 1

    return BrailleGrid(
        rows=sorted(set(global_rows)),
        columns=sorted(set(global_cols)),
        cells=grid_cells,
        row_spacing=row_spacing,
        col_spacing=col_spacing,
        inter_cell_spacing=inter_cell_spacing,
        line_spacing=line_spacing,
        confidence=1.0 # can be based on grid regularity
    )
