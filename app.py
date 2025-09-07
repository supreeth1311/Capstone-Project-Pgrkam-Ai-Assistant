import streamlit as st
import openai
from googletrans import Translator
import pyttsx3

# Initialize APIs
openai.api_key = "YOUR_OPENAI_API_KEY"
translator = Translator()
engine = pyttsx3.init()

# UI Title
st.title("PGRKAM AI Assistant")

# Language selection
language = st.selectbox("Choose Language", ["English", "Hindi", "Punjabi"])

# User input
user_input = st.text_input("Enter your query:")

# Function to generate response
def generate_response(prompt, lang="English"):
    # Translate to English if necessary
    if lang != "English":
        prompt = translator.translate(prompt, dest='en').text
    
    # GPT API call
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    answer = response['choices'][0]['message']['content']
    
    # Translate back if necessary
    if lang != "English":
        answer = translator.translate(answer, dest='hi' if lang == "Hindi" else 'pa').text
    
    return answer

# Generate and display response
if user_input:
    answer = generate_response(user_input, language)
    st.text_area("Response", answer, height=200)
    
    # Text to speech
    if st.button("Listen"):
        engine.say(answer)
        engine.runAndWait()
