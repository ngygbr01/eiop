import os
import json
import time
from playwright.sync_api import sync_playwright
from config import SYSTEMS

def futtat_bejelentkezes(username, password, system_key):
    config = SYSTEMS.get(system_key)
    if not config:
        return {"status": "error", "message": "Ismeretlen rendszer!"}
    
    base_url = config["url"]
    state_file = config["state_file"]

    try:
        with sync_playwright() as p:
            # headless=False -> LÁTHATÓ MÓD
            browser = p.chromium.launch(headless=False)
            context = None
            
            # 1. Meglévő session ellenőrzése
            if os.path.exists(state_file):
                try:
                    context = browser.new_context(storage_state=state_file)
                    page = context.new_page()
                    page.goto(base_url, timeout=15000)
                    
                    if page.is_visible("input[name='username']"):
                        # Ha kidobott a rendszer
                        page.close(); context.close(); context = None
                    else:
                        # Ha még bent vagyunk
                        page.close(); browser.close()
                        return {"status": "success", "message": f"{system_key.upper()}: Kapcsolat aktív."}
                except:
                    if context: context.close()

            # 2. Új bejelentkezés
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
                    page.close(); browser.close()
                    return {"status": "success", "message": f"{system_key.upper()}: Sikeres belépés."}
                except:
                    browser.close()
                    return {"status": "error", "message": "Időtúllépés vagy hibás jelszó."}
            except Exception as e:
                browser.close()
                return {"status": "error", "message": str(e)}

    except Exception as e:
        return {"status": "error", "message": f"Playwright hiba: {str(e)}"}

def ellenoriz_session_ervenyesseg(state_file):
    if not os.path.exists(state_file): return False
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        cookies = data.get('cookies', [])
        if not cookies: return False
        
        current_time = time.time()
        for cookie in cookies:
            if 'expires' in cookie and cookie['expires'] != -1:
                if cookie['expires'] < current_time: return False
        return True
    except:
        return False