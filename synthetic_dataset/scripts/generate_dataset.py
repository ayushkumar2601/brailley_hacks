from PIL import Image, ImageDraw, ImageFilter
import random
import os

OUTPUT_DIR = "synthetic_dataset/generated"

BRAILLE_MAP = {
    "A": [1],
    "B": [1,2],
    "C": [1,4],
    "D": [1,4,5],
    "E": [1,5],
    "F": [1,2,4],
    "G": [1,2,4,5],
    "H": [1,2,5],
    "I": [2,4],
    "J": [2,4,5],

    "K": [1,3],
    "L": [1,2,3],
    "M": [1,3,4],
    "N": [1,3,4,5],
    "O": [1,3,5],
    "P": [1,2,3,4],
    "Q": [1,2,3,4,5],
    "R": [1,2,3,5],
    "S": [2,3,4],
    "T": [2,3,4,5],

    "U": [1,3,6],
    "V": [1,2,3,6],
    "W": [2,4,5,6],
    "X": [1,3,4,6],
    "Y": [1,3,4,5,6],
    "Z": [1,3,5,6]
}

DOT_POSITIONS = {
    1: (20, 20),
    2: (20, 50),
    3: (20, 80),
    4: (60, 20),
    5: (60, 50),
    6: (60, 80),
}

os.makedirs(OUTPUT_DIR, exist_ok=True)

for char, dots in BRAILLE_MAP.items():

    class_dir = os.path.join(OUTPUT_DIR, char)
    os.makedirs(class_dir, exist_ok=True)

    for i in range(60):

        img = Image.new("L", (100, 120), color=255)
        draw = ImageDraw.Draw(img)

        for dot in dots:

            x, y = DOT_POSITIONS[dot]

            x += random.randint(-4, 4)
            y += random.randint(-4, 4)

            radius = random.randint(8, 13)

            draw.ellipse(
                (
                    x-radius,
                    y-radius,
                    x+radius,
                    y+radius
                ),
                fill=0
            )

        angle = random.uniform(-8, 8)
        img = img.rotate(angle)

        if random.random() > 0.5:
            img = img.filter(
                ImageFilter.GaussianBlur(
                    radius=random.uniform(0.3, 1.2)
                )
            )

        output_path = os.path.join(
            class_dir,
            f"{char}_{i}.png"
        )

        img.save(output_path)

print("Dataset generation complete.")
