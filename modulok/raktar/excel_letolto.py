import os
import time
import json
import pandas as pd
from playwright.sync_api import sync_playwright
from config import LOGIN_DATA_DIR 
from config import HEADLESS_MODE

def excel_szinkronizacio_stream(state_file):
    """
    Generator (SSE) a raktárkészlet Excel letöltéséhez és feldolgozásához.
    """
    url = "https://szvgtoolsshop.hu/administrator/index.php?view=products&inStock&mode=2"
    
    if not os.path.exists(state_file):
        yield f"data: {json.dumps({'type': 'error', 'message': 'Nincs bejelentkezve!'})}\n\n"
        return

    yield f"data: {json.dumps({'type': 'step', 'step': 1})}\n\n"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS_MODE)
            context = browser.new_context(storage_state=state_file, accept_downloads=True)
            page = context.new_page()
            
            try:
                page.goto(url, timeout=60000)
                page.wait_for_selector("a[onclick*='downloadInStockProducts']", state="visible", timeout=15000)
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Oldalbetöltési hiba: {str(e)}'})}\n\n"
                browser.close()
                return

            # 2. LÉPÉS
            yield f"data: {json.dumps({'type': 'step', 'step': 2})}\n\n"
            
            try:
                # Kattintás az export gombra
                page.locator("a[onclick*='downloadInStockProducts']").click()

                # Várakozás a Popup-ra (SweetAlert)
                confirm_selector = "button.swal2-confirm.pure-button-primary"
                page.wait_for_selector(confirm_selector, state="visible", timeout=5000)
                
                # Letöltés megerősítése
                with page.expect_download(timeout=60000) as download_info:
                    page.locator(confirm_selector).click()
                
                download = download_info.value
                import tempfile
                temp_dir = tempfile.gettempdir()
                temp_file = os.path.join(temp_dir, f"inventory_{int(time.time())}.xlsx")
                download.save_as(temp_file)
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Letöltési hiba: {str(e)}'})}\n\n"
                browser.close()
                return

            browser.close()

            # 3. LÉPÉS
            yield f"data: {json.dumps({'type': 'step', 'step': 3})}\n\n"
            
            try:
                # ... (Pandas beolvasás és tisztítás - EZ IS MARAD) ...
                df = None
                try: df = pd.read_excel(temp_file)
                except: df = pd.read_csv(temp_file)

                df.columns = [str(c).strip() for c in df.columns]
                products = []
                
                for _, row in df.iterrows():
                    # ... (Adat kinyerés loop - EZ IS MARAD) ...
                    # (Másold be a korábbi logikát a products.append-ig)
                    try:
                        name = str(row.get('Terméknév', '')).strip()
                        if not name or name.lower() == 'nan': continue
                        sku = str(row.get('Cikkszám', '')).strip()
                        stock = int(float(str(row.get('Szabad készlet', 0)).replace(',', '.')))
                        price_raw = str(row.get('Nettó ár', 0)).replace(' ', '').replace(',', '.')
                        price = int(float(price_raw))
                        barcode = str(row.get('Vonalkód', '')).split('.')[0]
                        if barcode == 'nan': barcode = ""

                        products.append({
                            "name": name, "sku": sku, "barcode": barcode,
                            "stock": stock, "price": price,
                            "raw_price": f"{price:,} Ft".replace(",", " ")
                        })
                    except: continue

                # Fájl törlés
                try: os.remove(temp_file)
                except: pass

                # --- ÚJ RÉSZ: MENTÉS SZERVERRE (JSON CACHE) ---
                cache_file = os.path.join(LOGIN_DATA_DIR, "inventory_cache.json")
                cache_data = {
                    "timestamp": time.time(), # Aktuális idő másodpercben
                    "data": products
                }
                
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f, ensure_ascii=False)
                
                print(f"✅ Adatok mentve ide: {cache_file}")

                # KÉSZ ÜZENET
                response_data = {"type": "complete", "data": products}
                yield f"data: {json.dumps(response_data)}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Feldolgozási hiba: {str(e)}'})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'Kritikus hiba: {str(e)}'})}\n\n"