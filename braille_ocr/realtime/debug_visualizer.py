"""
debug_visualizer.py
--------------------
Visual debugging overlay system for the Braille OCR pipeline.

Produces annotated images showing every stage of processing so that
developers can *see* why OCR fails.  Supports multiple debug modes and
can optionally save intermediate frames to disk.

Usage:
    from braille_ocr.realtime.debug_visualizer import DebugVisualizer

    dbg = DebugVisualizer(enabled=True, save_to_disk=True)
    dbg.set_perspective(frame, contour)
    dbg.set_preprocessing(gray, enhanced, binary)
    dbg.set_blobs(frame, accepted, rejected)
    composite = dbg.build_composite()
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from braille_ocr.realtime.grid_estimator import BrailleGrid, GridCell
from braille_ocr.realtime.dot_snapper import SnappedCell

logger = logging.getLogger(__name__)


# ── Debug output directory ────────────────────────────────────────────────────

_DEBUG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "braille_ai", "temp", "debug",
)


class DebugMode(Enum):
    """Available debug overlay modes."""
    RAW = auto()
    PERSPECTIVE = auto()
    NORMALIZED = auto()
    THRESHOLD = auto()
    BLOBS = auto()
    COMPOSITE = auto()


@dataclass
class DebugVisualizer:
    """
    Collects intermediate pipeline images and produces debug overlays.

    Enable with ``enabled=True``.  When ``save_to_disk=True``, images
    are written to ``braille_ai/temp/debug/`` on every call to
    :meth:`save_all`.
    """

    enabled: bool = False
    save_to_disk: bool = False
    save_dir: str = _DEBUG_DIR
    show_ids: bool = False

    # Collected frames — populated by setter methods
    _raw_frame: Optional[np.ndarray] = field(default=None, repr=False)
    _perspective_frame: Optional[np.ndarray] = field(default=None, repr=False)
    _perspective_contour: Optional[np.ndarray] = field(default=None, repr=False)
    _gray: Optional[np.ndarray] = field(default=None, repr=False)
    _enhanced: Optional[np.ndarray] = field(default=None, repr=False)
    _binary: Optional[np.ndarray] = field(default=None, repr=False)
    _blob_frame: Optional[np.ndarray] = field(default=None, repr=False)
    _accepted_dots: List[Tuple[int, int, int]] = field(default_factory=list)
    _rejected_dots: List[Tuple[int, int, int]] = field(default_factory=list)
    _spacing_h: float = 0.0
    _spacing_v: float = 0.0
    _grid: Optional[BrailleGrid] = field(default=None, repr=False)
    _snapped_cells: List[SnappedCell] = field(default_factory=list)
    _extracted_patches: List[np.ndarray] = field(default_factory=list)
    _cnn_confidences: List[float] = field(default_factory=list)
    _final_text: str = ""

    # ── Setters ───────────────────────────────────────────────────────────

    def set_raw(self, frame: np.ndarray) -> None:
        if self.enabled:
            self._raw_frame = frame.copy()

    def set_perspective(
        self,
        warped: np.ndarray,
        contour: Optional[np.ndarray] = None,
    ) -> None:
        if self.enabled:
            self._perspective_frame = warped.copy()
            self._perspective_contour = contour

    def set_preprocessing(
        self,
        gray: np.ndarray,
        enhanced: np.ndarray,
        binary: np.ndarray,
    ) -> None:
        if self.enabled:
            self._gray = gray.copy()
            self._enhanced = enhanced.copy()
            self._binary = binary.copy()

    def set_blobs(
        self,
        frame: np.ndarray,
        accepted: List[Tuple[int, int, int]],
        rejected: List[Tuple[int, int, int]],
    ) -> None:
        if self.enabled:
            self._blob_frame = frame.copy()
            self._accepted_dots = list(accepted)
            self._rejected_dots = list(rejected)

    def set_spacing(self, horizontal: float, vertical: float) -> None:
        if self.enabled:
            self._spacing_h = horizontal
            self._spacing_v = vertical

    def set_grid(self, grid: Optional[BrailleGrid]) -> None:
        if self.enabled:
            self._grid = grid

    def set_snapped_cells(self, cells: List[SnappedCell]) -> None:
        if self.enabled:
            self._snapped_cells = list(cells)

    def set_cnn_results(self, patches: List[np.ndarray], confidences: List[float], text: str) -> None:
        if self.enabled:
            self._extracted_patches = list(patches)
            self._cnn_confidences = list(confidences)
            self._final_text = text

    # ── Overlay builders ──────────────────────────────────────────────────

    def draw_perspective_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw the detected document boundary on *frame*."""
        vis = frame.copy()
        if self._perspective_contour is not None:
            pts = self._perspective_contour.reshape(-1, 2).astype(np.int32)
            cv2.polylines(vis, [pts], isClosed=True, color=(0, 255, 255), thickness=2)
            for i, (x, y) in enumerate(pts):
                labels = ["TL", "TR", "BR", "BL"]
                label = labels[i] if i < 4 else str(i)
                cv2.circle(vis, (x, y), 6, (0, 200, 255), -1)
                cv2.putText(vis, label, (x + 8, y - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        return vis

    def draw_blob_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw accepted (green) and rejected (red) dots."""
        vis = frame.copy() if len(frame.shape) == 3 else cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        for i, (cx, cy, r) in enumerate(self._rejected_dots):
            cv2.circle(vis, (cx, cy), max(r + 2, 5), (0, 0, 220), 2)
            if self.show_ids:
                cv2.putText(vis, f"R{i}", (cx + r + 3, cy - 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 0, 200), 1)

        for i, (cx, cy, r) in enumerate(self._accepted_dots):
            cv2.circle(vis, (cx, cy), max(r + 2, 5), (0, 220, 100), 2)
            if self.show_ids:
                cv2.putText(vis, str(i), (cx + r + 3, cy - 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 200, 80), 1)

        return vis

    def draw_spacing_lines(self, frame: np.ndarray) -> np.ndarray:
        """Draw estimated horizontal and vertical spacing guides."""
        vis = frame.copy() if len(frame.shape) == 3 else cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        h, w = vis.shape[:2]

        if self._spacing_h > 5 and self._accepted_dots:
            xs = sorted(set(d[0] for d in self._accepted_dots))
            for x in xs:
                cv2.line(vis, (x, 0), (x, h), (80, 80, 180), 1)

        if self._spacing_v > 5 and self._accepted_dots:
            ys = sorted(set(d[1] for d in self._accepted_dots))
            for y in ys:
                cv2.line(vis, (0, y), (w, y), (80, 180, 80), 1)

        # Legend
        cv2.putText(
            vis,
            f"H-sp: {self._spacing_h:.1f}  V-sp: {self._spacing_v:.1f}",
            (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 220), 1,
        )
        return vis

    def draw_grid_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw the inferred Braille grid (rows, columns, cell boxes)."""
        vis = frame.copy() if len(frame.shape) == 3 else cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        if not self._grid:
            return vis
            
        h, w = vis.shape[:2]
        
        # Draw cell boxes
        for cell in self._grid.cells:
            bx, by, bw, bh = cell.box
            cv2.rectangle(vis, (bx, by), (bx + bw, by + bh), (255, 120, 0), 1)
            
        # Draw rows and columns
        for row_y in self._grid.rows:
            cv2.line(vis, (0, int(row_y)), (w, int(row_y)), (0, 0, 255), 1)
        for col_x in self._grid.columns:
            cv2.line(vis, (int(col_x), 0), (int(col_x), h), (0, 255, 0), 1)
            
        return vis
        
    def draw_snapped_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw snapped dots and cell labels."""
        vis = frame.copy() if len(frame.shape) == 3 else cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        
        for cell in self._snapped_cells:
            binary_str = f"[{','.join(map(str, cell.dots))}]"
            # get the box from the grid if possible
            if self._grid and cell.cell_id < len(self._grid.cells):
                gcell = self._grid.cells[cell.cell_id]
                bx, by, bw, bh = gcell.box
                cv2.putText(vis, binary_str, (bx, max(0, by - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
                
            for i, coord in enumerate(cell.snapped_coords):
                if cell.dots[i]:
                    # Snapped dot (active)
                    cv2.circle(vis, (int(coord[0]), int(coord[1])), 4, (0, 255, 255), -1)
                else:
                    # Empty slot
                    cv2.circle(vis, (int(coord[0]), int(coord[1])), 2, (100, 100, 100), -1)
                    
        return vis
        
    def draw_final_text_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw final decoded text and CNN confidences."""
        vis = frame.copy() if len(frame.shape) == 3 else cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        h, w = vis.shape[:2]
        
        # Draw background panel at bottom
        cv2.rectangle(vis, (0, h - 40), (w, h), (30, 30, 30), -1)
        
        # Draw final text
        cv2.putText(vis, f"Decoded: {self._final_text}", (10, h - 15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
        # Draw average confidence if available
        if self._cnn_confidences:
            avg_conf = sum(self._cnn_confidences) / len(self._cnn_confidences)
            cv2.putText(vis, f"Avg Conf: {avg_conf:.2f}", (w - 180, h - 15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 1)
                        
        return vis

    # ── Composite builder ─────────────────────────────────────────────────

    def build_composite(self, target_h: int = 360) -> Optional[np.ndarray]:
        """
        Assemble a side-by-side composite of all debug stages.

        Returns a single BGR image with panels for:
          [raw | perspective | enhanced | binary | blobs]

        Returns ``None`` if debugging is disabled or no frames collected.
        """
        if not self.enabled:
            return None

        panels: List[np.ndarray] = []

        def _to_bgr(img: Optional[np.ndarray]) -> Optional[np.ndarray]:
            if img is None:
                return None
            if len(img.shape) == 2:
                return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            return img

        def _resize(img: np.ndarray) -> np.ndarray:
            h_img, w_img = img.shape[:2]
            scale = target_h / max(h_img, 1)
            new_w = max(1, int(w_img * scale))
            return cv2.resize(img, (new_w, target_h))

        # Raw
        raw = _to_bgr(self._raw_frame)
        if raw is not None:
            panels.append(_add_label(_resize(raw), "RAW"))

        # Perspective
        persp = _to_bgr(self._perspective_frame)
        if persp is not None:
            panels.append(_add_label(_resize(persp), "PERSPECTIVE"))
        elif raw is not None and self._perspective_contour is not None:
            overlay = self.draw_perspective_overlay(raw)
            panels.append(_add_label(_resize(overlay), "CONTOUR"))

        # Enhanced
        enh = _to_bgr(self._enhanced)
        if enh is not None:
            panels.append(_add_label(_resize(enh), "ENHANCED"))

        # Binary
        bm = _to_bgr(self._binary)
        if bm is not None:
            panels.append(_add_label(_resize(bm), "THRESHOLD"))

        # Blob overlay
        blob_base = _to_bgr(self._perspective_frame or self._raw_frame)
        if blob_base is not None and self._accepted_dots:
            blob_vis = self.draw_blob_overlay(blob_base)
            blob_vis = self.draw_spacing_lines(blob_vis)
            panels.append(_add_label(_resize(blob_vis), "BLOBS"))
            
        # Grid and Snapped Overlay
        if blob_base is not None and (self._grid or self._snapped_cells):
            grid_vis = self.draw_grid_overlay(blob_base)
            grid_vis = self.draw_snapped_overlay(grid_vis)
            panels.append(_add_label(_resize(grid_vis), "GRID+SNAPPED"))
            
        # Final Text & CNN Overlay
        if blob_base is not None and self._final_text:
            text_vis = self.draw_final_text_overlay(blob_base)
            panels.append(_add_label(_resize(text_vis), "FINAL OUTPUT"))

        if not panels:
            return None

        return np.hstack(panels)

    # ── Disk persistence ──────────────────────────────────────────────────

    def save_all(self, tag: str = "") -> None:
        """
        Save all collected intermediate images to *save_dir*.

        Files are named with a timestamp and optional *tag* prefix.
        """
        if not self.enabled or not self.save_to_disk:
            return

        os.makedirs(self.save_dir, exist_ok=True)
        ts = int(time.time() * 1000)
        prefix = f"{tag}_{ts}" if tag else str(ts)

        pairs: Dict[str, Optional[np.ndarray]] = {
            "raw": self._raw_frame,
            "perspective": self._perspective_frame,
            "gray": self._gray,
            "enhanced": self._enhanced,
            "binary": self._binary,
        }

        for name, img in pairs.items():
            if img is not None:
                path = os.path.join(self.save_dir, f"{prefix}_{name}.jpg")
                cv2.imwrite(path, img, [cv2.IMWRITE_JPEG_QUALITY, 90])

        # Blob overlay
        blob_base = self._perspective_frame if self._perspective_frame is not None else self._raw_frame
        if blob_base is not None and self._accepted_dots:
            blob_vis = self.draw_blob_overlay(blob_base)
            path = os.path.join(self.save_dir, f"{prefix}_blobs.jpg")
            cv2.imwrite(path, blob_vis, [cv2.IMWRITE_JPEG_QUALITY, 90])

        # Composite
        composite = self.build_composite()
        if composite is not None:
            path = os.path.join(self.save_dir, f"{prefix}_composite.jpg")
            cv2.imwrite(path, composite, [cv2.IMWRITE_JPEG_QUALITY, 90])

        logger.debug("Debug images saved to %s with prefix %s", self.save_dir, prefix)

    # ── Reset ─────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all collected frames for the next processing cycle."""
        self._raw_frame = None
        self._perspective_frame = None
        self._perspective_contour = None
        self._gray = None
        self._enhanced = None
        self._binary = None
        self._blob_frame = None
        self._accepted_dots = []
        self._rejected_dots = []
        self._spacing_h = 0.0
        self._spacing_v = 0.0
        self._grid = None
        self._snapped_cells = []
        self._extracted_patches = []
        self._cnn_confidences = []
        self._final_text = ""


# ── Module-level helpers ──────────────────────────────────────────────────────

def _add_label(img: np.ndarray, label: str) -> np.ndarray:
    """Draw a small label in the top-left corner of *img*."""
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (len(label) * 11 + 8, 22), (20, 20, 25), -1)
    cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)
    cv2.putText(img, label, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 220, 255), 1)
    return img
