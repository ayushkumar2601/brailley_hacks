import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import os

# ======================
# LABELS
# ======================

LABELS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

# ======================
# MODEL
# ======================

class BrailleCNN(nn.Module):
    def __init__(self):
        super(BrailleCNN, self).__init__()

        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),

            nn.Conv2d(32, 64, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2)
        )

        # IMPORTANT:
        # This EXACTLY matches train_model.py

        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 16 * 16, 128),
            nn.ReLU(),
            nn.Linear(128, 26)
        )

    def forward(self, x):
        x = self.conv(x)
        x = self.fc(x)
        return x

# ======================
# LOAD MODEL
# ======================

MODEL_PATH = "synthetic_dataset/models/braille_cnn.pth"

model = BrailleCNN()

model.load_state_dict(
    torch.load(MODEL_PATH, map_location="cpu")
)

model.eval()

# ======================
# IMAGE TRANSFORM
# ======================

transform = transforms.Compose([
    transforms.Grayscale(),
    transforms.Resize((64, 64)),
    transforms.ToTensor()
])

# ======================
# CELL DIRECTORY
# ======================

CELL_DIR = "braille_ai/cells"

files = sorted(os.listdir(CELL_DIR))

sentence = ""

print("\n======================")
print("BRAILLE CELL PREDICTION")
print("======================\n")

for file in files:

    if not file.endswith(".png"):
        continue

    path = os.path.join(CELL_DIR, file)

    img = Image.open(path)

    tensor = transform(img).unsqueeze(0)

    with torch.no_grad():

        output = model(tensor)

        probabilities = torch.softmax(output, dim=1)

        confidence, predicted = torch.max(
            probabilities,
            1
        )

    letter = LABELS[predicted.item()]
    conf = confidence.item() * 100

    if conf < 60:
        continue

    sentence += letter

    print(f"{file} → {letter} ({conf:.2f}%)")

print("\n======================")
print("FINAL TEXT")
print("======================")
print(sentence)
print("======================")
