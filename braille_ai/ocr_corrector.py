"""
ocr_corrector.py
----------------
Groq-powered OCR correction for Braille text output.
Uses llama-3.1-8b-instant to fix OCR errors and reconstruct readable English.
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

_client = None

# Logging file
_LOG_FILE = "braille_ai/temp/correction_logs.jsonl"
os.makedirs(os.path.dirname(_LOG_FILE), exist_ok=True)

def _get_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        from groq import Groq
        _client = Groq(api_key=api_key)
        return _client
    except ImportError:
        return None

def _log_correction(raw_text: str, corrected_text: str, confidence: float, edit_distance: int, skipped: bool = False):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "raw_text": raw_text,
        "corrected_text": corrected_text,
        "confidence": confidence,
        "edit_distance": edit_distance,
        "skipped_due_to_confidence": skipped
    }
    try:
        with open(_LOG_FILE, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Failed to log correction: {e}")

def levenshtein(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def correct_ocr_text(raw_text: str, confidence: float) -> tuple[str, bool]:
    """
    Applies LLM correction to the raw OCR text with strict hallucination guards.
    Returns (corrected_text, was_changed).
    """
    import os
    if os.getenv("EVAL_MODE") == "1":
        return raw_text, False
        
    if not raw_text or len(raw_text.strip()) < 3:
        return raw_text, False

    client = _get_client()
    if client is None:
        return raw_text, False

    # CONFIDENCE GATING: Skip LLM if OCR confidence is too low
    if confidence < 0.65:
        _log_correction(raw_text, raw_text, confidence, 0, skipped=True)
        return raw_text, False

    prompt = (
        "You are a strict OCR corrector for a Braille reader. The input is raw text decoded from an image.\n"
        "Your task is to fix minor spelling, punctuation, or spacing errors.\n\n"
        "STRICT RULES:\n"
        "1. DO NOT invent new words or hallucinate semantic meaning.\n"
        "2. ONLY fix minor typos, merge fragmented words (e.g., 'he llo' -> 'hello'), or fix missing letters (e.g., 'c?t' -> 'cat').\n"
        "3. Preserve the original text as much as possible. Make the MINIMUM number of edits required.\n"
        "4. DO NOT add conversational text. Return ONLY the corrected text.\n"
        "5. If the text is already correct or you are unsure, return the exact original text.\n\n"
        f"Raw OCR text: {raw_text}\n"
        "Corrected text:"
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,   # zero for deterministic output
            max_tokens=256,
        )
        corrected = response.choices[0].message.content.strip()
        
        # Guardrails against hallucinations
        dist = levenshtein(raw_text, corrected)
        max_allowed_dist = max(3, int(len(raw_text) * 0.3))
        
        if dist > max_allowed_dist or len(corrected) > len(raw_text) * 1.5:
            # Over-corrected / hallucinated, fallback to original
            _log_correction(raw_text, raw_text, confidence, dist, skipped=False)
            return raw_text, False
            
        _log_correction(raw_text, corrected, confidence, dist, skipped=False)
        changed = bool(corrected and corrected != raw_text)
        return (corrected, True) if changed else (raw_text, False)
        
    except Exception as e:
        print(f"⚠️  Groq correction failed: {e}")
        return raw_text, False

def is_groq_available() -> bool:
    return _get_client() is not None

if __name__ == "__main__":
    test_cases = [
        ("HE1LO W0RLD", 0.9),
        ("the qu1ck br0wn f0x", 0.8),
        ("br?ille is a tact1le wr1ting system", 0.7),
        ("t??s i? a v?ry b?d re?d", 0.4) # Should skip due to low confidence
    ]
    print("Testing Controlled Groq OCR corrector...\n")
    for raw, conf in test_cases:
        corrected, changed = correct_ocr_text(raw, confidence=conf)
        print(f"  Raw (conf={conf}): {raw}")
        print(f"  Corrected:       {corrected}\n")
