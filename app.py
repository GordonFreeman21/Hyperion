import streamlit as st
import os
import time
import random
import groq
from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient

# --- 1. SETUP & KEYS ---
load_dotenv()

# Lade ALLE Groq Keys
GROQ_KEYS = [
    os.getenv("GROQ_API_KEY_1"),
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_3")
]
VALID_GROQ_KEYS = [k for k in GROQ_KEYS if k]

# Lade ALLE Tavily Keys
TAVILY_KEYS = [
    os.getenv("TAVILY_API_KEY_1"),
    os.getenv("TAVILY_API_KEY_2"),
    os.getenv("TAVILY_API_KEY_3")
]
VALID_TAVILY_KEYS = [k for k in TAVILY_KEYS if k]

st.set_page_config(page_title="HyperionX", page_icon="⚡", layout="wide")

# --- 2. CSS STYLING ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #E0E0E0; }
    .stTextInput > div > div > input { background-color: #1a1c24; color: #fff; border: 1px solid #333; }
    .stChatMessage { background-color: transparent; }
    .stStatusWidget { margin-bottom: 0px; }
</style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚡ HyperionX Ultimate")
    
    # Status Groq
    if VALID_GROQ_KEYS:
        st.success(f"🧠 Brain Power: {len(VALID_GROQ_KEYS)} Cores Active")
    else:
        st.error("❌ Keine Groq Keys gefunden!")

    # Status Tavily (Jetzt gefixt!)
    if VALID_TAVILY_KEYS:
        st.success(f"🌍 Neural Search: {len(VALID_TAVILY_KEYS)} Keys Active")
    else:
        st.warning("⚠️ Search Offline (Keys prüfen)")

    if st.button("🗑️ Reset Memory"):
        st.session_state.messages = []
        st.rerun()

# --- 4. INTELLIGENTE FUNKTIONEN ---

def get_intent(prompt):
    """Router mit Failover"""
    keys_shuffled = VALID_GROQ_KEYS.copy()
    random.shuffle(keys_shuffled)
    for key in keys_shuffled:
        try:
            client = Groq(api_key=key)
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "Classify: 'CHAT' for greeting/slang/jokes. 'SEARCH' for facts/news/weather/people. Output only 1 word."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0, max_tokens=5
            )
            return "SEARCH" in completion.choices[0].message.content.upper()
        except: continue
    return False

def perform_search(query):
    """Tavily Rotation (Gefixt für deine 3 Keys!)"""
    if not VALID_TAVILY_KEYS: return None
    
    keys_shuffled = VALID_TAVILY_KEYS.copy()
    random.shuffle(keys_shuffled)

    for key in keys_shuffled:
        try:
            tavily = TavilyClient(api_key=key)
            response = tavily.search(query=f"{query} current news 2025", search_depth="basic", max_results=3)
            parts = [f"- {r['title']}: {r['content']}" for r in response.get('results', [])]
            return "\n\n".join(parts)
        except:
            continue # Probiere nächsten Tavily Key
    return None

def clean_stream(stream):
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

def generate_response_with_failover(messages):
    """Groq Rotation"""
    keys_shuffled = VALID_GROQ_KEYS.copy()
    random.shuffle(keys_shuffled)
    for key in keys_shuffled:
        try:
            client = Groq(api_key=key)
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                stream=True,
                temperature=0.6,
                presence_penalty=0.4
            )
            return clean_stream(stream)
        except groq.RateLimitError: continue
        except Exception: continue
    return ["⚠️ SYSTEM ERROR: Alle Keys verbraucht."]

# --- 5. MAIN APP ---

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    final_prompt = prompt
    
    # Router
    should_search = get_intent(prompt) if VALID_GROQ_KEYS else False

    # Search
    if should_search and VALID_TAVILY_KEYS:
        with st.status("🌍 Checking Intelligence...", expanded=False) as status:
            search_data = perform_search(prompt)
            if search_data:
                status.update(label="Data Acquired", state="complete")
                final_prompt = (
                    f"USER: {prompt}\n\n"
                    f"SEARCH RESULTS (2025):\n{search_data}\n\n"
                    f"INSTRUCTION: Use results for facts. Use internal knowledge for ages/dates."
                )
            else:
                status.update(label="No Data found", state="error")

    # Generation
    with st.chat_message("assistant"):
        system_prompt = "You are HyperionX. Reply in the EXACT SAME language/dialect as the user."
        full_messages = [
            {"role": "system", "content": system_prompt},
            *st.session_state.messages[:-1],
            {"role": "user", "content": final_prompt}
        ]
        response_generator = generate_response_with_failover(full_messages)
        response_text = st.write_stream(response_generator)
        st.session_state.messages.append({"role": "assistant", "content": response_text})