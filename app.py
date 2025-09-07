import streamlit as st
from deep_translator import GoogleTranslator
import requests
import os

# -------------------------
# Load Gemini API key from Streamlit Secrets
# -------------------------
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="PGRKAM AI Assistant", layout="centered")
st.title("📘 PGRKAM AI Assistant")
st.write("Ask your questions and get answers powered by Gemini API!")

# Language selection
language = st.selectbox("Choose language:", ["English", "Hindi", "Punjabi"])

# User input
user_input = st.text_input("Type your question:")

# -------------------------
# Gemini API query function
# -------------------------
def query_gemini(prompt_text):
    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GEMINI_API_KEY}"
    }
    payload = {
        "contents": [
            {"parts": [{"text": prompt_text}]}
        ],
        "temperature": 0.7
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        result = response.json()
        text_output = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "")
        return text_output
    else:
        return f"Error: {response.status_code} - {response.text}"

# -------------------------
# Process the query
# -------------------------
if user_input:
    st.write("🔍 Processing your query...")

    # Translate input to English for API
    translated_input = GoogleTranslator(source='auto', target='en').translate(user_input)

    # Query Gemini API
    gemini_response = query_gemini(translated_input)

    # Translate back to selected language
    lang_map = {"English": "en", "Hindi": "hi", "Punjabi": "pa"}
    translated_response = GoogleTranslator(source='en', target=lang_map[language]).translate(gemini_response)

    # Show response
    st.success(translated_response)

# Footer
st.markdown("---")
st.caption("This chatbot is currently using Gemini API for text queries only.")
