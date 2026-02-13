import requests
import json
from typing import Dict, Any, Optional
from config import COLAB_API_URL, API_TIMEOUT, UPLOAD_TIMEOUT

class LLMClient:
    
    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or COLAB_API_URL
        self.session = requests.Session()
    
    def test_connection(self) -> bool:
        try:
            response = self.session.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def generate_response(self, prompt: str, context: str = "", max_tokens: int = 500, temperature: float = 0.7) -> Dict[str, Any]:
        try:
            payload = {
                "prompt": prompt,
                "context": context,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = self.session.post(
                f"{self.api_url}/generate",
                json=payload,
                timeout=API_TIMEOUT
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "response": response.json().get("text", ""),
                    "metadata": response.json().get("metadata", {})
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}",
                    "response": ""
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timed out. The LLM is taking too long to respond.",
                "response": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error communicating with LLM: {str(e)}",
                "response": ""
            }
    
    def summarize_lecture(self, transcript: str, max_length: int = 300) -> Dict[str, Any]:
        prompt = f"Summarize the following lecture in about {max_length} words:\n\n{transcript}"
        return self.generate_response(prompt, context="", max_tokens=max_length * 2)
    
    def explain_topic(self, topic: str, context: str) -> Dict[str, Any]:
        prompt = f"Based on the lecture content, explain the topic: {topic}"
        return self.generate_response(prompt, context=context)
    
    def answer_question(self, question: str, context: str) -> Dict[str, Any]:
        prompt = f"Answer the following question based on the lecture content: {question}"
        return self.generate_response(prompt, context=context)
    
    def update_api_url(self, new_url: str):
        self.api_url = new_url

    def upload_video(self, video_path: str) -> Dict[str, Any]:
        try:
            filename = video_path.split("/")[-1].split("\\")[-1]
            with open(video_path, "rb") as f:
                response = self.session.post(
                    f"{self.api_url}/upload",
                    files={"video": (filename, f)},
                    timeout=UPLOAD_TIMEOUT
                )
            if response.status_code == 200:
                return {"success": True, "job_id": response.json().get("job_id")}
            return {"success": False, "error": response.json().get("error", f"Status {response.status_code}")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        try:
            response = self.session.get(f"{self.api_url}/status/{job_id}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {"success": True, "status": data["status"], "progress": data["progress"], "message": data["message"], "error": data.get("error")}
            return {"success": False, "status": "unknown"}
        except Exception as e:
            return {"success": False, "status": "error", "error": str(e)}

    def get_job_result(self, job_id: str) -> Dict[str, Any]:
        try:
            response = self.session.get(f"{self.api_url}/result/{job_id}", timeout=60)
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            return {"success": False, "error": response.json().get("error", f"Status {response.status_code}")}
        except Exception as e:
            return {"success": False, "error": str(e)}
