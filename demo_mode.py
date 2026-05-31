import cv2
import numpy as np
import time
from collections import deque
from braille_ocr.realtime.braille_detector import detect_braille

class DemoUI:
    def __init__(self):
        self.text_history = deque(maxlen=5) # Smoothing
        self.conf_history = deque(maxlen=5)
        self.last_update_time = time.time()
        
    def add_text_shadow(self, img, text, pos, font, scale, color, thickness):
        """Draw text with a shadow for better readability."""
        cv2.putText(img, text, (pos[0]+2, pos[1]+2), font, scale, (0, 0, 0), thickness+1)
        cv2.putText(img, text, pos, font, scale, color, thickness)

    def draw_confidence_bar(self, img, conf, x, y, w, h):
        """Draw a live confidence bar."""
        cv2.rectangle(img, (x, y), (x+w, y+h), (50, 50, 50), -1)
        
        fill_w = int(w * conf)
        if conf > 0.8:
            color = (0, 255, 0)
        elif conf > 0.5:
            color = (0, 200, 255)
        else:
            color = (0, 0, 255)
            
        cv2.rectangle(img, (x, y), (x+fill_w, y+h), color, -1)
        cv2.rectangle(img, (x, y), (x+w, y+h), (255, 255, 255), 1)

    def update(self, frame):
        """Process frame and draw overlay UI."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Call the updated detector
        result = detect_braille(gray, camera_mode=True)
        
        # Smooth text and confidence
        if result.valid:
            self.text_history.append(result.text)
            self.conf_history.append(result.confidence)
        elif result.message == "LOW_CONFIDENCE" and result.text == "uncertain":
            self.text_history.append("...")
            self.conf_history.append(result.confidence)
        else:
            self.text_history.append("")
            self.conf_history.append(0.0)

        # Get smoothed values
        display_text = self.text_history[-1] if self.text_history else ""
        avg_conf = sum(self.conf_history) / max(len(self.conf_history), 1)

        # Draw UI
        h, w = frame.shape[:2]
        
        # Background overlay for text
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h-120), (w, h), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

        # Draw larger readable OCR text
        self.add_text_shadow(frame, f"Braille: {display_text}", (20, h-70), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

        # Draw confidence bar
        self.add_text_shadow(frame, "Confidence:", (20, h-25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        self.draw_confidence_bar(frame, avg_conf, 180, h-40, 200, 20)

        # Draw failure warnings
        warnings = []
        if result.message == "LOW_LIGHT":
            warnings.append("WARNING: LOW LIGHT")
        elif result.message == "GRID_UNSTABLE":
            warnings.append("WARNING: GRID UNSTABLE")
        elif result.message == "LOW_CONFIDENCE":
            warnings.append("WARNING: LOW CONFIDENCE")
        elif result.message == "BLUR_REJECTION":
            warnings.append("WARNING: CAMERA BLUR")

        y_warn = 40
        for warn in warnings:
            self.add_text_shadow(frame, warn, (20, y_warn), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            y_warn += 35

        # Draw bounding boxes from result
        if result.boxes:
            for box in result.boxes:
                bx, by, bw, bh = box
                cv2.rectangle(frame, (bx, by), (bx+bw, by+bh), (0, 255, 0), 2)

        return frame

def run_demo():
    print("Starting BrailleScan Demo Mode...")
    print("Press 'q' to quit.")
    
    cap = cv2.VideoCapture(0)
    ui = DemoUI()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break
            
        demo_frame = ui.update(frame)
        
        cv2.imshow('BrailleScan Demo', demo_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_demo()
