"""
app.py
------
Flask web server for the Braille Accessibility Scanner.

Endpoints
---------
GET  /                      → main UI
GET  /api/frame             → latest annotated camera frame (base64 JPEG)
GET  /api/status            → JSON status (quality, dot_count, last_text, stats)
GET  /api/history           → JSON list of last 30 recognised text segments
GET  /api/voices            → list available TTS voices
POST /api/speak             → speak arbitrary text via TTS  { "text": "..." }
POST /api/speak_history     → re-read the full session history
POST /api/pause             → pause / resume scanning       { "paused": true }
POST /api/clear             → clear session history
POST /api/tts_settings      → update TTS rate/volume/voice  { "rate": 175, "volume": 1.0, "voice_id": "..." }
POST /api/process_frame     → process a browser webcam frame (base64 JPEG)
POST /api/upload            → process an uploaded image file
GET  /api/demo              → run demo on bundled test image
POST /api/camera/restart    → restart OpenCV camera
GET  /api/health            → simple health check
"""

import base64
import os
import threading
import time

# OpenCV cannot show the macOS auth dialog from Flask's background thread.
# The browser "Allow camera" button (getUserMedia) is the primary camera path.
os.environ["OPENCV_AVFOUNDATION_SKIP_AUTH"] = "1"

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
from functools import wraps

from braille_ocr.realtime.camera_loop import CameraLoop
from braille_ocr.realtime.session import ScanSession
from braille_ocr.realtime.tts_engine import TTSEngine
from braille_ocr.realtime.async_pipeline import async_ocr

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# ── Production Extensions ─────────────────────────────────────────────────────
# Redis Client
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = None
try:
    redis_client = redis.from_url(redis_url)
    redis_client.ping()
except Exception as e:
    print(f"⚠️  Redis not available: {e}. Falling back to memory state.")
    redis_client = None

# SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "100 per hour"],
    storage_uri=redis_url if redis_client else "memory://"
)

# Basic Auth Decorator
def check_auth(username, password):
    # In production, this should check a secure database
    return username == os.getenv("APP_USER", "admin") and password == os.getenv("APP_PASS", "password")

def authenticate():
    return jsonify({"error": "Unauthorized Access"}), 401

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Bypass auth in development if no credentials set
        if not os.getenv("APP_USER"):
            return f(*args, **kwargs)
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


# ── Global singletons ─────────────────────────────────────────────────────────
tts     = TTSEngine(rate=175, volume=1.0)
session = ScanSession()
camera  = CameraLoop(tts, session, camera_index=0, target_fps=8)

# Browser webcam is primary — click "Allow camera" in the UI.
camera._push_placeholder("Click Allow camera above.\nVideo only — no microphone.")

# ── Groq corrector (optional) ─────────────────────────────────────────────────
try:
    from braille_ai.ocr_corrector import correct_with_groq, is_groq_available
    _GROQ_OK = False # Disabled for Phase 2 debugging
    def correct_with_groq(text): return text
    print(f"⚠️  Groq AI correction: disabled for Phase 2")
except ImportError:
    _GROQ_OK = False
    def correct_with_groq(text): return text

# ── CNN predictor (optional) ──────────────────────────────────────────────────
try:
    from braille_ai.cnn_predictor import CNNPredictor
    _cnn = CNNPredictor()
    _CNN_OK = _cnn.model is not None
    print(f"{'✅' if _CNN_OK else '⚠️ '} CNN model: {'loaded' if _CNN_OK else 'not found'}")
except Exception as e:
    _CNN_OK = False
    _cnn = None
    print(f"⚠️  CNN predictor unavailable: {e}")


# ── Helper: process an image file for full-page OCR ──────────────────────────

def _process_image_bytes(img_bytes: bytes) -> dict:
    """
    Run the full pipeline on raw image bytes:
      1. Decode image
      2. Detect braille dots (realtime detector)
      3. Optionally run CNN on extracted cells
      4. Translate to English
      5. Optionally correct with Groq
    Returns a result dict.
    """
    arr   = np.frombuffer(img_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        return {"error": "Could not decode image"}

    from braille_ocr.realtime.perspective import correct_perspective
    working_frame, contour = correct_perspective(frame)
    gray = cv2.cvtColor(working_frame, cv2.COLOR_BGR2GRAY)

    from braille_ocr.realtime.braille_detector import detect_braille, braille_to_english, _decode_flexible, _find_blobs_adaptive, _filter_uniform_size, _estimate_two_pass_spacing
    result = detect_braille(gray, camera_mode=False)   # permissive for uploads

    # For uploads: if confidence is low but dots were found, still attempt decode
    # so the user sees something rather than a blank result
    if not result.valid and result.dot_count >= 2:
        dots = _find_blobs_adaptive(gray)
        dots = _filter_uniform_size(dots, tolerance=0.70)
        if len(dots) >= 2:
            med_r = float(np.median([d[2] for d in dots]))
            intra, inter = _estimate_two_pass_spacing(dots, med_r)
            raw_text, boxes, per_cell_conf, dot_infos = _decode_flexible(dots, intra, inter, med_r)
            if raw_text and raw_text.strip():
                result.text = raw_text
                result.boxes = boxes
                result.per_cell_conf = per_cell_conf
                result.dots = dot_infos
                result.message = "low_confidence_result"

    if not result.text:
        return {
            "ok": False,
            "text": "",
            "corrected": "",
            "confidence": round(result.confidence, 2),
            "dot_count": result.dot_count,
            "message": result.message or "No braille detected",
        }

    english = braille_to_english(result.text)

    # Groq correction
    corrected = english
    if _GROQ_OK and english:
        corrected = correct_with_groq(english)

    # Annotate frame with per-dot coloured circles and cell boxes
    annotated = working_frame.copy()
    for dot in result.dots:
        cv2.circle(annotated, (dot.x, dot.y), max(dot.r + 2, 5), dot.colour, 2)
    for i, (x, y, bw, bh) in enumerate(result.boxes):
        conf_i = result.per_cell_conf[i] if i < len(result.per_cell_conf) else 0.5
        box_colour = (
            (0, 220, 100) if conf_i >= 0.7 else
            (0, 200, 220) if conf_i >= 0.4 else
            (60, 60, 220)
        )
        cv2.rectangle(annotated, (x, y), (x + bw, y + bh), box_colour, 2)
    if english:
        cv2.putText(
            annotated, f"Reading: {english}",
            (12, annotated.shape[0] - 16),
            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 120), 2,
        )

    _, jpeg_buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
    frame_b64 = base64.b64encode(jpeg_buf.tobytes()).decode("utf-8")

    return {
        "ok": True,
        "text": english,
        "corrected": corrected,
        "confidence": round(result.confidence, 2),
        "dot_count": result.dot_count,
        "frame": frame_b64,
        "groq_used": _GROQ_OK and corrected != english,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/debug", methods=["GET", "POST"])
@requires_auth
@limiter.limit("50 per minute")
def api_debug():
    """
    Get or set the debug mode configuration.
    POST JSON: { "enabled": true, "save_to_disk": true, "show_ids": false }
    """
    from braille_ocr.realtime.frame_analyzer import debug_visualizer
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        if "enabled" in data:
            debug_visualizer.enabled = bool(data["enabled"])
        if "save_to_disk" in data:
            debug_visualizer.save_to_disk = bool(data["save_to_disk"])
        if "show_ids" in data:
            debug_visualizer.show_ids = bool(data["show_ids"])

        status = "enabled" if debug_visualizer.enabled else "disabled"
        disk_status = "active" if debug_visualizer.save_to_disk else "inactive"
        tts.speak(f"Debug mode {status}. Disk persistence is {disk_status}.", priority=True)

    return jsonify({
        "enabled": debug_visualizer.enabled,
        "save_to_disk": debug_visualizer.save_to_disk,
        "show_ids": debug_visualizer.show_ids,
        "save_dir": debug_visualizer.save_dir,
    })


@app.route("/api/frame")
@limiter.limit("120 per minute")
def api_frame():
    b64 = camera.get_latest_frame_b64()
    return jsonify({"frame": b64, "ts": time.time()})


@app.route("/api/status")
def api_status():
    status = camera.get_status()
    status["stats"]   = session.stats()
    status["paused"]  = session.is_paused
    status["running"] = camera.running
    status["groq_ok"] = _GROQ_OK
    status["cnn_ok"]  = _CNN_OK
    return jsonify(status)


@app.route("/api/history")
def api_history():
    segments = session.get_history(30)
    return jsonify([
        {"text": s.text, "ts": s.timestamp, "source": s.source,
         "confidence": getattr(s, "confidence", 0)}
        for s in segments
    ])


@app.route("/api/voices")
def api_voices():
    """Return available TTS voices for the dropdown."""
    voices = tts.get_voices()
    return jsonify({"voices": voices})


@app.route("/api/speak", methods=["POST"])
def api_speak():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400
    session.add_text(text, source="manual")
    tts.speak(text, priority=True)
    return jsonify({"ok": True, "text": text})


@app.route("/api/speak_history", methods=["POST"])
def api_speak_history():
    full = session.get_full_text()
    if not full:
        tts.speak("No text in history yet.", priority=True)
    else:
        tts.speak(full, priority=True)
    return jsonify({"ok": True})


@app.route("/api/pause", methods=["POST"])
def api_pause():
    data   = request.get_json(silent=True) or {}
    paused = bool(data.get("paused", not session.is_paused))
    session.is_paused = paused
    msg = "Scanning paused." if paused else "Scanning resumed."
    tts.speak(msg, priority=True)
    return jsonify({"ok": True, "paused": paused})


@app.route("/api/clear", methods=["POST"])
def api_clear():
    session.clear()
    tts.speak("History cleared.", priority=True)
    return jsonify({"ok": True})


@app.route("/api/tts_settings", methods=["POST"])
def api_tts_settings():
    data     = request.get_json(silent=True) or {}
    rate     = int(data.get("rate",     tts._rate))
    volume   = float(data.get("volume", tts._volume))
    voice_id = data.get("voice_id", None)

    tts._rate   = max(80, min(300, rate))
    tts._volume = max(0.0, min(1.0, volume))

    if voice_id:
        tts.set_voice(voice_id)

    tts.speak("Settings updated.", priority=True)
    return jsonify({"ok": True, "rate": tts._rate, "volume": tts._volume})


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "ts": time.time(), "groq": _GROQ_OK, "cnn": _CNN_OK})


@app.route("/api/process_frame", methods=["POST"])
def api_process_frame():
    """Process a JPEG frame from the browser webcam (getUserMedia)."""
    data = request.get_json(silent=True) or {}
    b64  = data.get("frame", "")
    if not b64:
        return jsonify({"error": "No frame provided"}), 400

    try:
        raw   = base64.b64decode(b64.split(",", 1)[-1])
        arr   = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({"error": "Could not decode image"}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    camera.browser_mode = True
    status = camera.process_bgr_frame(frame, source="browser")
    status["stats"]  = session.stats()
    status["paused"] = session.is_paused
    status["frame"]  = camera.get_latest_frame_b64()
    return jsonify({"ok": True, **status})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """
    Process an uploaded image file (JPEG/PNG).
    Accepts multipart/form-data with field 'image', or JSON with base64 'frame'.
    """
    img_bytes = None

    # Multipart upload
    if "image" in request.files:
        f = request.files["image"]
        img_bytes = f.read()
    # JSON base64
    elif request.is_json:
        data = request.get_json(silent=True) or {}
        b64  = data.get("frame", "")
        if b64:
            try:
                img_bytes = base64.b64decode(b64.split(",", 1)[-1])
            except Exception:
                pass

    if not img_bytes:
        return jsonify({"error": "No image provided"}), 400

    result = _process_image_bytes(img_bytes)
    if result.get("ok") and result.get("text"):
        session.add_text(
            result.get("corrected") or result["text"],
            source="upload",
            confidence=result.get("confidence", 0),
        )
        tts.speak(result.get("corrected") or result["text"], priority=True)

    return jsonify(result)


@app.route("/api/camera/restart", methods=["POST"])
def api_camera_restart():
    camera.browser_mode = False
    result = camera.restart_opencv_camera()
    result["stats"] = session.stats()
    return jsonify(result)


@app.route("/api/demo")
def api_demo():
    """Demo: run the detector on a bundled test image."""
    samples = {
        "hello": "test_hello.png",
        "hi":    "test_hi.png",
        "cat":   "test_cat.png",
        "abc":   "test_abc.png",
    }
    key      = request.args.get("image", "hello").lower()
    filename = samples.get(key, samples["hello"])
    path     = os.path.join(os.path.dirname(__file__), filename)

    img = cv2.imread(path)
    if img is None:
        # Try braille test images
        alt = os.path.join(os.path.dirname(__file__), f"test_braille_{key}.png")
        img = cv2.imread(alt)
    if img is None:
        return jsonify({"error": f"Sample image not found: {filename}"}), 404

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    out  = camera.process_gray_frame(gray, img.copy())

    if out.get("valid") and out.get("text"):
        text = out["text"]
        if _GROQ_OK:
            text = correct_with_groq(text)
        session.add_text(text, source="demo", confidence=out.get("confidence", 1.0))
        tts.speak(f"Detected: {text}", priority=True)

    _, jpeg_buf = cv2.imencode(".jpg", out["annotated"], [cv2.IMWRITE_JPEG_QUALITY, 90])
    frame_b64   = base64.b64encode(jpeg_buf.tobytes()).decode("utf-8")

    with camera._lock:
        camera._latest_jpeg = jpeg_buf.tobytes()
        camera._latest_status.update({
            "quality":          "OK",
            "braille_detected": True,
            "dot_count":        out.get("dot_count", 0),
            "last_text":        out.get("text", ""),
            "confidence":       out.get("confidence", 0),
        })

    return jsonify({
        "ok":         True,
        "image":      key,
        "text":       out.get("text", ""),
        "confidence": out.get("confidence", 0),
        "valid":      out.get("valid", False),
        "frame":      frame_b64,
        "spoken":     bool(out.get("valid") and out.get("text")),
    })


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Braille Accessibility Scanner (Phase 3 Production)")
    print("  Open http://localhost:5050 in your browser")
    print("=" * 60 + "\n")
    socketio.run(app, host="0.0.0.0", port=5050, debug=False)
