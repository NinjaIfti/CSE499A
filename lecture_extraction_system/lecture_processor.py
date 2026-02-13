from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from database import Lecture, Transcript, Frame, get_db
from video_processor import VideoProcessor
from audio_processor import AudioProcessor
from ocr_processor import OCRProcessor
from config import PROCESSED_DIR, MAX_PROMPT_LENGTH
import os

class LectureProcessor:
    
    def __init__(self):
        self.video_processor = None
        self.audio_processor = AudioProcessor()
        self.ocr_processor = OCRProcessor()
    
    def process_lecture(self, lecture_id: int, video_path: str, db: Session, progress_callback=None):
        try:
            # Update status
            lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
            lecture.status = "processing"
            db.commit()
            
            if progress_callback:
                progress_callback("Initializing video processor...", 10)
            
            self.video_processor = VideoProcessor(video_path)
            if not self.video_processor.open_video():
                raise Exception("Failed to open video")
            
            video_info = self.video_processor.get_video_info()
            lecture.duration = video_info["duration"]
            db.commit()
            
            if progress_callback:
                progress_callback("Extracting audio...", 20)
            
            audio_path = PROCESSED_DIR / f"lecture_{lecture_id}" / "audio.wav"
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not self.video_processor.extract_audio(str(audio_path)):
                raise Exception("Failed to extract audio")
            
            if progress_callback:
                progress_callback("Transcribing audio with Whisper...", 30)
            
            segments = self.audio_processor.get_segments_with_timestamps(str(audio_path))
            
            if progress_callback:
                progress_callback("Saving transcripts...", 50)
            
            for segment in segments:
                transcript = Transcript(
                    lecture_id=lecture_id,
                    timestamp_start=segment["start"],
                    timestamp_end=segment["end"],
                    text=segment["text"],
                    confidence=segment["confidence"]
                )
                db.add(transcript)
            db.commit()
            
            if progress_callback:
                progress_callback("Extracting frames...", 60)
            
            frames_data = self.video_processor.extract_frames(lecture_id)
            
            if progress_callback:
                progress_callback("Performing OCR on frames...", 70)
            
            total_frames = len(frames_data)
            for idx, (timestamp, frame_path) in enumerate(frames_data):
                ocr_result = self.ocr_processor.extract_text(frame_path)
                
                frame = Frame(
                    lecture_id=lecture_id,
                    timestamp=timestamp,
                    frame_path=frame_path,
                    extracted_text=ocr_result.get("full_text", ""),
                    handwritten_text=ocr_result.get("handwritten_text", ""),
                    printed_text=ocr_result.get("printed_text", ""),
                    ocr_confidence=ocr_result.get("average_confidence", 0.0)
                )
                db.add(frame)
                
                if progress_callback and idx % 5 == 0:
                    progress = 70 + (20 * (idx / total_frames))
                    progress_callback(f"Processing frames... ({idx}/{total_frames})", int(progress))
            
            db.commit()
            
            if progress_callback:
                progress_callback("Finalizing...", 95)
            
            lecture.status = "completed"
            lecture.processed_at = datetime.utcnow()
            db.commit()
            
            if progress_callback:
                progress_callback("Processing complete!", 100)
            
            return True
            
        except Exception as e:
            print(f"Error processing lecture: {e}")
            lecture.status = "failed"
            db.commit()
            
            if progress_callback:
                progress_callback(f"Error: {str(e)}", 0)
            
            return False
        finally:
            if self.video_processor:
                self.video_processor.close()
    
    def get_lecture_context(self, lecture_id: int, db: Session) -> str:
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        if not lecture:
            return ""
        
        context_parts = []
        
        context_parts.append("=== LECTURE TRANSCRIPT ===\n")
        transcripts = db.query(Transcript).filter(
            Transcript.lecture_id == lecture_id
        ).order_by(Transcript.timestamp_start).all()
        
        for transcript in transcripts:
            time_str = self._format_timestamp(transcript.timestamp_start)
            context_parts.append(f"[{time_str}] {transcript.text}")
        
        context_parts.append("\n\n=== TEXT FROM SLIDES (Printed) ===\n")
        frames = db.query(Frame).filter(
            Frame.lecture_id == lecture_id
        ).order_by(Frame.timestamp).all()
        
        for frame in frames:
            if frame.printed_text and frame.printed_text.strip():
                time_str = self._format_timestamp(frame.timestamp)
                context_parts.append(f"[{time_str}] {frame.printed_text}")
        
        context_parts.append("\n\n=== HANDWRITING ON SLIDES ===\n")
        for frame in frames:
            if frame.handwritten_text and frame.handwritten_text.strip():
                time_str = self._format_timestamp(frame.timestamp)
                context_parts.append(f"[{time_str}] {frame.handwritten_text}")

        full_context = "\n".join(context_parts)
        if len(full_context) > MAX_PROMPT_LENGTH:
            full_context = full_context[:MAX_PROMPT_LENGTH] + "\n\n[Truncated...]"
        return full_context
    
    def _format_timestamp(self, seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
