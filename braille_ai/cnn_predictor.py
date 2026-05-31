"""
CNN-based Braille character predictor - Fixed version
"""

import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import numpy as np
import os

# CNN Architecture
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

LABELS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

class CNNPredictor:
    def __init__(self, model_path=None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Try multiple possible model locations
        possible_paths = [
            model_path,
            "synthetic_dataset/models/braille_cnn.pth",
            "braille_ai/models/braille_cnn.pth",
            "models/braille_cnn.pth",
            "braille_cnn.pth"
        ]
        
        self.model = None
        
        for path in possible_paths:
            if path and os.path.exists(path):
                try:
                    self.model = BrailleCNN()
                    self.model.load_state_dict(torch.load(path, map_location=self.device))
                    self.model.to(self.device)
                    self.model.eval()
                    print(f"✅ CNN Model loaded from {path}")
                    break
                except Exception as e:
                    print(f"⚠️  Failed to load from {path}: {e}")
        
        if self.model is None:
            print("⚠️  No CNN model found. Using fallback (simple mapping).")
        
        # Image transformation
        self.transform = transforms.Compose([
            transforms.Grayscale(),
            transforms.Resize((64, 64)),
            transforms.ToTensor(),
            transforms.Normalize([0.5], [0.5])
        ])
    
    def predict_cell(self, cell_image):
        """Predict single Braille cell"""
        if self.model is None:
            # Fallback: return placeholder
            return "?", 0.0
        
        try:
            tensor = self.transform(cell_image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                output = self.model(tensor)
                probabilities = torch.softmax(output, dim=1)
                confidence, predicted = torch.max(probabilities, 1)
            
            letter = LABELS[predicted.item()]
            confidence_score = confidence.item() * 100
            return letter, confidence_score
        except Exception as e:
            print(f"Prediction error: {e}")
            return "?", 0.0
    
    def predict_cells_batch(self, cell_images):
        """Predict multiple cells"""
        results = []
        for i, cell in enumerate(cell_images):
            letter, confidence = self.predict_cell(cell)
            results.append({
                'letter': letter,
                'confidence': confidence,
                'is_reliable': confidence > 70
            })
        return results

if __name__ == "__main__":
    predictor = CNNPredictor()
    print(f"Device: {predictor.device}")
    print("✅ CNN Predictor ready")
