import os
import torch
import torch.nn as nn
import torch.optim as optim

from torchvision import datasets, transforms
from torch.utils.data import DataLoader

# =========================
# CONFIG
# =========================

DATASET_PATH = "synthetic_dataset/generated"
MODEL_SAVE_PATH = "synthetic_dataset/models/braille_cnn.pth"

BATCH_SIZE = 16
EPOCHS = 5
IMAGE_SIZE = 64
NUM_CLASSES = 26

# =========================
# TRANSFORMS
# =========================

transform = transforms.Compose([
    transforms.Grayscale(),
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
])

# =========================
# DATASET
# =========================

dataset = datasets.ImageFolder(
    DATASET_PATH,
    transform=transform
)

loader = DataLoader(
    dataset,
    batch_size=BATCH_SIZE,
    shuffle=True
)

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
            nn.Linear(128, NUM_CLASSES)
        )

    def forward(self, x):
        x = self.conv(x)
        x = self.fc(x)
        return x

# =========================
# TRAINING SETUP
# =========================

device = torch.device("cpu")

model = BrailleCNN().to(device)

criterion = nn.CrossEntropyLoss()

optimizer = optim.Adam(
    model.parameters(),
    lr=0.001
)

# =========================
# TRAIN LOOP
# =========================

for epoch in range(EPOCHS):

    running_loss = 0.0

    for images, labels in loader:

        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()

        outputs = model(images)

        loss = criterion(outputs, labels)

        loss.backward()

        optimizer.step()

        running_loss += loss.item()

    print(f"Epoch {epoch+1} Loss: {running_loss:.4f}")

# =========================
# SAVE MODEL
# =========================

torch.save(model.state_dict(), MODEL_SAVE_PATH)

print("Model training complete.")
