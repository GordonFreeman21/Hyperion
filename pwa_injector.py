"""
PWA Injector for Streamlit
Injects manifest, service worker, and PWA meta tags into the Streamlit app.
"""

import streamlit as st
import streamlit.components.v1 as components


def inject_pwa_tags():
    """Inject PWA meta tags and service worker registration into the page."""
    
    pwa_html = """
    <script>
    (function() {
        // Prevent multiple injections
        if (window.__pwaInjected) return;
        window.__pwaInjected = true;
        
        // Wait for DOM to be ready
        function injectPWA() {
            const head = document.head || document.getElementsByTagName('head')[0];
            
            // Check if already injected
            if (document.querySelector('link[rel="manifest"]')) return;
            
            // Manifest link
            const manifestLink = document.createElement('link');
            manifestLink.rel = 'manifest';
            manifestLink.href = '/app/static/manifest.json';
            head.appendChild(manifestLink);
            
            // Theme color
            const themeColor = document.createElement('meta');
            themeColor.name = 'theme-color';
            themeColor.content = '#00FFB3';
            head.appendChild(themeColor);
            
            // Apple-specific meta tags
            const appleMeta = [
                { name: 'apple-mobile-web-app-capable', content: 'yes' },
                { name: 'apple-mobile-web-app-status-bar-style', content: 'black-translucent' },
                { name: 'apple-mobile-web-app-title', content: 'HyperionX' }
            ];
            
            appleMeta.forEach(meta => {
                const tag = document.createElement('meta');
                tag.name = meta.name;
                tag.content = meta.content;
                head.appendChild(tag);
            });
            
            // Apple touch icon
            const appleIcon = document.createElement('link');
            appleIcon.rel = 'apple-touch-icon';
            appleIcon.href = '/app/static/icon-192.png';
            head.appendChild(appleIcon);
            
            // MS tile color
            const msTile = document.createElement('meta');
            msTile.name = 'msapplication-TileColor';
            msTile.content = '#050A18';
            head.appendChild(msTile);
            
            console.log('[PWA] Meta tags injected');
        }
        
        // Register service worker
        function registerServiceWorker() {
            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.register('/app/static/sw.js', { scope: '/' })
                    .then(registration => {
                        console.log('[PWA] Service Worker registered:', registration.scope);
                        
                        // Check for updates
                        registration.addEventListener('updatefound', () => {
                            const newWorker = registration.installing;
                            newWorker.addEventListener('statechange', () => {
                                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                    // New content available
                                    showUpdateNotification();
                                }
                            });
                        });
                    })
                    .catch(err => {
                        console.error('[PWA] Service Worker registration failed:', err);
                    });
            }
        }
        
        // Show update notification
        function showUpdateNotification() {
            const notification = document.createElement('div');
            notification.id = 'pwa-update-notification';
            notification.innerHTML = `
                <style>
                    #pwa-update-notification {
                        position: fixed;
                        bottom: 100px;
                        left: 50%;
                        transform: translateX(-50%);
                        background: linear-gradient(135deg, rgba(77,163,255,0.95), rgba(0,255,179,0.90));
                        color: #061226;
                        padding: 16px 24px;
                        border-radius: 16px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.4);
                        z-index: 999999;
                        display: flex;
                        align-items: center;
                        gap: 16px;
                        font-family: 'Space Grotesk', system-ui, sans-serif;
                        font-weight: 600;
                        animation: slideUp 0.3s ease-out;
                    }
                    #pwa-update-notification button {
                        background: rgba(0,0,0,0.2);
                        border: none;
                        color: #061226;
                        padding: 8px 16px;
                        border-radius: 8px;
                        cursor: pointer;
                        font-weight: 700;
                        font-family: inherit;
                    }
                    @keyframes slideUp {
                        from { transform: translateX(-50%) translateY(100px); opacity: 0; }
                        to { transform: translateX(-50%) translateY(0); opacity: 1; }
                    }
                </style>
                <span>🚀 Update available!</span>
                <button onclick="location.reload()">Refresh</button>
                <button onclick="this.parentElement.remove()">Later</button>
            `;
            document.body.appendChild(notification);
        }
        
        // Install prompt handling
        let deferredPrompt = null;
        
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            showInstallButton();
        });
        
        function showInstallButton() {
            // Check if already installed
            if (window.matchMedia('(display-mode: standalone)').matches) return;
            
            // Create install button
            const installBtn = document.createElement('div');
            installBtn.id = 'pwa-install-btn';
            installBtn.innerHTML = `
                <style>
                    #pwa-install-btn {
                        position: fixed;
                        bottom: 100px;
                        right: 20px;
                        z-index: 999998;
                    }
                    #pwa-install-btn button {
                        background: linear-gradient(135deg, rgba(77,163,255,0.92), rgba(0,255,179,0.82));
                        color: #061226;
                        border: none;
                        padding: 14px 20px;
                        border-radius: 50px;
                        cursor: pointer;
                        font-weight: 800;
                        font-family: 'Space Grotesk', system-ui, sans-serif;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        transition: all 0.2s;
                    }
                    #pwa-install-btn button:hover {
                        transform: scale(1.05);
                    }
                    #pwa-install-btn .close {
                        position: absolute;
                        top: -8px;
                        right: -8px;
                        background: rgba(255,255,255,0.9);
                        border: none;
                        width: 24px;
                        height: 24px;
                        border-radius: 50%;
                        cursor: pointer;
                        font-size: 14px;
                        color: #333;
                    }
                </style>
                <button onclick="window.__installPWA()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    Install App
                </button>
                <button class="close" onclick="this.parentElement.remove()">×</button>
            `;
            document.body.appendChild(installBtn);
        }
        
        window.__installPWA = async function() {
            if (!deferredPrompt) return;
            
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            
            if (outcome === 'accepted') {
                console.log('[PWA] User accepted install prompt');
                document.getElementById('pwa-install-btn')?.remove();
            }
            
            deferredPrompt = null;
        };
        
        // Track install
        window.addEventListener('appinstalled', () => {
            console.log('[PWA] App installed');
            document.getElementById('pwa-install-btn')?.remove();
        });
        
        // Initialize
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                injectPWA();
                registerServiceWorker();
            });
        } else {
            injectPWA();
            registerServiceWorker();
        }
    })();
    </script>
    """
    
    components.html(pwa_html, height=0, width=0)


def inject_pwa_install_prompt():
    """Create a visible install prompt button in Streamlit."""
    
    st.markdown("""
    <script>
    (function() {
        // This runs in the Streamlit context
        if (window.matchMedia('(display-mode: standalone)').matches) {
            // Already installed
            return;
        }
    })();
    </script>
    """, unsafe_allow_html=True)