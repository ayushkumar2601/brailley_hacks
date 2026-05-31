"""
generate_labels.py
------------------
Converts Braille unicode/text into binary dot arrays.
Validates legal Braille structures.
Generates the label JSON required for training.
"""

from typing import List, Dict, Optional
import json

# Reverse lookup from char to dots based on standard Braille Grade-1
CHAR_TO_DOTS = {
    'a': [1,0,0,0,0,0], 'b': [1,1,0,0,0,0], 'c': [1,0,0,1,0,0],
    'd': [1,0,0,1,1,0], 'e': [1,0,0,0,1,0], 'f': [1,1,0,1,0,0],
    'g': [1,1,0,1,1,0], 'h': [1,1,0,0,1,0], 'i': [0,1,0,1,0,0],
    'j': [0,1,0,1,1,0], 'k': [1,0,1,0,0,0], 'l': [1,1,1,0,0,0],
    'm': [1,0,1,1,0,0], 'n': [1,0,1,1,1,0], 'o': [1,0,1,0,1,0],
    'p': [1,1,1,1,0,0], 'q': [1,1,1,1,1,0], 'r': [1,1,1,0,1,0],
    's': [0,1,1,1,0,0], 't': [0,1,1,1,1,0], 'u': [1,0,1,0,0,1],
    'v': [1,1,1,0,0,1], 'w': [0,1,0,1,1,1], 'x': [1,0,1,1,0,1],
    'y': [1,0,1,1,1,1], 'z': [1,0,1,0,1,1], ' ': [0,0,0,0,0,0]
}

def unicode_to_dots(unicode_char: str) -> List[int]:
    """
    Converts a Braille unicode character (U+2800 to U+28FF) to a 6-bit array.
    """
    # Braille unicode starts at 0x2800. 
    # Bits are mapped: dot 1=0x1, dot 2=0x2, dot 3=0x4, dot 4=0x8, dot 5=0x10, dot 6=0x20
    if len(unicode_char) == 1 and 0x2800 <= ord(unicode_char) <= 0x283F:
        val = ord(unicode_char) - 0x2800
        return [
            1 if (val & 0x1) else 0,
            1 if (val & 0x2) else 0,
            1 if (val & 0x4) else 0,
            1 if (val & 0x8) else 0,
            1 if (val & 0x10) else 0,
            1 if (val & 0x20) else 0
        ]
    return [0]*6

def char_to_dots(char: str) -> List[int]:
    """Converts a single ASCII character to 6-dot array using Grade-1."""
    return CHAR_TO_DOTS.get(char.lower(), [0,0,0,0,0,0])

def generate_label(char: str, cell_position: List[int], source: str = "dsbi", augmented: bool = False, conf: float = 1.0) -> dict:
    """
    Generates a standardized JSON label dictionary.
    """
    dots = char_to_dots(char) if char.lower() in CHAR_TO_DOTS else unicode_to_dots(char)
    
    return {
        "dots": dots,
        "char": char,
        "confidence": conf,
        "source": source,
        "augmented": augmented,
        "cell_position": cell_position
    }

def validate_dots(dots: List[int]) -> bool:
    """Validates that a dot array is legal (length 6, containing only 0s and 1s)."""
    if len(dots) != 6: return False
    return all(d in (0, 1) for d in dots)

if __name__ == "__main__":
    print(generate_label('k', [4, 7]))
    print(generate_label('\u2813', [0, 0])) # Dots 1, 2, 5 -> [1,1,0,0,1,0]
