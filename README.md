# BrailleScan — AI Braille Reader

A real-time Braille OCR web app that reads Braille from a camera or uploaded image, converts it to English text, and speaks it aloud.

## Features

- **Live camera scanning** — uses browser `getUserMedia` (works on macOS Safari/Chrome without permission issues)
- **Image upload** — drag-and-drop or file picker for processing photos
- **CNN model** — trained on 1,560 synthetic Braille images (26 letters × 60 variants), loss: 0.0001
- **Groq AI correction** — uses `llama-3.1-8b-instant` to fix OCR errors
- **Text-to-Speech** — pyttsx3 with voice selection, speed, and volume controls
- **Modern UI** — dark/light theme, confidence meter, session history, mobile responsive

## Quick Start

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd Braille-OCR-e-Braille-Tales

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 5. Run the app
python3 app.py

# 6. Open in browser
open http://localhost:5050
```

## Environment Variables

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
```

Get a free Groq API key at [console.groq.com](https://console.groq.com).

## Usage

### Live Camera
1. Click **Allow Camera** — browser will ask for permission
2. Hold a Braille page in front of the camera
3. Text is detected, translated, and spoken automatically

### Upload Image
1. Click **Upload Image** or drag-and-drop a photo onto the camera area
2. The pipeline processes the image and speaks the result

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| `Space` | Pause / Resume scanning |
| `R` | Repeat last text |
| `H` | Read full history |
| `C` | Copy last text |
| `U` | Open upload dialog |

## Architecture

```
app.py (Flask, port 5050)
├── braille_ocr/realtime/
│   ├── camera_loop.py      — frame capture (browser primary, OpenCV fallback)
│   ├── braille_detector.py — pure-CV dot detection + braille decode
│   ├── frame_analyzer.py   — image quality analysis
│   ├── session.py          — session state & history
│   └── tts_engine.py       — thread-safe TTS (pyttsx3 + macOS say fallback)
├── braille_ai/
│   ├── cnn_predictor.py    — CNN model inference (PyTorch)
│   └── ocr_corrector.py    — Groq AI text correction
└── braille_ocr/core/       — batch OCR pipeline (fastai, for scanned pages)
```

## Model

The CNN model (`synthetic_dataset/models/braille_cnn.pth`) is a lightweight PyTorch CNN:
- Input: 64×64 grayscale Braille cell images
- Architecture: 2× Conv+ReLU+MaxPool → 2× FC
- Output: 26 classes (A–Z)
- Training: 1,560 synthetic images, final loss ~0.0001

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main UI |
| GET | `/api/status` | Scanner status + stats |
| GET | `/api/history` | Last 30 recognised segments |
| GET | `/api/voices` | Available TTS voices |
| POST | `/api/process_frame` | Process browser webcam frame |
| POST | `/api/upload` | Process uploaded image |
| POST | `/api/speak` | Speak text via TTS |
| POST | `/api/tts_settings` | Update rate/volume/voice |
| GET | `/api/demo` | Run demo on test image |
| GET | `/api/health` | Health check |

## Requirements

- Python 3.9+
- macOS / Linux / Windows
- Webcam (optional — upload works without camera)
- Groq API key (optional — OCR works without it)
