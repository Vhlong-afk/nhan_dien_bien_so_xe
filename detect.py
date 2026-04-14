import cv2
import numpy as np
from ultralytics import YOLO
import easyocr
import base64
from pathlib import Path
import os

class LicensePlateDetector:
    def __init__(self):
        # Load YOLO model
        self.model = YOLO("best.pt")
        # Load EasyOCR reader (Vietnamese + English)
        #self.ocr_reader = easyocr.Reader(['vi', 'en'], gpu=False)

    def detect_license_plate(self, image_path):
        """
        Detect license plate in image/video frame (ROBUST VERSION).
        Returns: cropped_plate_image (base64), ocr_text, confidence
        """
        print(f"[DEBUG] Processing: {image_path}")
        
        #  CHECK FILE EXISTS FIRST
        if isinstance(image_path, str):
            if not os.path.exists(image_path):
                return None, f"❌ File không tồn tại: {image_path}", 0.0
            if not os.access(image_path, os.R_OK):
                return None, f"❌ Không đọc được file (permission): {image_path}", 0.0
            image = cv2.imread(image_path)
            video_mode = False
            print(f"[DEBUG] File OK, shape: {image.shape if image is not None else 'None'}")
        else:
            image = image_path
            video_mode = True

        if image is None:
            return None, "❌ cv2.imread fail - File corrupt hoặc format lạ", 0.0

        # Preprocessing: Tăng contrast + giảm noise
        image = cv2.convertScaleAbs(image, alpha=1.2, beta=15)  # Tăng brightness/contrast
        image = cv2.GaussianBlur(image, (3,3), 0)  # Giảm noise
        
        #  TRIAL 1: Main model (best.pt)
        print("[DEBUG] === TRIAL 1: best.pt ===")
        results = self.model(image, conf=0.25, imgsz=640, verbose=False, device='cpu')
        
        print(f"[DEBUG] Tìm thấy {len(results[0].boxes) if results[0].boxes is not None else 0} objects")
        if results[0].boxes is not None:
            confs_debug = results[0].boxes.conf.cpu().numpy()
            print(f"[DEBUG] Confidences: {confs_debug}")
        
        #  FALLBACK: Nếu fail → thử yolov8n.pt
        if results[0].boxes is None or len(results[0].boxes) == 0:
            print("[DEBUG] === FALLBACK: yolov8n.pt ===")
            try:
                fallback_model = YOLO('yolov8s.pt')  # Generic plates
                results = fallback_model(image, conf=0.25, imgsz=640, verbose=False, device='cpu')
                print(f"[DEBUG] Fallback found: {len(results[0].boxes) if results[0].boxes else 0}")
            except:
                print("[DEBUG] Fallback model fail")
        
        if results[0].boxes is None or len(results[0].boxes) == 0:
            #  FINAL TRY: Resize + low conf
            print("[DEBUG] === FINAL TRY: Resize 50% ===")
            small_img = cv2.resize(image, (320, 320))
            results = self.model(small_img, conf=0.25, imgsz=320, verbose=False, device='cpu')
            
            if results[0].boxes is None or len(results[0].boxes) == 0:
                return None, "❌ Không detect được dù thử 3 cách (best.pt + yolov8n + resize). Gửi ảnh + terminal log!", 0.0

        # Get best box (license plate)
        boxes = results[0].boxes.xyxy.cpu().numpy()
        confs = results[0].boxes.conf.cpu().numpy()
        print(f"[DEBUG] Best confidence: {max(confs):.3f}")
        if len(confs) == 0:
            return None, "Không có box hợp lệ", 0.0
        best_idx = np.argmax(confs)
        best_box = boxes[best_idx]
        best_conf = confs[best_idx]

        # Crop plate
        x1, y1, x2, y2 = map(int, best_box)
        cropped_plate = image[y1:y2, x1:x2]

        if cropped_plate.size == 0:
            return None, "Không crop được biển số", best_conf

        # OCR text
        #ocr_results = self.ocr_reader.readtext(cropped_plate)
        #ocr_text = ' '.join([text[1] for text in ocr_results]).strip().upper()
        #if not ocr_text:
           # ocr_text = "Không đọc được text"
        ocr_text = "DEMO"

        # Convert cropped to base64
        _, buffer = cv2.imencode('.jpg', cropped_plate)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        return img_base64, ocr_text, float(best_conf)

    def process_video(self, video_path, output_dir='output'):
        """
        Process video and save frames with plates.
        For demo, extract key frames.
        """
        cap = cv2.VideoCapture(video_path)
        frame_count = 0
        os.makedirs(output_dir, exist_ok=True)
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % 30 == 0:  # Every 30 frames
                img_b64, text, conf = self.detect_license_plate(frame)
                if img_b64:
                    # Save example frame
                    cv2.imwrite(f'{output_dir}/frame_{frame_count}.jpg', frame)
            frame_count += 1
        cap.release()
        return f"Đã xử lý video, lưu {frame_count//30} frames tại {output_dir}"

# Test function
if __name__ == "__main__":
    detector = LicensePlateDetector()
    # Test với nhiều ảnh
    test_images = [
        'dataset/images/train/ngoaigiao1.jpg',
        'dataset/images/val/xemay14.jpg'
    ]
    for img_path in test_images:
        print(f"\nTest {img_path}:")
        img_b64, text, conf = detector.detect_license_plate(img_path)
        print(f"Text: {text}, Conf: {conf}")
