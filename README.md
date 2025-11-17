
# PGRKAM Copilot (Streamlit + Groq)

Multilingual (Punjabi/Hindi/English) assistant for PGRKAM: chat, RAG over uploaded PDFs, smart intent routing, and basic job recommendations.

## Deploy on Streamlit Cloud
1. Fork/Upload this repo.
2. Add **secrets** in Streamlit:
   - `GROQ_API_KEY`
   - (optional) `MODEL_NAME` (default `llama-3.1-70b-versatile`)
3. Set Python version to 3.11+ and point to `requirements.txt`.
4. Run! Upload PGRKAM PDFs in the sidebar to enable RAG.

## Local run
```bash
pip install -r requirements.txt
export GROQ_API_KEY=YOUR_KEY
streamlit run app.py
=======
PGRKAM Smart Assistant

🚀 AI-powered smart assistant for the Punjab Ghar Ghar Rozgar and Karobar Mission (PGRKAM) digital employment platform.
This project enhances user experience by providing an intelligent guide to navigate multiple modules (jobs, self-employment, counseling, career guidance, etc.) through smart automation and conversational AI.

✨ Key Features

🤖 AI Chatbot for query resolution

🔍 Smart Navigation across PGRKAM modules

🌐 Multilingual Support (English, Punjabi, Hindi)

📱 Seamless Web & Mobile Integration

⚡ Automation-Driven User Experience

