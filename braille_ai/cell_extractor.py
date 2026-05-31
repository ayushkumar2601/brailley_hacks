from PIL import Image, ImageDraw
import numpy as np
import os

INPUT_IMAGE = "test_braille_hello.png"
OUTPUT_FOLDER = "braille_ai/cells"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Load image
img = Image.open(INPUT_IMAGE).convert("L")

# Resize for consistency
img = img.resize((800, 400))

# Convert to numpy
arr = np.array(img)

# Threshold
binary = arr < 180

# Find dark pixels
ys, xs = np.where(binary)

if len(xs) == 0:
    print("No Braille dots detected.")
    exit()

# Bounding box
x_min = xs.min()
x_max = xs.max()
y_min = ys.min()
y_max = ys.max()

# Crop useful region
cropped = img.crop((x_min, y_min, x_max, y_max))

# Approximate Braille grid
CELL_WIDTH = 60
CELL_HEIGHT = 100

cropped_width, cropped_height = cropped.size

draw = ImageDraw.Draw(cropped)

cell_count = 0

for y in range(0, cropped_height, CELL_HEIGHT):
    for x in range(0, cropped_width, CELL_WIDTH):

        x2 = min(x + CELL_WIDTH, cropped_width)
        y2 = min(y + CELL_HEIGHT, cropped_height)

        cell = cropped.crop((x, y, x2, y2))

        # Save cell
        cell_path = os.path.join(
            OUTPUT_FOLDER,
            f"cell_{cell_count}.png"
        )

        cell.save(cell_path)

        # Draw rectangle
        draw.rectangle(
            [x, y, x2, y2],
            outline="red",
            width=2
        )

        cell_count += 1

# Save debug image
cropped.save("braille_ai/temp/debug_cells.png")

print("======================")
print("CELL EXTRACTION DONE")
print("======================")
print(f"Total Cells: {cell_count}")
print("Saved in braille_ai/cells/")
