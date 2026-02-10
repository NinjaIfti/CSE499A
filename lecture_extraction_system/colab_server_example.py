# This is an example Flask API server to run in Google Colab
# It provides endpoints for the local app to connect to your LLM

from flask import Flask, request, jsonify
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from pyngrok import ngrok
import os

app = Flask(__name__)

# Global variables for model
model = None
tokenizer = None

def load_llm():
    """Load your LLM model - customize this based on your model"""
    global model, tokenizer
    
    # Example: Load a model (replace with your model)
    model_name = "microsoft/phi-2"  # or any other model you want
    
    print(f"Loading model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    print("Model loaded successfully!")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "model_loaded": model is not None
    }), 200

@app.route('/generate', methods=['POST'])
def generate():
    """Generate response from LLM"""
    try:
        data = request.json
        prompt = data.get('prompt', '')
        context = data.get('context', '')
        max_tokens = data.get('max_tokens', 500)
        temperature = data.get('temperature', 0.7)
        
        # Combine context and prompt
        full_prompt = f"""Based on the following lecture content, answer the question.

Lecture Content:
{context}

Question: {prompt}

Answer:"""
        
        # Tokenize and generate
        inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Decode response
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract only the answer part (after the prompt)
        answer = generated_text[len(full_prompt):].strip()
        
        return jsonify({
            "text": answer,
            "metadata": {
                "prompt_length": len(full_prompt),
                "tokens_generated": len(outputs[0]) - len(inputs['input_ids'][0])
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

def start_server():
    """Start Flask server with ngrok tunnel"""
    
    # Load model first
    load_llm()
    
    # Set ngrok auth token (get from https://dashboard.ngrok.com)
    # ngrok.set_auth_token("YOUR_NGROK_TOKEN")
    
    # Start ngrok tunnel
    public_url = ngrok.connect(5000)
    print(f"\n🚀 Server is running!")
    print(f"📡 Public URL: {public_url}")
    print(f"Copy this URL to your local app's API configuration\n")
    
    # Run Flask app
    app.run(port=5000)

# Usage in Colab:
# 1. Install dependencies:
#    !pip install flask pyngrok transformers torch accelerate bitsandbytes
#
# 2. Run this script:
#    start_server()
#
# 3. Copy the ngrok URL and paste it in your local Streamlit app

if __name__ == "__main__":
    start_server()
