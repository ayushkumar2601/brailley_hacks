"""
evaluator.py
------------
Evaluation utilities for Braille OCR accuracy, CNN performance, and Dataset Benchmarking.
Generates metrics for Character Accuracy, Cell Accuracy, and Confusion Analysis.
"""

import os
import json
import numpy as np

def calculate_accuracy(expected: str, predicted: str) -> dict:
    """Calculate character accuracy using Levenshtein distance."""
    from braille_ai.ocr_corrector import levenshtein
    if not expected:
        return {"char_accuracy": 0.0, "edit_distance": len(predicted)}
        
    ed = levenshtein(expected, predicted)
    acc = max(0.0, 1.0 - (ed / len(expected)))
    
    return {
        "char_accuracy": acc,
        "edit_distance": ed,
        "expected": expected,
        "predicted": predicted
    }

def benchmark_datasets(datasets: dict):
    """
    Benchmarks multiple datasets (e.g. synthetic, augmented, real).
    datasets: dict of { "dataset_name": [(expected_text, predicted_text), ...] }
    """
    report = {}
    for name, samples in datasets.items():
        total_acc = 0.0
        for exp, pred in samples:
            res = calculate_accuracy(exp, pred)
            total_acc += res["char_accuracy"]
            
        avg_acc = total_acc / max(len(samples), 1)
        report[name] = {
            "average_accuracy": avg_acc,
            "samples_evaluated": len(samples)
        }
    return report

def generate_cnn_report(predictions: list, ground_truths: list):
    """
    Generate CNN Evaluation Reports: Per-dot accuracy, precision, recall.
    Inputs are lists of 6-bit arrays: [1,0,1,0,0,0]
    """
    if len(predictions) != len(ground_truths) or not predictions:
        return {}
        
    predictions = np.array(predictions)
    ground_truths = np.array(ground_truths)
    
    # Calculate per-dot metrics
    per_dot_accuracy = (predictions == ground_truths).mean(axis=0)
    
    # True positives, false positives, false negatives
    tp = ((predictions == 1) & (ground_truths == 1)).sum(axis=0)
    fp = ((predictions == 1) & (ground_truths == 0)).sum(axis=0)
    fn = ((predictions == 0) & (ground_truths == 1)).sum(axis=0)
    
    precision = np.divide(tp, tp + fp, out=np.zeros_like(tp, dtype=float), where=(tp + fp) != 0)
    recall = np.divide(tp, tp + fn, out=np.zeros_like(tp, dtype=float), where=(tp + fn) != 0)
    
    # Cell level accuracy (all 6 dots correct)
    exact_matches = np.all(predictions == ground_truths, axis=1)
    cell_accuracy = exact_matches.mean()
    
    return {
        "cell_accuracy": float(cell_accuracy),
        "per_dot_accuracy": per_dot_accuracy.tolist(),
        "per_dot_precision": precision.tolist(),
        "per_dot_recall": recall.tolist()
    }

if __name__ == "__main__":
    # Test evaluation
    print("Testing CNN Evaluator...")
    preds = [[1,0,1,0,0,0], [1,1,0,0,0,0], [1,0,0,0,0,0]]
    truths = [[1,0,1,0,0,0], [1,0,0,0,0,0], [1,0,0,0,0,0]]
    
    report = generate_cnn_report(preds, truths)
    print(json.dumps(report, indent=2))
