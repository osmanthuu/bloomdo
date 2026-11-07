import os
import threading
import time
import requests
import streamlit as st
import streamlit.components.v1 as components

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Pastel Blooms To-Do 🌸",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide Streamlit default chrome/margins for an app feel
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding-top: 0.5rem;
        padding-bottom: 0rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
        max-width: 100%;
    }
</style>
""", unsafe_allow_html=True)

FLASK_PORT = 5005

def run_flask():
    from app import app
    app.run(host='127.0.0.1', port=FLASK_PORT, debug=False, use_reloader=False)

# Start Flask backend in background thread if not already running
@st.cache_resource
def ensure_flask_running():
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    # Wait until Flask is responding
    max_retries = 25
    for _ in range(max_retries):
        try:
            r = requests.get(f"http://127.0.0.1:{FLASK_PORT}/", timeout=1)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.2)
    return True

ensure_flask_running()

# Embed the complete cute pastel app via full-height iframe
app_url = f"http://127.0.0.1:{FLASK_PORT}"

components.iframe(src=app_url, height=920, scrolling=True)

st.markdown("""
<div style="text-align: center; padding: 10px 0; font-family: 'Quicksand', sans-serif; color: #ec4899; font-size: 13px;">
  🌸 <b>Pastel Blooms To-Do</b> &bull; Built with Flask & Streamlit &bull; 
  <a href="https://github.com" target="_blank" style="color: #ec4899; text-decoration: underline;">Deploy on Streamlit Community Cloud</a>
</div>
""", unsafe_allow_html=True)
