import easyocr
from typing import List, Dict, Tuple
import numpy as np
import cv2
from config import OCR_LANGUAGES, OCR_CONFIDENCE_THRESHOLD

class OCRProcessor:
    
    def __init__(self, languages: List[str] = None):
        self.languages = languages or OCR_LANGUAGES
        self.reader = None
    
    def load_reader(self):
        if self.reader is None:
            print(f"Loading OCR reader for languages: {self.languages}")
            self.reader = easyocr.Reader(self.languages, gpu=True)
            print("OCR reader loaded successfully")
    
    def _detect_handwriting(self, image_path: str, bbox: List) -> bool:
        try:
            img = cv2.imread(image_path)
            x_min = int(min([point[0] for point in bbox]))
            y_min = int(min([point[1] for point in bbox]))
            x_max = int(max([point[0] for point in bbox]))
            y_max = int(max([point[1] for point in bbox]))
            
            roi = img[y_min:y_max, x_min:x_max]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            stroke_variance = np.std(binary)
            
            is_handwritten = edge_density > 0.15 or stroke_variance > 70
            
            return is_handwritten
        except:
            return False
    
    def extract_text(self, image_path: str, confidence_threshold: float = OCR_CONFIDENCE_THRESHOLD) -> Dict:
        if self.reader is None:
            self.load_reader()
        
        try:
            results = self.reader.readtext(image_path)
            
            filtered_results = []
            all_text = []
            handwritten_text = []
            printed_text = []
            
            for bbox, text, confidence in results:
                if confidence >= confidence_threshold:
                    is_handwritten = self._detect_handwriting(image_path, bbox)
                    text_type = "handwritten" if is_handwritten else "printed"
                    
                    filtered_results.append({
                        "text": text,
                        "confidence": confidence,
                        "bbox": bbox,
                        "type": text_type
                    })
                    all_text.append(text)
                    
                    if is_handwritten:
                        handwritten_text.append(text)
                    else:
                        printed_text.append(text)
            
            return {
                "success": True,
                "full_text": " ".join(all_text),
                "handwritten_text": " ".join(handwritten_text),
                "printed_text": " ".join(printed_text),
                "details": filtered_results,
                "average_confidence": np.mean([r["confidence"] for r in filtered_results]) if filtered_results else 0.0
            }
            
        except Exception as e:
            print(f"Error during OCR: {e}")
            return {
                "success": False,
                "error": str(e),
                "full_text": "",
                "details": []
            }
    
    def extract_text_from_multiple(self, image_paths: List[str]) -> List[Dict]:
        results = []
        for image_path in image_paths:
            result = self.extract_text(image_path)
            results.append({
                "image_path": image_path,
                **result
            })
        return results
    
    def get_text_only(self, image_path: str) -> str:
        result = self.extract_text(image_path)
        return result.get("full_text", "") if result["success"] else ""
