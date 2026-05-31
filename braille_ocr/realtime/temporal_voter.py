"""
temporal_voter.py
-----------------
Multi-frame temporal voting to stabilize OCR outputs over time and prevent flickering.
"""

from typing import List, Dict, Optional
from collections import deque
from braille_ocr.realtime.dot_snapper import SnappedCell
from braille_ocr.realtime.binary_encoder import binary_to_char

class TemporalVoter:
    def __init__(self, history_size: int = 5, min_votes: int = 3):
        self.history_size = history_size
        self.min_votes = min_votes
        # List of frames, where each frame is a list of binary cell tuples: tuple(dot1..dot6)
        self.frame_history: deque[List[tuple]] = deque(maxlen=history_size)
        
    def vote(self, current_cells: List[SnappedCell]) -> List[SnappedCell]:
        """
        Applies majority voting across the frame history to stabilize the binary cells.
        Returns a new list of stabilized SnappedCells.
        """
        # Convert current cells to tuple format for easy hashing
        current_binary = [tuple(c.dots) for c in current_cells]
        self.frame_history.append(current_binary)
        
        if not current_cells:
            return []
            
        stabilized_cells = []
        for i, cell in enumerate(current_cells):
            # Count occurrences of cell patterns at this position across history
            pattern_counts: Dict[tuple, int] = {}
            for frame in self.frame_history:
                if i < len(frame):
                    pattern = frame[i]
                    pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
                    
            # Find the most common pattern
            if pattern_counts:
                best_pattern = max(pattern_counts.items(), key=lambda x: x[1])
                # If the best pattern has enough votes, use it, otherwise keep current
                if best_pattern[1] >= self.min_votes:
                    stable_dots = list(best_pattern[0])
                else:
                    stable_dots = cell.dots
            else:
                stable_dots = cell.dots
                
            stabilized_cells.append(SnappedCell(
                cell_id=cell.cell_id,
                dots=stable_dots,
                confidence=cell.confidence,
                snapped_coords=cell.snapped_coords
            ))
            
        return stabilized_cells
        
    def reset(self):
        self.frame_history.clear()
