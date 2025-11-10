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
