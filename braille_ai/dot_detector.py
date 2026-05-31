from PIL import Image, ImageDraw
import numpy as np
import os

INPUT_IMAGE = "test_braille_hello.png"

img = Image.open(INPUT_IMAGE).convert("L")

# Resize
img = img.resize((800, 400))

arr = np.array(img)

# Threshold
binary = arr < 160

# Dot storage
dots = []

visited = np.zeros(binary.shape, dtype=bool)

HEIGHT, WIDTH = binary.shape

# DFS for connected components
def dfs(y, x, points):

    stack = [(y, x)]

    while stack:

        cy, cx = stack.pop()

        if cy < 0 or cx < 0 or cy >= HEIGHT or cx >= WIDTH:
            continue

        if visited[cy][cx]:
            continue

        if not binary[cy][cx]:
            continue

        visited[cy][cx] = True

        points.append((cx, cy))

        for ny in range(cy - 1, cy + 2):
            for nx in range(cx - 1, cx + 2):
                stack.append((ny, nx))

# Find connected dark regions
for y in range(HEIGHT):
    for x in range(WIDTH):

        if binary[y][x] and not visited[y][x]:

            component = []

            dfs(y, x, component)

            # Ignore tiny noise
            if len(component) > 20:

                xs = [p[0] for p in component]
                ys = [p[1] for p in component]

                cx = int(sum(xs) / len(xs))
                cy = int(sum(ys) / len(ys))

                dots.append((cx, cy))

# Draw results
debug = img.convert("RGB")

draw = ImageDraw.Draw(debug)

for x, y in dots:

    r = 10

    draw.ellipse(
        (x-r, y-r, x+r, y+r),
        outline="red",
        width=3
    )

# Save debug image
os.makedirs("braille_ai/temp", exist_ok=True)

debug.save("braille_ai/temp/detected_dots.png")

print("======================")
print("DOT DETECTION COMPLETE")
print("======================")
print(f"Total Dots: {len(dots)}")

for d in dots[:20]:
    print(d)
