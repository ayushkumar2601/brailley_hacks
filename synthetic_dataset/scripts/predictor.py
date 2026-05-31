import torch
import torch.nn as nn

from PIL import Image
from torchvision import transforms

# =========================
# CONFIG
# =========================

MODEL_PATH = "synthetic_dataset/models/braille_cnn.pth"

IMAGE_PATH = "synthetic_dataset/generated/A/A_0.png"

IMAGE_SIZE = 64

CLASSES = [
    "A","B","C","D","E","F","G","H","I","J",
    "K","L","M","N","O","P","Q","R","S","T",
    "U","V","W","X","Y","Z"
]

# =========================
# MODEL
# =========================

class BrailleCNN(nn.Module):
    def __init__(self):
        super(BrailleCNN, self).__init__()

        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),

            nn.Conv2d(32, 64, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )

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

# =========================
# LOAD MODEL
# =========================

device = torch.device("cpu")

model = BrailleCNN().to(device)

model.load_state_dict(
    torch.load(MODEL_PATH, map_location=device)
)

model.eval()

# =========================
# IMAGE TRANSFORM
# =========================

transform = transforms.Compose([
    transforms.Grayscale(),
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
])

# =========================
# LOAD IMAGE
# =========================

image = Image.open(IMAGE_PATH)

tensor = transform(image)

tensor = tensor.unsqueeze(0).to(device)

# =========================
# PREDICTION
# =========================

with torch.no_grad():

    output = model(tensor)

    probabilities = torch.softmax(output, dim=1)

    confidence, predicted = torch.max(probabilities, 1)

predicted_letter = CLASSES[predicted.item()]

confidence_score = confidence.item() * 100

# =========================
# OUTPUT
# =========================

print("\n======================")
print("BRAILLE AI PREDICTION")
print("======================")

print(f"Predicted Letter : {predicted_letter}")

print(f"Confidence Score : {confidence_score:.2f}%")

print("======================\n")
