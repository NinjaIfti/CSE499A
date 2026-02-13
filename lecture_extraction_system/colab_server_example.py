from flask import Flask, request, jsonify
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
from pyngrok import ngrok

app = Flask(__name__)
model = None
tokenizer = None

def load_llm():
    global model, tokenizer
    model_name = "microsoft/phi-2"

    print(f"Loading model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load config first and set pad_token_id before loading model
    config = AutoConfig.from_pretrained(model_name, trust_remote_code=True)
    config.pad_token_id = tokenizer.pad_token_id

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        config=config,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )

    print("Model loaded successfully!")

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "model_loaded": model is not None}), 200

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        context = data.get('context', '')
        max_tokens = data.get('max_tokens', 500)
        temperature = data.get('temperature', 0.7)

        full_prompt = f"""Based on the following lecture content, answer the question.

Lecture Content:
{context}

Question: {prompt}

Answer:"""

        inputs = tokenizer(full_prompt, return_tensors="pt", truncation=True, max_length=2048).to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )

        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        answer = generated_text[len(full_prompt):].strip()

        return jsonify({
            "text": answer,
            "metadata": {
                "prompt_length": len(full_prompt),
                "tokens_generated": len(outputs[0]) - len(inputs['input_ids'][0])
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def start_server():
    load_llm()
    public_url = ngrok.connect(5000)
    print(f"\n🚀 Server is running!")
    print(f"📡 Public URL: {public_url}")
    print(f"Copy this URL to your local app\n")
    app.run(port=5000)

if __name__ == "__main__":
    start_server()
