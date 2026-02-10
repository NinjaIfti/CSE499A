import whisper
from typing import List, Dict
from config import WHISPER_MODEL

class AudioProcessor:
    
    def __init__(self, model_name: str = WHISPER_MODEL):
        self.model_name = model_name
        self.model = None
    
    def load_model(self):
        if self.model is None:
            print(f"Loading Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
            print("Whisper model loaded successfully")
    
    def transcribe(self, audio_path: str, language: str = None) -> Dict:
        if self.model is None:
            self.load_model()
        
        try:
            print(f"Transcribing audio: {audio_path}")
            
            result = self.model.transcribe(
                audio_path,
                language=language,
                task="transcribe",
                verbose=False
            )
            
            return {
                "success": True,
                "text": result["text"],
                "segments": result["segments"],
                "language": result["language"]
            }
            
        except Exception as e:
            print(f"Error during transcription: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "segments": []
            }
    
    def get_segments_with_timestamps(self, audio_path: str) -> List[Dict]:
        result = self.transcribe(audio_path)
        
        if not result["success"]:
            return []
        
        segments = []
        for segment in result["segments"]:
            segments.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip(),
                "confidence": segment.get("confidence", 0.0)
            })
        
        return segments
    
    def get_full_transcript(self, audio_path: str) -> str:
        result = self.transcribe(audio_path)
        return result.get("text", "") if result["success"] else ""
