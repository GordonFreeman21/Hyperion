import streamlit as st
import os
import time
from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient

# --- 1. SETUP ---
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

st.set_page_config(page_title="HyperionX", page_icon="⚡", layout="wide")

# --- 2. CSS STYLING ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #E0E0E0; }
    .stTextInput > div > div > input { background-color: #1a1c24; color: #fff; border: 1px solid #333; }
    .stChatMessage { background-color: transparent; }
</style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚡ HyperionX")
    if not GROQ_API_KEY:
        st.error("❌ Missing GROQ_API_KEY")
        st.stop()
        
    # Status Check
    search_status = "✅ Online" if TAVILY_API_KEY else "⚠️ Offline"
    st.caption(f"Neural Search: {search_status}")

    if st.button("🗑️ Reset Chat"):
        st.session_state.messages = []
        st.rerun()

# --- 4. FUNCTIONS ---

def perform_search(query):
    """
    Uses Tavily to get real-time context.
    """
    try:
        tavily = TavilyClient(api_key=TAVILY_API_KEY)
        # Search for current status to identify the person
        response = tavily.search(query=f"{query} current status 2025", search_depth="basic", max_results=3)
        
        context_parts = []
        for result in response.get('results', []):
            context_parts.append(f"- {result['title']}: {result['content']}")
        return "\n\n".join(context_parts)
    except Exception:
        return None

def should_we_search(prompt):
    """
    Keyword Router.
    """
    keywords = ["who", "what", "when", "2024", "2025", "price", "chancellor", "wer", "wie", "was", "wann", "aktuell", "kanzler", "alter", "alt", "old"]
    return any(k in prompt.lower() for k in keywords)

def clean_stream(stream):
    """
    Filters out technical garbage, returns pure text.
    """
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

# --- 5. MAIN APP ---

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Logic Loop
if prompt := st.chat_input("Input Command..."):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    client = Groq(api_key=GROQ_API_KEY)
    final_prompt = prompt
    
    # --- SEARCH & CONTEXT INJECTION ---
    if TAVILY_API_KEY and should_we_search(prompt):
        with st.status("Accessing Real-Time Data...", expanded=False) as status:
            search_data = perform_search(prompt)
            
            if search_data:
                status.update(label="Data Acquired", state="complete")
                
                # --- THE FIX IS HERE ---
                # We changed the instruction to allow Hybrid Thinking (Search + Internal Knowledge)
                final_prompt = (
                    f"USER QUESTION: {prompt}\n\n"
                    f"--- REAL-TIME SEARCH RESULTS (2025) ---\n"
                    f"{search_data}\n"
                    f"---------------------------------------\n"
                    f"INSTRUCTION: \n"
                    f"1. Use the Search Results to determine WHO is being asked about or WHAT is the current situation.\n"
                    f"2. If the user asks for static facts (like Age, Birthdate, Height) that are missing from the search results, USE YOUR INTERNAL TRAINING DATA to fill in the gaps.\n"
                    f"3. Example: If search says 'Olaf Scholz is Chancellor' but doesn't say his age, YOU calculate his age based on his birthdate (1958)."
                )
            else:
                status.update(label="Search Failed (Using Memory)", state="error")

    # --- GENERATION ---
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"You are HyperionX. Current Date: {time.strftime('%Y-%m-%d')}. Answer concisely in the language of the user."},
                *st.session_state.messages[:-1],
                {"role": "user", "content": final_prompt}
            ],
            stream=True,
            temperature=0.5,
            presence_penalty=0.5
        )
        response_text = st.write_stream(clean_stream(stream))
        st.session_state.messages.append({"role": "assistant", "content": response_text})