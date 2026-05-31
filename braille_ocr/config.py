"""
config.py
---------
All tuneable constants for the e-Braille Tales pipeline.
Edit these values to calibrate the tool to your own
Perkins Brailler / flatbed-scanner combination.
"""

# ── Image segmentation ────────────────────────────────────────────────────────

# Pixel along the x-axis (landscape mode, 300 dpi portrait scan) at which the
# first braille cell begins on every line.  Calibrate once per brailler/scanner
# pair by opening the "with character rectangles" JPEG in GIMP and reading the
# x coordinate of the leftmost dot shadow.
X_MIN: int = 282

# Width and height of a single braille cell in pixels at 300 dpi.
CHARACTER_WIDTH: int = 60
CHARACTER_HEIGHT: int = 90

# Maximum number of lines on a landscape 8½ × 11 / A4 Perkins Brailler page.
MAX_LINES_PER_PAGE: int = 19

# Number of braille characters per line (Perkins Brailler, minimal left margin).
CHARS_PER_LINE: int = 41

# ── PEF output ────────────────────────────────────────────────────────────────

# Adjust to match your braille embosser or e-reader specifications.
PEF_COLUMNS_PER_PAGE: int = 40
PEF_LINES_PER_PAGE: int = 25

# ── Deep-learning model ───────────────────────────────────────────────────────

# Filename of the fastai learner exported with learn.export().
MODEL_FILENAME: str = "Model_Perkins_Brailler_acc9997"

# Batch size used when running inference.
INFERENCE_BATCH_SIZE: int = 64

# ── Folder names ──────────────────────────────────────────────────────────────

OCR_RAW_DATA_FOLDER: str = "OCR Raw Data"
OCR_PREDICTIONS_FOLDER: str = "OCR Predictions"
RECTANGLES_FOLDER: str = "Page image files with rectangles"
