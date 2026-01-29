import os
from playwright.sync_api import sync_playwright

def fetch_inventory(state_file):
    """
    Belép az SZVG admin felületre a mentett sessionnel, 
    és leszedi a raktáron lévő termékeket.
    """
    url = "https://szvgtoolsshop.hu/administrator/index.php?view=products&inStock&mode=2"
    
    if not os.path.exists(state_file):
        return {"status": "error", "message": "Nincs bejelentkezve (hiányzó state file)."}

    data = []
    
    try:
        with sync_playwright() as p:
            # Headless módban, hogy gyors legyen
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=state_file)
            page = context.new_page()
            
            print(f"🔄 Adatok letöltése innen: {url}")
            page.goto(url, timeout=60000)
            
            # Megvárjuk, amíg a táblázat betöltődik
            try:
                page.wait_for_selector("table tbody tr", timeout=15000)
            except:
                browser.close()
                return {"status": "success", "data": [], "message": "Nincs termék a listában."}

            # --- GYORS ADATKINYERÉS (Browser Context-ben futtatott JS) ---
            # Ez sokkal gyorsabb, mint egyesével loopolni Pythonban
            products = page.evaluate("""() => {
                const rows = Array.from(document.querySelectorAll("table tbody tr"));
                return rows.map(row => {
                    const cells = row.querySelectorAll("td");
                    if (cells.length < 8) return null;

                    // 1. Név kinyerése (a tag b tagjéből)
                    const nameEl = cells[1].querySelector("a b") || cells[1];
                    const name = nameEl.innerText.trim();

                    // 2. Készlet (pl. "40 darab" -> 40)
                    const stockRaw = cells[2].innerText.trim(); // "40 darab"
                    const stock = parseInt(stockRaw.split(' ')[0].replace('.', '')) || 0;

                    // 3. Cikkszám (5. oszlop)
                    const sku = cells[5].innerText.trim();

                    // 4. Vonalkód (6. oszlop)
                    const barcode = cells[6].innerText.trim();

                    // 5. Ár (7. oszlop)
                    const priceRaw = cells[7].innerText.trim(); // "21.912 Ft"
                    // Csak a számokat hagyjuk meg
                    const price = parseInt(priceRaw.replace(/\D/g, '')) || 0;

                    return {
                        name: name,
                        sku: sku,
                        barcode: barcode,
                        stock: stock,
                        price: price,
                        raw_price: priceRaw
                    };
                }).filter(item => item !== null);
            }""")

            print(f"✅ Siker: {len(products)} termék letöltve.")
            browser.close()
            
            return {"status": "success", "data": products}

    except Exception as e:
        print(f"❌ Hiba a scraperben: {str(e)}")
        return {"status": "error", "message": str(e)}