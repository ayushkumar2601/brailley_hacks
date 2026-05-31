"""
train_dot_model.py
------------------
Trains the multi-label dot prediction CNN.
Uses BCEWithLogitsLoss to predict independent probabilities for each of the 6 braille dots.
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
from torchvision import transforms
from PIL import Image
import glob
import json
import numpy as np
from sklearn.metrics import precision_score, recall_score, brier_score_loss
from braille_ai.dot_cnn import DotPredictorCNN
from synthetic_dataset.scripts.augment_realism import RealismAugmentor

class BrailleDotDataset(Dataset):
    def __init__(self, data_dir, transform=None, augment=False):
        self.data_dir = data_dir
        self.transform = transform
        self.augment = augment
        self.augmentor = RealismAugmentor(p=0.5) if augment else None
        
        self.images_dir = os.path.join(data_dir, "images")
        self.labels_dir = os.path.join(data_dir, "labels")
        self.samples = []
        
        if os.path.exists(self.images_dir) and os.path.exists(self.labels_dir):
            image_files = glob.glob(os.path.join(self.images_dir, "*.jpg"))
            for img_path in image_files:
                base_id = os.path.basename(img_path).replace(".jpg", "")
                label_path = os.path.join(self.labels_dir, f"{base_id}.json")
                if os.path.exists(label_path):
                    try:
                        with open(label_path, "r") as f:
                            label_data = json.load(f)
                        dots = label_data.get("dots", [])
                        if len(dots) == 6:
                            self.samples.append((img_path, torch.FloatTensor(dots)))
                    except Exception as e:
                        print(f"Error loading {label_path}: {e}")
                        
    def __len__(self):
        return len(self.samples)
        
    def __getitem__(self, idx):
        img_path, labels = self.samples[idx]
        image = Image.open(img_path).convert('L')
        
        if self.augmentor:
            img_np = np.array(image)
            img_np = self.augmentor.augment_all(img_np)
            image = Image.fromarray(img_np)
            
        if self.transform:
            image = self.transform(image)
            
        return image, labels

def evaluate_metrics(model, dataloader, device):
    model.eval()
    all_preds = []
    all_labels = []
    all_probs = []
    
    with torch.no_grad():
        for images, labels in dataloader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            probs = torch.sigmoid(outputs)
            preds = (probs > 0.5).float()
            
            all_preds.append(preds.cpu().numpy())
            all_labels.append(labels.cpu().numpy())
            all_probs.append(probs.cpu().numpy())
            
    all_preds = np.vstack(all_preds)
    all_labels = np.vstack(all_labels)
    all_probs = np.vstack(all_probs)
    
    exact_match = np.all(all_preds == all_labels, axis=1).mean()
    per_dot_precision = precision_score(all_labels.flatten(), all_preds.flatten())
    per_dot_recall = recall_score(all_labels.flatten(), all_preds.flatten())
    calibration_error = brier_score_loss(all_labels.flatten(), all_probs.flatten())
    
    return {
        'exact_cell_accuracy': exact_match,
        'per_dot_precision': per_dot_precision,
        'per_dot_recall': per_dot_recall,
        'calibration_brier_score': calibration_error
    }

def generate_report(metrics):
    report_path = "training_report.md"
    with open(report_path, "w") as f:
        f.write("# DotCNN Training Report\n\n")
        f.write("## Evaluation Metrics\n")
        f.write(f"- **Exact Cell Accuracy**: {metrics['exact_cell_accuracy']:.4f}\n")
        f.write(f"- **Per-dot Precision**: {metrics['per_dot_precision']:.4f}\n")
        f.write(f"- **Per-dot Recall**: {metrics['per_dot_recall']:.4f}\n")
        f.write(f"- **Calibration Error (Brier Score)**: {metrics['calibration_brier_score']:.4f}\n")
    print(f"Generated {report_path}")

def train_model(epochs=10, batch_size=32, lr=0.001):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = DotPredictorCNN().to(device)
    
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    transform = transforms.Compose([
        transforms.Resize((64, 64)),
        transforms.ToTensor(),
        transforms.Normalize([0.5], [0.5])
    ])
    
    full_dataset = BrailleDotDataset("datasets/training_data", transform=transform, augment=True)
    if len(full_dataset) == 0:
        print("No training data found. Run convert_dataset.py first.")
        return
        
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])
        
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    print(f"Starting training on {device} for {epochs} epochs with {train_size} train / {val_size} val samples...")
    
    best_acc = 0.0
    os.makedirs("braille_ai/models", exist_ok=True)
    
    final_metrics = {}
    
    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
            
        avg_loss = running_loss / max(1, len(train_loader))
        
        metrics = evaluate_metrics(model, val_loader, device)
        exact_acc = metrics['exact_cell_accuracy']
        
        print(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f} - Val Exact Acc: {exact_acc:.4f}")
        
        # Save latest checkpoint
        torch.save(model.state_dict(), "braille_ai/models/braille_dot_cnn_latest.pth")
        
        # Save best checkpoint
        if exact_acc >= best_acc:
            best_acc = exact_acc
            final_metrics = metrics
            torch.save(model.state_dict(), "braille_ai/models/braille_dot_cnn_best.pth")
            
    print("Training completed. Generating report...")
    if not final_metrics:
        final_metrics = evaluate_metrics(model, val_loader, device)
    generate_report(final_metrics)

if __name__ == "__main__":
    train_model(epochs=1)
