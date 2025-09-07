import streamlit as st
from googletrans import Translator
from google.cloud import speech
import os
from dotenv import load_dotenv
import requests
import tempfile

# -------------------------
# Load environment variables
# -------------------------
load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# -------------------------
# Initialize translator
# -------------------------
translator = Translator()

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="PGRKAM AI Assistant", layout="centered")
st.title("📘 PGRKAM AI Assistant")
st.write("A smart chatbot for job seekers. Supports text & voice queries!")

# Language selection
language = st.selectbox("Choose language:", ["English", "Hindi", "Punjabi"])

# Tabs for Text / Voice input
tab1, tab2 = st.tabs(["Text Query", "Voice Query"])

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
# Speech-to-Text function
# -------------------------
def speech_to_text(audio_file):
    client = speech.SpeechClient()
    audio_content = audio_file.read()

    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code="en-US"
    )

    response = client.recognize(config=config, audio=audio)
    if response.results:
        return response.results[0].alternatives[0].transcript
    else:
        return ""

# -------------------------
# Text Query Tab
# -------------------------
with tab1:
    user_input = st.text_input("Type your question:")
    if user_input:
        st.write("🔍 Processing your text query...")
        # Translate to English
        translated_input = translator.translate(user_input, dest='en').text
        # Get response from Gemini API
        gemini_response = query_gemini(translated_input)
        # Translate back to selected language
        lang_codes = {"English": "en", "Hindi": "hi", "Punjabi": "pa-IN"}
        translated_response = translator.translate(gemini_response, dest=lang_codes[language]).text
        st.success(translated_response)

# -------------------------
# Voice Query Tab
# -------------------------
with tab2:
    audio_file = st.file_uploader("Upload your voice query (WAV/FLAC format):", type=["wav", "flac"])
    if audio_file:
        st.write("🎙 Processing your voice query...")
        # Convert speech to text
        user_input = speech_to_text(audio_file)
        st.write(f"➡ Recognized Text: {user_input}")
        if user_input:
            # Translate to English for Gemini
            translated_input = translator.translate(user_input, dest='en').text
            # Query Gemini API
            gemini_response = query_gemini(translated_input)
            # Translate back to selected language
            lang_codes = {"English": "en", "Hindi": "hi", "Punjabi": "pa-IN"}
            translated_response = translator.translate(gemini_response, dest=lang_codes[language]).text
            st.success(translated_response)

# Footer
st.markdown("---")
st.caption("This chatbot is integrated with Gemini API and Speech-to-Text API for text & voice queries.")
