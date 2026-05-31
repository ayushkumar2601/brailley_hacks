from PIL import Image

# =====================================
# BRAILLE MAP
# =====================================

BRAILLE_MAP = {
    (1,): "A",
    (1, 2): "B",
    (1, 4): "C",
    (1, 4, 5): "D",
    (1, 5): "E",
    (1, 2, 4): "F",
    (1, 2, 4, 5): "G",
    (1, 2, 5): "H",
    (2, 4): "I",
    (2, 4, 5): "J",

    (1, 3): "K",
    (1, 2, 3): "L",
    (1, 3, 4): "M",
    (1, 3, 4, 5): "N",
    (1, 3, 5): "O",
    (1, 2, 3, 4): "P",
    (1, 2, 3, 4, 5): "Q",
    (1, 2, 3, 5): "R",
    (2, 3, 4): "S",
    (2, 3, 4, 5): "T",

    (1, 3, 6): "U",
    (1, 2, 3, 6): "V",
    (2, 4, 5, 6): "W",
    (1, 3, 4, 6): "X",
    (1, 3, 4, 5, 6): "Y",
    (1, 3, 5, 6): "Z"
}

# =====================================
# LOAD IMAGE
# =====================================

img = Image.open("braille_ai/temp/detected_dots.png").convert("RGB")

# =====================================
# DETECTED DOTS
# =====================================

dots = [
    (32, 81),
    (32, 201),
    (99, 201),

    (192, 81),

    (259, 201),

    (352, 81),
    (352, 201),
    (352, 321),

    (512, 81),
    (512, 201),
    (512, 321),

    (672, 81),
    (672, 321),

    (739, 201)
]

# =====================================
# SORT DOTS
# =====================================

dots = sorted(dots, key=lambda p: p[0])

# =====================================
# GROUP INTO CELLS
# =====================================

cells = []

current = [dots[0]]

for i in range(1, len(dots)):

    prev_x = dots[i - 1][0]
    curr_x = dots[i][0]

    # new cell gap
    if curr_x - prev_x > 90:
        cells.append(current)
        current = []

    current.append(dots[i])

cells.append(current)

# =====================================
# FIXED GLOBAL COORDINATES
# =====================================
# These values come from analyzing the full image:
# - Minimum Y across ALL dots ~ 60 (top row)
# - Maximum Y across ALL dots ~ 340 (bottom row)
# - Row boundaries calculated from the FULL Braille document

GLOBAL_MIN_Y = 60
GLOBAL_MAX_Y = 340

# Row thresholds (evenly spaced between min and max)
# Row 1: 0-33% (60-153) → positions 1 & 4
# Row 2: 33-66% (153-247) → positions 2 & 5  
# Row 3: 66-100% (247-340) → positions 3 & 6

ROW1_THRESHOLD = GLOBAL_MIN_Y + (GLOBAL_MAX_Y - GLOBAL_MIN_Y) * 0.33  # ~153
ROW2_THRESHOLD = GLOBAL_MIN_Y + (GLOBAL_MAX_Y - GLOBAL_MIN_Y) * 0.66  # ~247

# =====================================
# PROCESS CELLS
# =====================================

decoded_text = ""

print("\n====================")
print("DECODED PATTERNS")
print("====================\n")
print(f"[SYSTEM] Using fixed global rows: Y < {ROW1_THRESHOLD:.0f} = row1, Y < {ROW2_THRESHOLD:.0f} = row2, else row3\n")

for idx, cell in enumerate(cells):
    
    xs = [p[0] for p in cell]
    ys = [p[1] for p in cell]

    min_x = min(xs)
    max_x = max(xs)

    width = max_x - min_x

    # Column split (still dynamic per cell - this is correct)
    col_split = min_x + (width / 2)

    pattern = []

    for x, y in cell:

        # LEFT COLUMN
        if x <= col_split:

            if y < ROW1_THRESHOLD:
                pattern.append(1)
            elif y < ROW2_THRESHOLD:
                pattern.append(2)
            else:
                pattern.append(3)

        # RIGHT COLUMN
        else:

            if y < ROW1_THRESHOLD:
                pattern.append(4)
            elif y < ROW2_THRESHOLD:
                pattern.append(5)
            else:
                pattern.append(6)

    # remove duplicates (if any dot sits exactly on boundary)
    pattern = tuple(sorted(list(set(pattern))))

    letter = BRAILLE_MAP.get(pattern, "?")

    print(f"Cell {idx+1}: {pattern} → {letter}")

    decoded_text += letter

# =====================================
# FINAL OUTPUT
# =====================================

print("\n====================")
print("FINAL TEXT")
print("====================")
print(decoded_text)
print("====================")