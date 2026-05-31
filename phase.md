# BrailleScan OCR Recovery Roadmap

Your current goal should NOT be:

> “make AI smarter”

Your goal should be:

> “make geometry deterministic”

So instead of randomly improving things, structure the recovery into 3 focused engineering phases.

---

# Phase 1 — Vision Stabilization Layer

## Goal:

Make the system reliably SEE Braille structure before decoding anything.

This phase alone can improve accuracy more than the CNN.

---

## Main Problems Being Solved

* Perspective distortion
* Uneven lighting
* Fake contours
* Noise blobs
* Camera instability

---

# Phase 1 Tasks

## 1. Perspective Correction

### Objective

Flatten the paper/page before OCR.

### Implement

* Edge detection
* Largest quadrilateral detection
* Homography transform

### Tools

* `cv2.Canny`
* `cv2.findContours`
* `cv2.getPerspectiveTransform`
* `cv2.warpPerspective`

### Deliverable

A normalized top-down Braille page image.

---

## 2. Illumination Normalization

### Objective

Remove shadows and improve contrast consistency.

### Implement

* CLAHE
* Gaussian blur
* Adaptive thresholding

### Deliverable

Consistent grayscale preprocessing pipeline.

---

## 3. Replace Contour Detector

### Objective

Detect circular Braille dots instead of random blobs.

### Replace

```text
Contour-based dot extraction
```

with:

```text
SimpleBlobDetector
```

### Filter By

* Area
* Circularity
* Convexity
* Inertia

### Deliverable

Reliable dot candidate extraction.

---

## 4. Build Dot Visualization Debugger

### Objective

Visually inspect detections.

### Add

Overlay:

* detected dots
* rejected dots
* confidence coloring
* spacing lines

### Deliverable

A debug mode showing WHY OCR fails.

---

# Phase 1 Success Criteria

You are successful when:

* detected dots align visually with real dots
* very few false positives appear
* page flattening works consistently
* preprocessing output looks stable frame-to-frame

---

# Phase 2 — Spatial Reconstruction Engine

## Goal:

Convert noisy detected dots into a mathematically stable Braille lattice.

This is the REAL OCR engine.

---

## Main Problems Being Solved

* Incorrect cell grouping
* Row drift
* Column drift
* Misaligned spacing
* Random character generation

---

# Phase 2 Tasks

## 1. Braille Grid Estimation

### Objective

Infer invisible Braille structure.

### Implement

Estimate:

* average horizontal spacing
* average vertical spacing
* line spacing
* cell boundaries

### Techniques

* clustering
* spacing histograms
* RANSAC
* nearest-neighbor analysis

### Deliverable

A reconstructed global Braille grid.

---

## 2. Dot Snapping System

### Objective

Snap noisy detections to nearest legal Braille positions.

### Example

Instead of:

```text
(102, 97)
```

snap to:

```text
Cell 4 → Dot 1
```

### Deliverable

Deterministic cell mapping.

---

## 3. Binary Cell Representation

### Objective

Represent cells as:

```python
[1,0,1,0,0,1]
```

instead of direct character labels.

### Why

Much easier to debug.

### Deliverable

Stable 6-bit Braille encoding engine.

---

## 4. Multi-Frame Voting

### Objective

Prevent flickering OCR.

### Implement

* rolling buffer
* confidence averaging
* majority vote
* temporal smoothing

### Deliverable

Stable OCR across webcam motion.

---

## 5. Disable Groq Completely

### Objective

Debug REAL OCR quality.

### Why

LLMs hide geometry problems.

### Deliverable

Pure raw OCR outputs.

---

# Phase 2 Success Criteria

You are successful when:

* identical frames produce identical text
* small camera movement does not change words
* characters remain stable across frames
* raw OCR becomes readable WITHOUT AI correction

---

# Phase 3 — AI & Production Intelligence

## Goal:

Improve robustness, semantic accuracy, and production readiness.

Only AFTER geometry is stable.

---

## Main Problems Being Solved

* Real-world variance
* Low-quality handwriting
* Edge cases
* Semantic cleanup
* Production scaling

---

# Phase 3 Tasks

## 1. Real Dataset Collection

### Since physical Braille is hard:

You can use:

* online Braille photographs
* scanned embossed pages
* educational PDFs
* synthetic-to-real augmentation

---

## 2. Dataset Augmentation Pipeline

### Add:

* blur
* perspective warp
* brightness variation
* motion blur
* JPEG artifacts
* paper textures

### Deliverable

Realistic training data.

---

## 3. Redesign CNN

### Current Problem

Whole-character classification is fragile.

### Replace With

Multi-label dot prediction:

```python
[1,0,1,1,0,0]
```

### Recommended

* BCEWithLogitsLoss
* lightweight CNN
* MobileNet backbone optional

---

## 4. Controlled LLM Correction

### Groq should:

* repair spacing
* repair probable words
* NEVER hallucinate

### Add

Confidence gating:

```python
if confidence < threshold:
    skip_llm()
```

---

## 5. Production Architecture Improvements

### Add

* async processing
* websocket streaming
* Docker
* Redis session manager
* authentication
* rate limiting

---

# Phase 3 Success Criteria

You are successful when:

* OCR works on unseen online images
* hand-drawn Braille partially works
* webcam scanning becomes reliable
* semantic corrections become minimal
* system can scale beyond single-user local mode

---

# Recommended Timeline

| Phase   | Focus                      | Difficulty  | Expected Gain |
| ------- | -------------------------- | ----------- | ------------- |
| Phase 1 | Vision stabilization       | Medium      | HUGE          |
| Phase 2 | Spatial reconstruction     | Hard        | MASSIVE       |
| Phase 3 | AI refinement & production | Medium-Hard | Incremental   |

---

# Most Important Strategic Advice

Do NOT touch:

* frontend
* Flask APIs
* UI polish
* Groq prompting
* fancy models

until:

```text
dot geometry becomes mathematically stable
```

That is the foundation of the entire system.

Right now your OCR errors are probably:

```text
80% geometry
15% preprocessing
5% AI/model
```

not the other way around.
