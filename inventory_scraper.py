import os
import time
import json
import pandas as pd
from playwright.sync_api import sync_playwright

def download_inventory_stream(state_file):
    """
    Generator függvény (SSE), ami kezeli a SweetAlert2 felugró ablakot,
    letölti az Excelt, majd feldolgozza JSON formátumba.
    """
    url = "https://szvgtoolsshop.hu/administrator/index.php?view=products&inStock&mode=2"
    
    if not os.path.exists(state_file):
        yield f"data: {json.dumps({'type': 'error', 'message': 'Nincs bejelentkezve!'})}\n\n"
        return

    # --- 1. LÉPÉS: OLDAL MEGNYITÁSA ---
    yield f"data: {json.dumps({'type': 'step', 'step': 1})}\n\n"
    
    try:
        with sync_playwright() as p:
            # LÁTHATÓ BÖNGÉSZŐ (headless=False), hogy lásd mi történik
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=state_file, accept_downloads=True)
            page = context.new_page()
            
            try:
                page.goto(url, timeout=60000)
                # Megvárjuk az első gombot (A lista letöltése)
                # Keresünk az onclick attribútumra, vagy a szövegre
                page.wait_for_selector("a[onclick*='downloadInStockProducts']", state="visible", timeout=15000)
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Oldalbetöltési hiba: {str(e)}'})}\n\n"
                browser.close()
                return

            # --- 2. LÉPÉS: EXPORTÁLÁS (Kattintás + Popup kezelés) ---
            yield f"data: {json.dumps({'type': 'step', 'step': 2})}\n\n"
            
            try:
                # 1. Rákattintunk a fő "A lista letöltése" gombra
                print("Kattintás az export gombra...")
                page.locator("a[onclick*='downloadInStockProducts']").click()

                # 2. Megvárjuk a SweetAlert2 felugró ablakot és a "Letöltés" gombot
                # A te HTML kódod alapján: button.swal2-confirm.pure-button-primary
                confirm_selector = "button.swal2-confirm.pure-button-primary"
                print("Várakozás a megerősítő ablakra...")
                page.wait_for_selector(confirm_selector, state="visible", timeout=5000)
                
                # 3. Download listener indítása és a popup gomb megnyomása
                with page.expect_download(timeout=60000) as download_info:
                    print("Megerősítés klikkelése...")
                    page.locator(confirm_selector).click()
                
                download = download_info.value
                temp_file = os.path.join(os.getcwd(), f"inventory_temp_{int(time.time())}.xlsx")
                download.save_as(temp_file)
                print(f"Fájl sikeresen letöltve: {temp_file}")
                
            except Exception as e:
                error_msg = f"Letöltési hiba (Popup nem jelent meg?): {str(e)}"
                print(error_msg)
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                browser.close()
                return

            browser.close()

            # --- 3. LÉPÉS: FELDOLGOZÁS (Pandas) ---
            yield f"data: {json.dumps({'type': 'step', 'step': 3})}\n\n"
            
            try:
                # Próbáljuk Excelként, ha nem megy, CSV-ként
                df = None
                try:
                    df = pd.read_excel(temp_file)
                except:
                    df = pd.read_csv(temp_file)

                # Oszlopnevek tisztítása
                df.columns = [str(c).strip() for c in df.columns]
                
                products = []
                
                for _, row in df.iterrows():
                    try:
                        # Adatkinyerés a CSV oszlopaiból
                        name = str(row.get('Terméknév', '')).strip()
                        if not name or name.lower() == 'nan': continue

                        sku = str(row.get('Cikkszám', '')).strip()
                        
                        # Készlet
                        stock_raw = row.get('Szabad készlet', 0)
                        try:
                            stock = int(float(str(stock_raw).replace(',', '.')))
                        except:
                            stock = 0
                            
                        # Ár
                        price_raw = row.get('Nettó ár', 0)
                        try:
                            price_str = str(price_raw).replace(' ', '').replace(',', '.')
                            price = int(float(price_str))
                        except:
                            price = 0
                            
                        # Vonalkód
                        barcode_raw = row.get('Vonalkód', '')
                        if pd.isna(barcode_raw) or barcode_raw == '':
                            barcode = ""
                        else:
                            barcode = str(barcode_raw).split('.')[0]

                        products.append({
                            "name": name,
                            "sku": sku,
                            "barcode": barcode,
                            "stock": stock,
                            "price": price,
                            "raw_price": f"{price:,} Ft".replace(",", " ")
                        })
                    except:
                        continue

                # Törlés
                try:
                    os.remove(temp_file)
                except:
                    pass

                # KÉSZ
                response_data = {"type": "complete", "data": products}
                yield f"data: {json.dumps(response_data)}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Fájlhiba: {str(e)}'})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'Kritikus hiba: {str(e)}'})}\n\n"