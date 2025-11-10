# services/llm.py
# services/llm.py  — REST version with clear error messages
import os, requests

MODEL_DEFAULT = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
API_URL = "https://api.groq.com/openai/v1/chat/completions"

def chat_complete(system_prompt: str, user_prompt: str, temperature: float = 0.2, model: str = None):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY in environment or secrets.")

    payload = {
        "model": model or MODEL_DEFAULT,
        "temperature": float(temperature),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    resp = requests.post(API_URL, json=payload, headers=headers, timeout=60)
    if resp.status_code >= 400:
        try:
            err = resp.json()
        except Exception:
            err = {"error": {"message": resp.text}}
        # Surface the exact reason in the UI/logs
        raise RuntimeError(f"Groq API error {resp.status_code}: {err.get('error', {}).get('message', err)}")
    data = resp.json()
    return data["choices"][0]["message"]["content"]

