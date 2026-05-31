# FULL RUNTIME AUDIT REPORT

**Date of Audit:** May 28, 2026  
**Auditor:** Senior Production QA & Infrastructure Engineer  

## Executive Summary
A comprehensive runtime verification of the BrailleScan repository was conducted. While the theoretical architecture is sound, the project is **not** currently ready for live judging or out-of-the-box execution by external developers. Significant mismatches exist between the documentation, the dependency manifest, and the actual runtime code. Several critical components crash instantly, and the evaluation scripts contain faked (mocked) results.

**Production Readiness Score:** 3/10 (Requires critical fixes before submission)

---

## Fully Working Components
- **Dataset Extraction Loop:** The core OpenCV extraction loop inside `convert_dataset.py` successfully processes available raw images (e.g., DSBI) into single-cell patches.
- **Path Safety:** No hardcoded local machine paths (e.g., `/Users/`, `C:\`) were found. The codebase relies properly on relative paths.
- **Environment Variable Fallbacks:** The system correctly falls back and gracefully degrades when optional APIs (like the Groq LLM) are missing.

---

## Partially Working Components
- **Demo Mode (`demo_mode.py`):** 
  - **Issue:** Fails instantly on macOS terminal execution with `OpenCV: not authorized to capture video (status 0)`.
  - **Cause:** OpenCV cannot independently trigger the macOS camera permission dialog from a terminal.
  - **Fix:** Requires explicit terminal permissions in macOS System Settings or a wrapper.
- **Training Pipeline (`train_dot_model.py`):**
  - **Issue:** Hangs or crashes if `convert_dataset.py` hasn't fully finished populating the `datasets/training_data/` directory.

---

## Broken Components
- **Flask Web App (`app.py`):**
  - **Issue:** Crashes instantly on startup with `RuntimeError: The Werkzeug web server is not designed to run in production. Pass allow_unsafe_werkzeug=True...`
  - **Cause:** `socketio.run()` detects a production environment but fails to properly hook into `eventlet` (which throws a deprecation warning) and defaults to rejecting Werkzeug.
  - **Fix:** Add `allow_unsafe_werkzeug=True` for local demos, or properly configure a WSGI server (gunicorn/eventlet).
- **Geometry Benchmark (`evaluation/geometry_benchmark.py`):**
  - **Issue:** **Completely faked results.**
  - **Cause:** The script attempts to import `PerspectiveCorrector` from `braille_ocr.realtime.perspective`. However, `perspective.py` only contains functions (e.g., `correct_perspective`), not a class. The script catches the `ImportError`, sets `mock_mode = True`, bypasses the entire CV pipeline, explicitly assigns `detected_bboxes = gt_bboxes # Mock`, and outputs a fake 100% detection rate.
  - **Fix:** Rewrite the benchmark to import the correct functions and actually process the images.
- **ScienceDB Integration:**
  - **Issue:** `python synthetic_dataset/scripts/import_scienceDB.py` outputs `Error: datasets/scienceDB does not exist.`
  - **Cause:** The raw dataset is not bundled in the repo and no download script is provided.

---

## Hidden Assumptions
1. **Missing Dependencies in `requirements.txt`:** 
   - The README instructs users to run `pip install -r requirements.txt`, but this file is missing `flask-socketio`, `flask-limiter`, `redis`, and `eventlet`. Attempting to run `app.py` after following the README results in an immediate `ModuleNotFoundError`.
2. **PYTHONPATH Assumption:**
   - Scripts inside `synthetic_dataset/scripts/` and `evaluation/` use absolute imports like `from braille_ocr.realtime...`. Because the project lacks a `setup.py` (no `pip install -e .` available), executing these scripts from the root directory throws `ModuleNotFoundError: No module named 'braille_ocr'` unless the user manually sets `export PYTHONPATH=.`.

---

## Performance Metrics
- **Startup Latency:** N/A (Web app crashes on boot).
- **Inference Latency:** N/A (Cannot process live frames).
- **Dataset Conversion:** High CPU usage. OpenCV perspective processing on 343 full-resolution images takes several minutes to extract cells.

---

## Stability Assessment
Currently, the project is highly fragile. If a judge were to clone this repository, run the setup instructions from the README, and attempt to start the app, they would immediately hit a `ModuleNotFoundError`. If they manually resolved the dependencies, the app would crash via the Werkzeug SocketIO error. If they ran `demo_mode.py`, it would fail due to camera permissions. 

---

## Security & Safety
- **No hardcoded secrets:** Validated.
- **No unsafe file loading:** Validated. `np.frombuffer` is used securely.

---

## Judge Readiness
**Would this survive a real judging session? NO.**
Judges follow instructions exactly as written. The README instructions guarantee an immediate crash. Furthermore, if a judge inspects the evaluation code, they will discover that the geometry benchmark is deliberately mocking 100% accuracy, which is grounds for disqualification in technical hackathons.

---

## Critical Fixes Required (In Priority Order)
1. **Update `requirements.txt`**: Add `flask-socketio`, `flask-limiter`, `redis`, and `eventlet`.
2. **Fix `app.py` Startup**: Add `allow_unsafe_werkzeug=True` to `socketio.run()`.
3. **Fix the Evaluation Script**: Remove the mock block in `geometry_benchmark.py` and correctly import `correct_perspective` from `perspective.py`.
4. **Fix Import Paths**: Add a `setup.py` or `pyproject.toml` so the package can be installed in editable mode (`pip install -e .`), preventing `PYTHONPATH` errors.
5. **Provide Dataset Scripts**: Add a script or instructions to actually download the ScienceDB dataset.

---

## Final Technical Verdict
The underlying computer vision math in `perspective.py` and the architecture concept are highly sophisticated. However, the glue code connecting the system is fundamentally broken. The project currently relies on "happy path" assumptions, undocumented environment setups, and faked benchmarks. Fixing the 5 items above will elevate this from a broken prototype to a robust, judge-ready application.
