"""
dot_cnn.py
----------
Multi-label CNN architecture for predicting the presence of the 6 braille dots in a cell.
Outputs 6 logits suitable for BCEWithLogitsLoss.
"""

import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import numpy as np
import os

class DotPredictorCNN(nn.Module):
    def __init__(self):
        super(DotPredictorCNN, self).__init__()
        # Lightweight MobileNet-style architecture or simple CNN for CPU efficiency
        self.features = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2), # 64x64 -> 32x32
            
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2), # 32x32 -> 16x16
            
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2), # 16x16 -> 8x8
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 8 * 8, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(128, 6) # 6 output neurons for 6 dots (multi-label)
        )
        
    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

class DotCNNPredictor:
    def __init__(self, model_path=None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        possible_paths = [
            model_path,
            "synthetic_dataset/models/braille_dot_cnn.pth",
            "braille_ai/models/braille_dot_cnn.pth",
            "models/braille_dot_cnn.pth",
            "braille_dot_cnn.pth"
        ]
        
        self.model = None
        for path in possible_paths:
            if path and os.path.exists(path):
                try:
                    self.model = DotPredictorCNN()
                    self.model.load_state_dict(torch.load(path, map_location=self.device))
                    self.model.to(self.device)
                    self.model.eval()
                    print(f"✅ Dot CNN Model loaded from {path}")
                    break
                except Exception as e:
                    print(f"⚠️ Failed to load from {path}: {e}")
                    
        self.transform = transforms.Compose([
            transforms.Grayscale(),
            transforms.Resize((64, 64)),
            transforms.ToTensor(),
            transforms.Normalize([0.5], [0.5])
        ])

    def predict_cell(self, cell_image):
        """
        Predict dots for a single cell image.
        Returns (binary_dots, confidence)
        """
        if self.model is None:
            return [0,0,0,0,0,0], 0.0
            
        try:
            tensor = self.transform(cell_image).unsqueeze(0).to(self.device)
            with torch.no_grad():
                logits = self.model(tensor)
                probs = torch.sigmoid(logits).squeeze(0) # convert logits to probabilities
                
            # Binarize with threshold 0.5
            dots = (probs > 0.5).int().tolist()
            
            # Confidence is the average confidence of the predictions
            # Confidence of 1 is 100%, 0 is 0%. 
            # If prob is 0.9, conf is 0.9. If prob is 0.1, conf is 0.9 (since we predicted 0).
            conf_scores = torch.where(probs > 0.5, probs, 1.0 - probs)
            confidence = conf_scores.mean().item()
            
            return dots, confidence
        except Exception as e:
            print(f"Prediction error: {e}")
            return [0,0,0,0,0,0], 0.0
            
    def predict_cells_batch(self, cell_images):
        """Predict multiple cells via batched tensor processing for efficiency."""
        if self.model is None or not cell_images:
            return []
            
        try:
            tensors = torch.stack([self.transform(img) for img in cell_images]).to(self.device)
            with torch.no_grad():
                logits = self.model(tensors)
                probs = torch.sigmoid(logits)
                
            dots_batch = (probs > 0.5).int().tolist()
            conf_scores_batch = torch.where(probs > 0.5, probs, 1.0 - probs).mean(dim=1).tolist()
            
            results = []
            for i in range(len(cell_images)):
                results.append({
                    "dots": dots_batch[i],
                    "confidence": conf_scores_batch[i]
                })
            return results
        except Exception as e:
            print(f"Batch prediction error: {e}")
            return [{"dots": [0]*6, "confidence": 0.0} for _ in cell_images]
