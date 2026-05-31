"""
augment_realism.py
------------------
Synthetic-to-Real Augmentation Engine.
Applies transformations to synthetic braille images to mimic real-world conditions:
- Blur, Perspective Distortion, Brightness Variation, Noise Injection, Dot Imperfections.
"""

import cv2
import numpy as np
import random
from PIL import Image, ImageEnhance, ImageFilter

class RealismAugmentor:
    def __init__(self, p=0.5):
        self.p = p # probability of applying a specific augmentation
        
    def _apply(self, prob):
        return random.random() < prob

    def augment_all(self, image: np.ndarray, is_dot_mask: bool = False) -> np.ndarray:
        """
        Applies a random combination of augmentations.
        If is_dot_mask is True, only geometric transformations are applied 
        to ensure labels align.
        """
        img = image.copy()
        
        # 1. Perspective Distortion (Geometric)
        if self._apply(self.p):
            img = self.perspective_distortion(img)
            
        # 2. Geometric dot imperfections (only applied to dot mask if we want missing dots)
        if is_dot_mask and self._apply(self.p):
            img = self.dot_imperfections_mask(img)
            return img # Stop here for masks
            
        if is_dot_mask:
            return img
            
        # The rest are applied only to the RGB/Gray image, not the mask
        
        # 3. Dot Imperfections (Visual)
        if self._apply(self.p):
            img = self.dot_imperfections_visual(img)
            
        # 4. Blur
        if self._apply(self.p):
            img = self.apply_blur(img)
            
        # 5. Brightness & Shadows
        if self._apply(self.p):
            img = self.brightness_variation(img)
            
        # 6. Noise & Texture
        if self._apply(self.p):
            img = self.noise_injection(img)
            
        return img

    def apply_blur(self, img: np.ndarray) -> np.ndarray:
        blur_type = random.choice(["gaussian", "motion", "defocus"])
        if blur_type == "gaussian":
            ksize = random.choice([3, 5])
            return cv2.GaussianBlur(img, (ksize, ksize), 0)
        elif blur_type == "motion":
            size = random.randint(3, 7)
            kernel_motion_blur = np.zeros((size, size))
            kernel_motion_blur[int((size-1)/2), :] = np.ones(size)
            kernel_motion_blur = kernel_motion_blur / size
            return cv2.filter2D(img, -1, kernel_motion_blur)
        else: # defocus
            ksize = random.choice([3, 5])
            return cv2.blur(img, (ksize, ksize))

    def perspective_distortion(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        pts1 = np.float32([[0,0],[w,0],[0,h],[w,h]])
        
        # Add random skew
        skew_max = int(min(w, h) * 0.05)
        pts2 = np.float32([
            [random.randint(0, skew_max), random.randint(0, skew_max)],
            [w - random.randint(0, skew_max), random.randint(0, skew_max)],
            [random.randint(0, skew_max), h - random.randint(0, skew_max)],
            [w - random.randint(0, skew_max), h - random.randint(0, skew_max)]
        ])
        
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        return cv2.warpPerspective(img, matrix, (w, h), borderValue=(255, 255, 255) if len(img.shape)==3 else 255)

    def brightness_variation(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        # Simulate uneven illumination/shadow
        shadow = np.zeros_like(img, dtype=np.float32)
        center_x = random.randint(0, w)
        center_y = random.randint(0, h)
        radius = random.randint(min(w, h)//2, min(w, h)*2)
        
        for i in range(h):
            for j in range(w):
                dist = np.hypot(j - center_x, i - center_y)
                # Gradient shadow
                intensity = np.clip(1.0 - (dist / radius), 0.3, 1.0)
                shadow[i, j] = intensity if len(img.shape) == 2 else [intensity]*3
                
        img_float = img.astype(np.float32) * shadow
        
        # Overall brightness shift
        shift = random.uniform(0.6, 1.4)
        img_float = np.clip(img_float * shift, 0, 255)
        
        return img_float.astype(np.uint8)

    def noise_injection(self, img: np.ndarray) -> np.ndarray:
        # Camera noise / Grain
        noise = np.random.normal(0, random.uniform(5, 15), img.shape).astype(np.float32)
        noisy_img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        
        # JPEG compression artifact simulation
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), random.randint(30, 80)]
        result, encimg = cv2.imencode('.jpg', noisy_img, encode_param)
        decimg = cv2.imdecode(encimg, 1 if len(img.shape)==3 else 0)
        
        return decimg

    def dot_imperfections_visual(self, img: np.ndarray) -> np.ndarray:
        # Morphological operations to erode/dilate dots simulating weak embossing
        op = random.choice([cv2.MORPH_ERODE, cv2.MORPH_DILATE])
        kernel = np.ones((2,2), np.uint8)
        return cv2.morphologyEx(img, op, kernel)

    def dot_imperfections_mask(self, mask: np.ndarray) -> np.ndarray:
        # Randomly drop dots (missing dots) for robustness
        # Assuming dots are white (255) on black (0) in the mask
        if self._apply(0.1): # 10% chance to drop a dot region
            h, w = mask.shape[:2]
            # Find contours (dots)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                c = random.choice(contours)
                cv2.drawContours(mask, [c], -1, 0, -1)
        return mask

if __name__ == "__main__":
    import sys
    print("Augmentor initialized.")
    if len(sys.argv) > 2:
        img = cv2.imread(sys.argv[1])
        if img is not None:
            aug = RealismAugmentor(p=1.0)
            res = aug.augment_all(img)
            cv2.imwrite(sys.argv[2], res)
            print(f"Saved augmented image to {sys.argv[2]}")
