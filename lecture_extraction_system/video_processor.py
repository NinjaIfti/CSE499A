import cv2
import os
from pathlib import Path
from typing import List, Tuple
import numpy as np
from config import FRAME_EXTRACTION_RATE, PROCESSED_DIR

class VideoProcessor:
    
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.video = None
        self.fps = None
        self.total_frames = None
        self.duration = None
    
    def open_video(self) -> bool:
        try:
            self.video = cv2.VideoCapture(self.video_path)
            if not self.video.isOpened():
                return False
            
            self.fps = self.video.get(cv2.CAP_PROP_FPS)
            self.total_frames = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))
            self.duration = self.total_frames / self.fps if self.fps > 0 else 0
            
            return True
        except Exception as e:
            print(f"Error opening video: {e}")
            return False
    
    def extract_audio(self, output_path: str) -> bool:
        try:
            import subprocess
            
            command = [
                'ffmpeg',
                '-i', self.video_path,
                '-vn',
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-y',
                output_path
            ]
            
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            return os.path.exists(output_path)
        except Exception as e:
            print(f"Error extracting audio: {e}")
            return False
    
    def extract_frames(self, lecture_id: int) -> List[Tuple[float, str]]:
        if not self.video or not self.video.isOpened():
            if not self.open_video():
                return []
        
        frames_dir = PROCESSED_DIR / f"lecture_{lecture_id}" / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        
        extracted_frames = []
        frame_count = 0
        saved_count = 0
        
        try:
            while True:
                ret, frame = self.video.read()
                if not ret:
                    break
                
                if frame_count % FRAME_EXTRACTION_RATE == 0:
                    timestamp = frame_count / self.fps
                    frame_path = frames_dir / f"frame_{saved_count:04d}.jpg"
                    
                    cv2.imwrite(str(frame_path), frame)
                    extracted_frames.append((timestamp, str(frame_path)))
                    saved_count += 1
                
                frame_count += 1
            
            return extracted_frames
            
        except Exception as e:
            print(f"Error extracting frames: {e}")
            return extracted_frames
        finally:
            self.close()
    
    def get_frame_at_timestamp(self, timestamp: float) -> np.ndarray:
        if not self.video or not self.video.isOpened():
            if not self.open_video():
                return None
        
        try:
            frame_number = int(timestamp * self.fps)
            self.video.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = self.video.read()
            
            if ret:
                return frame
            return None
        except Exception as e:
            print(f"Error getting frame at timestamp: {e}")
            return None
    
    def get_video_info(self) -> dict:
        if not self.video or not self.video.isOpened():
            if not self.open_video():
                return {}
        
        return {
            "duration": self.duration,
            "fps": self.fps,
            "total_frames": self.total_frames,
            "width": int(self.video.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self.video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        }
    
    def close(self):
        if self.video:
            self.video.release()
