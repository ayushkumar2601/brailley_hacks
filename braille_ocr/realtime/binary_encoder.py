"""
binary_encoder.py
-----------------
Translates 6-bit binary Braille cell representation into ASCII/Grade 1 Braille.
"""

from typing import List
from braille_ocr.realtime.dot_snapper import SnappedCell

# Standard Grade-1 Braille map
# Bit mask: bit0=dot1, bit1=dot2, bit2=dot3, bit3=dot4, bit4=dot5, bit5=dot6
_BRAILLE_TO_CHAR = {
    0b000001: "a",  0b000011: "b",  0b001001: "c",  0b011001: "d",  0b010001: "e",
    0b001011: "f",  0b011011: "g",  0b010011: "h",  0b001010: "i",  0b011010: "j",
    0b000101: "k",  0b000111: "l",  0b001101: "m",  0b011101: "n",  0b010101: "o",
    0b001111: "p",  0b011111: "q",  0b010111: "r",  0b001110: "s",  0b011110: "t",
    0b100101: "u",  0b100111: "v",  0b111010: "w",  0b101101: "x",  0b111101: "y",
    0b110101: "z",  0b000000: " ",
}

def binary_to_char(binary_dots: List[int]) -> str:
    """
    Converts a 6-element binary array [dot1..dot6] to a character.
    """
    if len(binary_dots) != 6:
        return "?"
        
    mask = 0
    for i in range(6):
        if binary_dots[i]:
            mask |= (1 << i)
            
    return _BRAILLE_TO_CHAR.get(mask, "?")

def encode_cells(snapped_cells: List[SnappedCell]) -> str:
    """
    Translates a list of SnappedCells into a text string.
    """
    text = ""
    for cell in snapped_cells:
        char = binary_to_char(cell.dots)
        text += char
    return text
