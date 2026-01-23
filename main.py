import os
import time
import random
import json
import re
import threading
import uuid
import html
from urllib.parse import urlparse

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient

# =========================
# 1) SETUP & KEYS
# =========================
load_dotenv()

def load_numbered_env_keys(prefix: str, max_n: int = 10):
    keys = []
    for i in range(1, max_n + 1):
        v = os.getenv(f"{prefix}{i}")
        if v:
            keys.append(v)
    return keys

VALID_GROQ_KEYS = load_numbered_env_keys("GROQ_API_KEY_", 10)
VALID_TAVILY_KEYS = load_numbered_env_keys("TAVILY_API_KEY_", 10)

# Assets
APP_ICON = "assets/hyperionx_icon.png"
ASSISTANT_AVATAR = "assets/assistant.png"
USER_AVATAR = "assets/user.png"

st.set_page_config(
    page_title="HyperionX",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================
# 2) PWA INJECTION
# =========================
def inject_pwa():
    """Inject PWA manifest, service worker, and meta tags."""
    
    pwa_script = """
    <script>
    (function() {
        // Prevent multiple injections
        if (window.__pwaInjected) return;
        window.__pwaInjected = true;
        
        function injectPWAMeta() {
            const head = document.head || document.getElementsByTagName('head')[0];
            
            // Check if already injected
            if (document.querySelector('link[rel="manifest"]')) return;
            
            // Manifest link
            const manifestLink = document.createElement('link');
            manifestLink.rel = 'manifest';
            manifestLink.href = 'static/manifest.json';
            head.appendChild(manifestLink);
            
            // Theme color
            let themeColor = document.querySelector('meta[name="theme-color"]');
            if (!themeColor) {
                themeColor = document.createElement('meta');
                themeColor.name = 'theme-color';
                head.appendChild(themeColor);
            }
            themeColor.content = '#00FFA3';
            
            // Apple-specific meta tags
            const appleMeta = [
                { name: 'apple-mobile-web-app-capable', content: 'yes' },
                { name: 'apple-mobile-web-app-status-bar-style', content: 'black-translucent' },
                { name: 'apple-mobile-web-app-title', content: 'HyperionX' },
                { name: 'mobile-web-app-capable', content: 'yes' }
            ];
            
            appleMeta.forEach(meta => {
                if (!document.querySelector(`meta[name="${meta.name}"]`)) {
                    const tag = document.createElement('meta');
                    tag.name = meta.name;
                    tag.content = meta.content;
                    head.appendChild(tag);
                }
            });
            
            // Apple touch icons
            const appleSizes = [180, 152, 144, 120, 114, 76, 72, 60, 57];
            appleSizes.forEach(size => {
                const link = document.createElement('link');
                link.rel = 'apple-touch-icon';
                link.sizes = `${size}x${size}`;
                link.href = `static/icon-${size >= 192 ? 192 : size >= 144 ? 144 : 72}.png`;
                head.appendChild(link);
            });
            
            // Splash screens for iOS
            const splashLink = document.createElement('link');
            splashLink.rel = 'apple-touch-startup-image';
            splashLink.href = 'static/icon-512.png';
            head.appendChild(splashLink);
            
            // MS tile
            const msTile = document.createElement('meta');
            msTile.name = 'msapplication-TileColor';
            msTile.content = '#050505';
            head.appendChild(msTile);
            
            const msTileImage = document.createElement('meta');
            msTileImage.name = 'msapplication-TileImage';
            msTileImage.content = 'static/icon-144.png';
            head.appendChild(msTileImage);
            
            console.log('[PWA] Meta tags injected');
        }
        
        // Register service worker
        function registerServiceWorker() {
            if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                    navigator.serviceWorker.register('static/sw.js', { scope: '/' })
                        .then(function(registration) {
                            console.log('[PWA] ServiceWorker registered:', registration.scope);
                            
                            // Check for updates periodically
                            setInterval(() => {
                                registration.update();
                            }, 60000); // Check every minute
                            
                            // Handle updates
                            registration.addEventListener('updatefound', () => {
                                const newWorker = registration.installing;
                                newWorker.addEventListener('statechange', () => {
                                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                        showUpdateNotification();
                                    }
                                });
                            });
                        })
                        .catch(function(err) {
                            console.log('[PWA] ServiceWorker registration failed:', err);
                        });
                });
            }
        }
        
        // Show update notification
        function showUpdateNotification() {
            const existing = document.getElementById('pwa-update-toast');
            if (existing) existing.remove();
            
            const toast = document.createElement('div');
            toast.id = 'pwa-update-toast';
            toast.innerHTML = `
                <div style="
                    position: fixed;
                    bottom: 100px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: rgba(10, 10, 10, 0.95);
                    border: 1px solid #00FFA3;
                    color: #fff;
                    padding: 16px 24px;
                    border-radius: 12px;
                    box-shadow: 0 0 20px rgba(0, 255, 163, 0.2);
                    z-index: 999999;
                    display: flex;
                    align-items: center;
                    gap: 16px;
                    font-family: 'Space Grotesk', sans-serif;
                    animation: slideUp 0.3s ease;
                ">
                    <span style="color: #00FFA3;">⚡ Update Ready</span>
                    <button onclick="location.reload()" style="
                        background: #00FFA3;
                        border: none;
                        color: #000;
                        padding: 6px 14px;
                        border-radius: 6px;
                        font-weight: bold;
                        cursor: pointer;
                    ">RELOAD</button>
                    <button onclick="this.parentElement.parentElement.remove()" style="
                        background: transparent;
                        border: none;
                        color: #666;
                        cursor: pointer;
                        font-size: 18px;
                    ">×</button>
                </div>
            `;
            document.body.appendChild(toast);
        }
        
        // Install prompt
        let deferredPrompt = null;
        
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            if (window.matchMedia('(display-mode: standalone)').matches) return;
            setTimeout(showInstallPrompt, 3000);
        });
        
        function showInstallPrompt() {
            const existing = document.getElementById('pwa-install-prompt');
            if (existing) existing.remove();
            
            const prompt = document.createElement('div');
            prompt.id = 'pwa-install-prompt';
            prompt.innerHTML = `
                <div style="
                    position: fixed;
                    bottom: 90px;
                    right: 20px;
                    z-index: 999998;
                    animation: fadeIn 0.5s ease;
                ">
                    <button id="pwa-install-btn" style="
                        background: rgba(5, 5, 5, 0.9);
                        border: 1px solid #00FFA3;
                        color: #00FFA3;
                        padding: 12px 20px;
                        border-radius: 8px;
                        cursor: pointer;
                        font-family: 'Space Grotesk', sans-serif;
                        font-weight: bold;
                        box-shadow: 0 0 15px rgba(0,255,163,0.15);
                        display: flex;
                        align-items: center;
                        gap: 10px;
                        backdrop-filter: blur(10px);
                    ">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="7 10 12 15 17 10"/>
                            <line x1="12" y1="15" x2="12" y2="3"/>
                        </svg>
                        INSTALL PWA
                    </button>
                    <button onclick="this.parentElement.parentElement.remove(); localStorage.setItem('pwa-dismissed', Date.now());" style="
                        position: absolute;
                        top: -8px;
                        right: -8px;
                        background: #00FFA3;
                        border: none;
                        width: 20px;
                        height: 20px;
                        border-radius: 50%;
                        cursor: pointer;
                        font-size: 12px;
                        color: #000;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    ">×</button>
                </div>
            `;
            
            const dismissed = localStorage.getItem('pwa-dismissed');
            if (dismissed && Date.now() - parseInt(dismissed) < 86400000) return;
            
            document.body.appendChild(prompt);
            
            document.getElementById('pwa-install-btn').addEventListener('click', async () => {
                if (!deferredPrompt) return;
                deferredPrompt.prompt();
                const { outcome } = await deferredPrompt.userChoice;
                if (outcome === 'accepted') document.getElementById('pwa-install-prompt')?.remove();
                deferredPrompt = null;
            });
        }
        
        // Initialize
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                injectPWAMeta();
                registerServiceWorker();
            });
        } else {
            injectPWAMeta();
            registerServiceWorker();
        }
    })();
    </script>
    """
    
    components.html(pwa_script, height=0, width=0)


# Inject PWA immediately after page config
# Inject PWA immediately after page config
inject_pwa()

import base64

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def get_img_with_href(local_img_path):
    img_format = os.path.splitext(local_img_path)[-1].replace('.', '')
    bin_str = get_base64_of_bin_file(local_img_path)
    return f"data:image/{img_format};base64,{bin_str}"

try:
    bg_img = get_img_with_href("assets/chatai.png")
except Exception:
    bg_img = ""  # Fallback if missing


# =========================
# 3) SESSION STATE
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []

# Handle URL params (for PWA shortcuts like "New Chat")
query_params = st.query_params
if query_params.get("action") == "new":
    st.session_state.messages = []
    st.query_params.clear()

# =========================
# 4) PREMIUM UI CSS + PWA ENHANCEMENTS
# =========================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Inter:wght@400;600;800&display=swap');

:root {
  --bg-deep: #050505;
  --bg-card: #0F0F0F;
  --bg-surface: #141414;
  --neon: #00FFA3;
  --neon-dim: rgba(0, 255, 163, 0.15);
  --text-main: #E0E0E0;
  --text-sub: #A0A0A0;
  --border: #2A2A2A;
  --accent-blue: #00CCFF;
}

/* App basics */
.stApp {
  background-color: var(--bg-deep);
  background-image: 
    linear-gradient(rgba(5, 5, 5, 0.85), rgba(5, 5, 5, 0.95)),
    url("__BG_IMG__");
  background-size: cover;
  background-position: center;
  background-attachment: fixed;
  color: var(--text-main);
  font-family: 'Inter', sans-serif;
}

/* Header / Hero */
.hx-header {
  padding: 1.5rem 0;
  border-bottom: 1px solid var(--border);
  background: rgba(5, 5, 5, 0.8);
  backdrop-filter: blur(12px);
  margin-bottom: 2rem;
  position: sticky;
  top: 0;
  z-index: 100;
}
.hx-logo {
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700;
  font-size: 1.8rem;
  letter-spacing: -0.04em;
  background: linear-gradient(135deg, #fff 0%, #aaa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hx-badge {
    font-size: 0.7rem; 
    padding: 4px 8px; 
    border-radius: 4px; 
    font-weight: 700; 
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-left: 8px;
    vertical-align: middle;
}
.hx-badge-chill {
    background: rgba(0, 255, 163, 0.1); color: var(--neon); border: 1px solid rgba(0, 255, 163, 0.3);
}
.hx-badge-pro {
    background: rgba(0, 204, 255, 0.1); color: var(--accent-blue); border: 1px solid rgba(0, 204, 255, 0.3);
}

/* Chat Input */
.stChatInput > div {
  background: rgba(20, 20, 20, 0.6) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  transition: all 0.2s ease;
}
.stChatInput > div:focus-within {
  border-color: var(--neon) !important;
  box-shadow: 0 0 20px var(--neon-dim) !important;
}
.stChatInput input {
    color: var(--text-main) !important;
}

/* Chat Messages */
div[data-testid="stChatMessage"] {
  background: transparent !important;
  border: none !important;
  padding: 1.5rem 0 !important;
}

div[data-testid="stChatMessage"] div[data-testid="stMarkdownContainer"] {
    font-family: 'Inter', sans-serif;
    line-height: 1.6;
    font-size: 1rem;
}

/* User Bubble override */
div[data-testid="stChatMessage"][data-testid="user"] {
    background: rgba(255,255,255, 0.03) !important;
    border-radius: 12px;
    padding: 1rem 1.5rem !important;
}

/* Buttons */
.stButton button {
    background: var(--bg-surface) !important;
    color: var(--text-main) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
.stButton button:hover {
    border-color: var(--text-sub) !important;
    background: var(--bg-card) !important;
}
/* Deep Nuke Button specific */
.deep-nuke-btn button {
    color: #FF4B4B !important;
    border-color: rgba(255, 75, 75, 0.3) !important;
}
.deep-nuke-btn button:hover {
    background: rgba(255, 75, 75, 0.1) !important;
    border-color: #FF4B4B !important;
}

/* Expander & Cards */
div[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

.source-card {
    background: var(--bg-surface);
    border-left: 3px solid var(--neon);
    padding: 0.8rem 1rem;
    border-radius: 4px;
    margin-bottom: 0.8rem;
    transition: transform 0.2s;
}
.source-card:hover {
    transform: translateX(4px);
    background: #1A1A1A;
}
.source-card a {
    color: var(--text-main);
    text-decoration: none;
    font-weight: 700;
}
.source-meta {
    font-size: 0.85rem;
    color: var(--text-sub);
    margin-top: 4px;
}
mark.hl {
    background: var(--neon-dim);
    color: var(--text-main);
    padding: 0 4px;
    border-radius: 2px;
}

/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 6px;
  background: var(--bg-deep);
}
::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 3px;
}

/* Mobile adjustments */
@media (max-width: 768px) {
  .hx-header { padding: 1rem 0; }
  .hx-logo { font-size: 1.4rem; }
}
</style>

<!-- Offline Banner -->
<div id="offline-banner" class="offline-banner">
  ⚡ You're offline. Reconnect to use all features.
</div>

<script>
(function() {
  const banner = document.getElementById('offline-banner');
  
  function updateOnlineStatus() {
    if (!navigator.onLine) {
      banner.classList.add('visible');
    } else {
      banner.classList.remove('visible');
    }
  }
  
  window.addEventListener('online', updateOnlineStatus);
  window.addEventListener('offline', updateOnlineStatus);
  
  // Initial check
  updateOnlineStatus();
})();
</script>
""" .replace("__BG_IMG__", bg_img),
    unsafe_allow_html=True
)

# =========================
# 5) KEY MANAGER
# =========================
class KeyManager:
    def __init__(self, keys, cooldown_seconds=25):
        self.keys = [k for k in keys if k]
        self.cooldown_seconds = cooldown_seconds
        self.lock = threading.Lock()
        self.inflight = {k: 0 for k in self.keys}
        self.cooldown_until = {k: 0.0 for k in self.keys}

    def acquire(self):
        with self.lock:
            now = time.time()
            available = [k for k in self.keys if self.cooldown_until[k] <= now]
            if not available:
                k = min(self.keys, key=lambda x: self.cooldown_until[x])
                self.inflight[k] += 1
                return k
            k = min(available, key=lambda x: self.inflight[x])
            self.inflight[k] += 1
            return k

    def release(self, key, ok=True):
        with self.lock:
            if key in self.inflight and self.inflight[key] > 0:
                self.inflight[key] -= 1
            if not ok and key in self.cooldown_until:
                self.cooldown_until[key] = time.time() + self.cooldown_seconds

@st.cache_resource
def groq_pool():
    return KeyManager(VALID_GROQ_KEYS, cooldown_seconds=25)

# =========================
# 6) SEARCH / ROUTING HELPERS
# =========================
EXCLUDE_DOMAINS = {
    "instagram.com", "tiktok.com", "facebook.com", "x.com", "twitter.com",
    "pinterest.com", "reddit.com"
}

OFFICIAL_HINT = (
    "site:bundesregierung.de OR site:bundeskanzler.de OR site:bundestag.de OR site:destatis.de "
    "OR site:ecb.europa.eu OR site:bundesbank.de OR site:europa.eu"
)

def new_msg_id() -> str:
    return uuid.uuid4().hex[:10]

def host_of(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""

def is_excluded(url: str) -> bool:
    h = host_of(url)
    return any(d in h for d in EXCLUDE_DOMAINS)

def force_search(prompt: str) -> bool:
    p = prompt.lower()
    politics = [
        "politik","regierung","bundestag","parlament","gesetz","verordnung","wahl","umfrage",
        "koalition","minister","kanzler","cdu","spd","afd","grüne","fdp",
        "politics","government","election","poll","parliament","bill","law",
        "ukraine","russland","russia","israel","gaza","un","nato","eu",
    ]
    economics = [
        "wirtschaft","inflation","zinsen","ezb","fed","gdp","bip","arbeitsmarkt","rezession","konjunktur",
        "börse","aktie","aktien","dax","dow","nasdaq","s&p",
        "bitcoin","krypto","crypto","wechselkurs","eur/usd","oil","brent",
        "economy","interest rate","stocks","market","bond","yield",
    ]
    changeable = [
        "preis","kosten","tarif","zins","rate","kurs",
        "heute","aktuell","stand","news","latest","today","breaking",
        "forecast","prognose",
    ]
    return any(t in p for t in (politics + economics + changeable))

def parse_json_loose(text: str):
    t = (text or "").strip()
    if t.startswith("```"):
        parts = t.split("```")
        candidates = [p.strip() for p in parts if "{" in p and "}" in p]
        if candidates:
            t = max(candidates, key=len)
        t = re.sub(r"^\s*json\s*", "", t.strip(), flags=re.IGNORECASE)
    m = re.search(r"\{.*\}", t, flags=re.DOTALL)
    if m:
        t = m.group(0)
    return json.loads(t)

def groq_json_call(system: str, user: str, max_tokens=160, temperature=0.0, tries=3):
    if not VALID_GROQ_KEYS:
        raise RuntimeError("No GROQ keys configured.")

    pool = groq_pool()
    last_err = None
    for _ in range(max(1, min(tries, len(pool.keys)))):
        key = pool.acquire()
        ok = True
        try:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return parse_json_loose(resp.choices[0].message.content)
        except Exception as e:
            ok = False
            last_err = e
        finally:
            pool.release(key, ok=ok)
    raise last_err or RuntimeError("Router JSON call failed")

def llm_should_browse_and_rewrite(prompt: str, recent_messages=None):
    recent_messages = recent_messages or []
    system = (
        "You are a routing classifier. Decide if web search is needed.\n"
        "Search is needed for current events, politics, economics, markets, live prices, time-sensitive facts.\n"
        "If search is needed, rewrite into a short high-signal web search query.\n"
        'Return ONLY JSON: {"should_search": true/false, "query": "..."}'
    )
    ctx = ""
    for m in recent_messages[-3:]:
        if m.get("role") in ("user", "assistant"):
            ctx += f"{m['role'].upper()}: {m.get('content','')}\n"
    data = groq_json_call(system, f"Context:\n{ctx}\nUser:\n{prompt}", max_tokens=160, temperature=0.0)
    return bool(data.get("should_search", False)), (data.get("query") or prompt).strip()

def llm_rewrite_query(prompt: str):
    system = (
        "Rewrite the user's request into a short, high-signal web search query. "
        "Remove filler words; add disambiguating keywords and time hints if useful.\n"
        'Return ONLY JSON: {"query": "..."}'
    )
    data = groq_json_call(system, prompt, max_tokens=120, temperature=0.0)
    return (data.get("query") or prompt).strip()

def llm_improve_query(prompt: str, previous_query: str, results: list):
    system = (
        "You improve web search queries.\n"
        "Given the question, the previous query, and weak snippets, propose ONE better query.\n"
        'Return ONLY JSON: {"query": "..."}'
    )
    snippets = "\n".join(
        [
            f"- {r.get('title','')}\n  URL: {r.get('url','')}\n  Snippet: {(r.get('content','') or '')[:220].replace(chr(10),' ')}"
            for r in (results or [])
        ]
    )
    user = f"Question: {prompt}\nPrevious query: {previous_query}\nSnippets:\n{snippets}"
    data = groq_json_call(system, user, max_tokens=140, temperature=0.2)
    return (data.get("query") or previous_query).strip()

def dedup_results(results: list):
    seen = set()
    out = []
    for r in results or []:
        url = (r.get("url") or "").strip()
        k = url.lower() if url else (r.get("title") or "").strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out

def results_look_weak(results: list) -> bool:
    if not results or len(results) < 2:
        return True
    total_chars = sum(len((r.get("content") or "").strip()) for r in results)
    return total_chars < 900

def looks_low_trust(results: list) -> bool:
    if not results:
        return True
    good = 0
    for r in results:
        h = host_of(r.get("url") or "")
        if any(x in h for x in [
            "bundeskanzler.de", "bundesregierung.de", "bundestag.de",
            "destatis.de", "bundesbank.de", "ecb.europa.eu", "europa.eu", ".gov"
        ]):
            good += 1
    return good == 0

@st.cache_data(ttl=300)
def perform_search_cached(query: str, depth: str = "basic"):
    if not VALID_TAVILY_KEYS:
        return []

    keys = VALID_TAVILY_KEYS[:]
    random.shuffle(keys)

    for key in keys:
        try:
            tavily = TavilyClient(api_key=key)
            try:
                resp = tavily.search(
                    query=query,
                    search_depth=depth,
                    max_results=6,
                    include_answer=False,
                    exclude_domains=list(EXCLUDE_DOMAINS),
                )
            except TypeError:
                resp = tavily.search(query=query, search_depth=depth, max_results=6, include_answer=False)

            results = resp.get("results", []) or []
            results = [r for r in results if not is_excluded(r.get("url") or "")]
            return results
        except Exception:
            continue
    return []

def sources_for_llm(results: list) -> str:
    blocks = []
    for i, r in enumerate(results or [], start=1):
        title = (r.get("title") or f"Source {i}").strip()
        url = (r.get("url") or "").strip()
        content = re.sub(r"\s+", " ", (r.get("content") or "").strip())
        if len(content) > 650:
            content = content[:650] + "..."
        blocks.append(f"[{i}] {title}\nURL: {url}\nSnippet: {content}")
    return "\n\n".join(blocks)

# =========================
# 7) CITATIONS (Markdown-safe)
# =========================
CITATION_RE = re.compile(r"\[(\d{1,3})\]")

def linkify_citations_preserve_code(md_text: str, msg_id: str, max_n: int) -> str:
    parts = re.split(r"(```.*?```)", md_text, flags=re.DOTALL)
    out = []
    for part in parts:
        if part.startswith("```"):
            out.append(part)
            continue

        def repl(m):
            n = int(m.group(1))
            if 1 <= n <= max_n:
                return f"[[{n}]](#src-{msg_id}-{n})"
            return m.group(0)

        out.append(CITATION_RE.sub(repl, part))
    return "".join(out)

def pick_best_sentence(snippet: str, query: str) -> str:
    if not snippet or not query:
        return ""
    qwords = [w.lower() for w in re.findall(r"[A-Za-zÄÖÜäöüß0-9]{4,}", query)]
    qset = set(qwords)
    sentences = re.split(r"(?<=[.!?])\s+", snippet.strip())
    if len(sentences) <= 1:
        return sentences[0] if sentences else snippet
    best, best_score = sentences[0], -1
    for s in sentences:
        swords = set(w.lower() for w in re.findall(r"[A-Za-zÄÖÜäöüß0-9]{4,}", s))
        score = len(swords & qset)
        if score > best_score:
            best_score = score
            best = s
    return best

def highlight_snippet_html(snippet: str, query: str) -> str:
    if not snippet:
        return ""
    best = pick_best_sentence(snippet, query)
    esc = html.escape(snippet)
    best_esc = html.escape(best) if best else ""
    if best_esc and best_esc in esc:
        return esc.replace(best_esc, f"<mark class='hl'>{best_esc}</mark>", 1)
    return esc

def render_sources_cards(results: list, msg_id: str, highlight_query: str = ""):
    if not results:
        return
    with st.expander("📚 Sources", expanded=False):
        for i, r in enumerate(results, start=1):
            title = html.escape((r.get("title") or f"Source {i}").strip())
            url = (r.get("url") or "").strip()
            url_esc = html.escape(url)

            content = re.sub(r"\s+", " ", (r.get("content") or "").strip())
            if len(content) > 520:
                content = content[:520] + "..."
            content_html = highlight_snippet_html(content, highlight_query)

            st.markdown(
                f"""
<div id="src-{msg_id}-{i}" class="source-card source-anchor">
  <div><strong>[{i}]</strong> <a href="{url_esc}" target="_blank" rel="noopener noreferrer">{title}</a></div>
  <div class="source-meta">{content_html}</div>
  <div class="source-meta" style="opacity:0.7; font-size: 0.85rem; margin-top: 4px;">{url_esc}</div>
  <div class="source-meta" style="margin-top:8px;">
    <a href="#ans-{msg_id}" style="color: var(--neon); font-weight: 600;">↑ Back to answer</a>
  </div>
</div>
""",
                unsafe_allow_html=True
            )

# =========================
# 8) GROQ STREAM
# =========================
def generate_response_stream(messages):
    if not VALID_GROQ_KEYS:
        yield "⚠️ No GROQ API keys configured. Please add your API keys to the .env file."
        return

    pool = groq_pool()
    key = pool.acquire()
    ok = True
    try:
        client = Groq(api_key=key)
        stream = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            stream=True,
            temperature=0.4,
            max_tokens=1024,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        ok = False
        yield f"⚠️ Model error / rate limit. Please try again. ({str(e)[:50]})"
    finally:
        pool.release(key, ok=ok)

# =========================
# 9) HEADER UI
# =========================
with st.container(border=False):
    # Header grid
    c1, c2, c3 = st.columns([2.5, 1, 0.8], vertical_alignment="center")
    
    with c1:
        # Initial Vibe State
        if "vibe_check" not in st.session_state:
            st.session_state.vibe_check = True

        tag = "CHILL UNFILTERED" if st.session_state.vibe_check else "RESEARCH PRO"
        tag_class = "hx-badge-chill" if st.session_state.vibe_check else "hx-badge-pro"
        
        st.markdown(f"""
        <div class="hx-logo">
            HYPERIONX <span class="hx-badge {tag_class}">{tag}</span>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        # Vibe Switch
        st.session_state.vibe_check = st.toggle("🔥 Chill Mode", value=True)

    with c3:
        # Deep Nuke
        st.markdown('<div class="deep-nuke-btn">', unsafe_allow_html=True)
        if st.button("☢️ RESET"):
            st.session_state.messages = []
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# =========================
# 10) RENDER CHAT HISTORY
# =========================
def render_assistant_markdown(text: str, msg_id: str, sources_count: int):
    md = linkify_citations_preserve_code(text, msg_id=msg_id, max_n=sources_count)
    st.markdown(f'<div id="ans-{msg_id}" class="answer-anchor"></div>', unsafe_allow_html=True)
    st.markdown(md)

for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            msg_id = msg.get("id") or "legacy"
            sources = msg.get("sources") or []
            render_assistant_markdown(msg.get("content", ""), msg_id, len(sources))
            if sources:
                render_sources_cards(sources, msg_id=msg_id, highlight_query=(msg.get("query") or ""))

# =========================
# 11) CHAT INPUT → SEARCH → ANSWER
# =========================
if prompt := st.chat_input("Ask HyperionX anything…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)

    sources = []
    must_search = force_search(prompt)

    # Decide browse + query
    try:
        if must_search:
            should_search = True
            search_query = llm_rewrite_query(prompt)
            search_query = f"{search_query} ({OFFICIAL_HINT})"
        else:
            should_search, search_query = llm_should_browse_and_rewrite(prompt, st.session_state.messages)
    except Exception:
        should_search = must_search
        search_query = prompt

    # Search + refine
    if should_search and VALID_TAVILY_KEYS:
        with st.status("🔍 Scanning sources…", expanded=False) as status:
            depth = "advanced" if must_search else "basic"
            status.update(label=f"🔍 Searching: {search_query[:60]}{'...' if len(search_query) > 60 else ''}", state="running")
            r1 = dedup_results(perform_search_cached(search_query, depth=depth))

            if results_look_weak(r1) or looks_low_trust(r1):
                try:
                    improved = llm_improve_query(prompt, search_query, r1)
                except Exception:
                    improved = search_query
                if must_search:
                    improved = f"{improved} ({OFFICIAL_HINT})"

                status.update(label=f"🔄 Refining: {improved[:60]}{'...' if len(improved) > 60 else ''}", state="running")
                r2 = dedup_results(perform_search_cached(improved, depth="advanced" if must_search else "basic"))
                sources = dedup_results((r1 or []) + (r2 or []))
            else:
                sources = r1

            status.update(
                label=f"✅ Found {len(sources)} sources" if sources else "⚠️ No sources found",
                state="complete" if sources else "error",
            )

    # System prompt logic based on vibe
    vibe_chill = st.session_state.get("vibe_check", True)
    
    if sources:
        if vibe_chill:
            system_text = (
                "You are HyperionX, a chill, uncensored, and high-tech AI.\n"
                "You speak directly and casually (like a tech-savvy friend).\n"
                "WEB SOURCES are provided. Use them to answer truthfullly.\n"
                "Cite them as [n].\n"
                "Don't give me moral lectures. Just answer the question based on the sources.\n"
                f"Current time: {time.strftime('%d %B %Y, %H:%M')}"
            )
        else:
            system_text = (
                "You are HyperionX, an advanced Research AI.\n"
                "WEB SOURCES are provided. You MUST answer directly and cite using [n].\n"
                "If sources conflict, explain the conflict.\n"
                "Maintain a professional, objective tone.\n"
                f"Current time: {time.strftime('%d %B %Y, %H:%M')}"
            )
    else:
        if vibe_chill:
            system_text = (
                "You are HyperionX. Chill, direct, and uncensored.\n"
                "Answer the user's question without fluff.\n"
                f"Current time: {time.strftime('%d %B %Y, %H:%M')}"
            )
        else:
            system_text = (
                "You are HyperionX, an advanced Research AI. Be concise and accurate.\n"
                "If you are uncertain, say so.\n"
                f"Current time: {time.strftime('%d %B %Y, %H:%M')}"
            )

    system_msg = {"role": "system", "content": system_text}

    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-6:]]
    messages_to_send = [system_msg] + history

    if sources:
        messages_to_send.append(
            {"role": "system", "content": "WEB SOURCES (cite as [1], [2], ...):\n\n" + sources_for_llm(sources)}
        )

    # Stream: show plain text while streaming, then render final markdown + citation links
    msg_id = new_msg_id()
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        st.markdown(f'<div id="ans-{msg_id}" class="answer-anchor"></div>', unsafe_allow_html=True)

        placeholder = st.empty()
        chunks = []

        for t in generate_response_stream(messages_to_send):
            chunks.append(t)
            placeholder.write("".join(chunks))

        full_response = "".join(chunks)

        md_final = linkify_citations_preserve_code(full_response, msg_id=msg_id, max_n=len(sources))
        placeholder.markdown(md_final)

        if sources:
            render_sources_cards(sources, msg_id=msg_id, highlight_query=prompt)

    st.session_state.messages.append(
        {"role": "assistant", "content": full_response, "sources": sources or [], "id": msg_id, "query": prompt}
    )

# =========================
# 12) FOOTER / PWA HINTS
# =========================
st.markdown("""
<div style="
    text-align: center;
    padding: 20px 0 10px;
    color: rgba(234, 242, 255, 0.4);
    font-size: 12px;
">
    <span id="pwa-status"></span>
</div>

<script>
(function() {
    const statusEl = document.getElementById('pwa-status');
    if (window.matchMedia('(display-mode: standalone)').matches) {
        statusEl.innerHTML = '⚡ Running as installed app';
    } else if ('serviceWorker' in navigator) {
        statusEl.innerHTML = '💡 Tip: Install this app for the best experience';
    }
})();
</script>
""", unsafe_allow_html=True)