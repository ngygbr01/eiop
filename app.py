import os
import sys
import json
import time 
from flask import Flask, render_template, jsonify, request
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# --- KONFIGURÁCIÓ ---
ADMIN_USER = os.environ.get("ADMIN_USERNAME")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD")
LOGIN_DATA_DIR = "login_data"

if not os.path.exists(LOGIN_DATA_DIR):
    os.makedirs(LOGIN_DATA_DIR)

# --- RENDSZEREK DEFINÍCIÓJA (Bővíthető) ---
# Itt adhatsz hozzá új shopokat később
SYSTEMS = {
    "szvg": {
        "url": "https://szvgtoolsshop.hu/administrator/",
        "state_file": os.path.join(LOGIN_DATA_DIR, "szvg_state.json")
    },
    "ptd": {
        "url": "https://ptdbolt.hu/administrator/",
        "state_file": os.path.join(LOGIN_DATA_DIR, "ptd_state.json")
    }
}

if not ADMIN_USER or not ADMIN_PASS:
    print("⚠️ FIGYELEM: Nincs beállítva az ADMIN_USERNAME vagy ADMIN_PASSWORD a .env fájlban!")

# --- EGYSÉGES LOGIN LOGIKA ---
def run_login_logic(username, password, system_key):
    # Kikeressük a configból a megfelelő URL-t és fájlt
    config = SYSTEMS.get(system_key)
    if not config:
        return {"status": "error", "message": "Ismeretlen rendszer!"}
    
    base_url = config["url"]
    state_file = config["state_file"]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True) # headless=True a háttérben futáshoz
            context = None
            
            # 1. Meglévő session ellenőrzése
            if os.path.exists(state_file):
                print(f"\n[{system_key.upper()}] Meglévő session ellenőrzése...")
                try:
                    context = browser.new_context(storage_state=state_file)
                    page = context.new_page()
                    page.goto(base_url, timeout=15000)
                    
                    if page.is_visible("input[name='username']"):
                        print(f"[{system_key.upper()}] Session lejárt.")
                        page.close(); context.close(); context = None
                    else:
                        print(f" [{system_key.upper()}] Session érvényes.")
                        page.close(); browser.close()
                        return {"status": "success", "message": f"{system_key.upper()}: Kapcsolat aktív."}
                except:
                    if context: context.close()

            # 2. Új bejelentkezés
            print(f"\n[{system_key.upper()}] Új bejelentkezés indítása...")
            context = browser.new_context()
            page = context.new_page()
            page.goto(base_url, timeout=15000)

            try:
                page.wait_for_selector("input[name='username']", timeout=5000)
                page.fill("input[name='username']", username)
                page.fill("input[name='password']", password)
                page.click("button[type='submit']")
                
                try:
                    page.wait_for_selector("#searchField_all", timeout=10000)
                    context.storage_state(path=state_file)
                    print(f"💾 Session elmentve: {state_file}")
                    
                    page.close(); browser.close()
                    return {"status": "success", "message": f"{system_key.upper()}: Sikeres belépés."}
                except:
                    # Hibakép mentése egyedi névvel
                    error_shot = os.path.join(LOGIN_DATA_DIR, f"{system_key}_error.png")
                    page.screenshot(path=error_shot)
                    browser.close()
                    return {"status": "error", "message": f"{system_key.upper()} Időtúllépés."}

            except Exception as e:
                browser.close()
                return {"status": "error", "message": str(e)}

    except Exception as e:
        return {"status": "error", "message": f"Playwright hiba: {str(e)}"}


# --- SESSION STATUS ELLENŐRZÉS (Cookie check) ---
def check_session_validity(state_file):
    if not os.path.exists(state_file): return False
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        cookies = data.get('cookies', [])
        if not cookies: return False
        
        current_time = time.time()
        for cookie in cookies:
            if 'expires' in cookie and cookie['expires'] != -1:
                if cookie['expires'] < current_time:
                    return False
        return True
    except:
        return False

# --- ROUTE-OK ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/raktar')
def raktar_info():
    return render_template('raktar.html')

@app.route('/kollazs')
def kollazs():
    return render_template('kollazs.html')

# --- ÚJ: EGYSÉGES API VÉGPONT ---
@app.route('/api/login', methods=['POST'])
def api_login():
    if not ADMIN_USER or not ADMIN_PASS:
        return jsonify({"status": "error", "message": "Nincs jelszó a .env-ben!"}), 500
    
    # A JSON body-ból olvassuk ki, melyik rendszer kell (pl. { "system": "szvg" })
    data = request.json
    system_key = data.get('system')
    
    if not system_key or system_key not in SYSTEMS:
        return jsonify({"status": "error", "message": "Érvénytelen rendszer azonosító!"}), 400

    result = run_login_logic(ADMIN_USER, ADMIN_PASS, system_key)
    return jsonify(result), (200 if result["status"] == "success" else 500)

@app.route('/api/status', methods=['GET'])
def get_system_status():
    # Dinamikusan felépítjük a státusz választ a SYSTEMS alapján
    status_response = {}
    for key, config in SYSTEMS.items():
        is_online = check_session_validity(config["state_file"])
        status_response[key] = "connected" if is_online else "disconnected"
        
    return jsonify(status_response)

if __name__ == '__main__':

    app.run(debug=True, port=5000)
