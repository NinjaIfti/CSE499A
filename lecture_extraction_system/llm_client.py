import requests
import json
from typing import Dict, Any, Optional
from config import COLAB_API_URL, API_TIMEOUT

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
