import io
import re
import numpy as np
import pandas as pd
import easyocr
import pypdfium2 as pdfium
from PIL import Image
from flask import Blueprint, request, send_file, render_template, jsonify

# Létrehozzuk a Flask Blueprintet
szkenner_bp = Blueprint('szkenner_bp', __name__)

# --- EasyOCR Inicializálása (Csak egyszer fut le) ---
print("🧠 EasyOCR modell betöltése (kis türelmet)...")
reader = easyocr.Reader(['hu'])
print("✅ Modell betöltve!")

def parse_invoice_text(raw_text):
    """Vízszintes (oszlopos) táblázatot építő logika"""
    lines = raw_text.split('\n')
    parsed_data = []
    current_item = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Új tétel sorszám keresése (pl. 0010, 0020)
        if re.match(r'^0\d{3}$', line): 
            if current_item:
                parsed_data.append(current_item)
            current_item = {
                "Tétel Sorszám": line, "Cikkszám": "null", "Megnevezés": "",
                "Mennyiség": "null", "Mértékegység": "null", "Egységár": "null",
                "Nettó Érték": "null", "Bruttó Érték": "null"
            }
            continue
        
        if current_item:
            if re.match(r'^[A-Z0-9]{5,8}$', line) and current_item["Cikkszám"] == "null":
                current_item["Cikkszám"] = line
                continue
                
            qty_match = re.search(r'^(\d+[\.,]\d{2})\s*(DB|db|Db|KLT|M|KG)?$', line)
            if qty_match and current_item["Mennyiség"] == "null":
                current_item["Mennyiség"] = qty_match.group(1)
                if qty_match.group(2):
                    current_item["Mértékegység"] = qty_match.group(2).upper()
                continue
                
            if line.upper() in ["DB", "KLT", "M", "KG"] and current_item["Mértékegység"] == "null":
                current_item["Mértékegység"] = line.upper()
                continue
                
            price_match = re.search(r'^(\d{1,3}(?:\.\d{3})*,\d{2})$', line)
            if price_match:
                val = price_match.group(1)
                if current_item["Egységár"] == "null": current_item["Egységár"] = val
                elif current_item["Nettó Érték"] == "null": current_item["Nettó Érték"] = val
                elif current_item["Bruttó Érték"] == "null": current_item["Bruttó Érték"] = val
                continue
            
            if len(line) > 5 and not re.search(r'(ÁFA|árengedmény|Megrendelés|Engedményezett|F\. kat|Gyártó)', line, re.IGNORECASE):
                current_item["Megnevezés"] += line + " "

    if current_item:
        parsed_data.append(current_item)
        
    if not parsed_data:
         return [{"Hiba": "Nem felismerhető formátum", "Nyers szöveg": raw_text[:300]}]
         
    for item in parsed_data:
        if "Megnevezés" in item:
            item["Megnevezés"] = item["Megnevezés"].strip()
            if not item["Megnevezés"]: item["Megnevezés"] = "null"

    return parsed_data

@szkenner_bp.route('/szkenner')
def szkenner_oldal():
    # Megjeleníti a felületet
    return render_template('szkenner.html')

@szkenner_bp.route('/api/upload-invoice', methods=['POST'])
def upload_invoice():
    if 'file' not in request.files:
        return jsonify({"detail": "Nincs fájl kiválasztva"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"detail": "Nincs fájl kiválasztva"}), 400

    try:
        file_bytes = file.read()
        raw_text = ""
        
        # PDF feldolgozása
        if file.mimetype == "application/pdf" or file.filename.lower().endswith(".pdf"):
            pdf = pdfium.PdfDocument(file_bytes)
            for i in range(len(pdf)):
                page = pdf[i]
                bitmap = page.render(scale=3)
                pil_image = bitmap.to_pil()
                
                # Átalakítás Numpy tömbbé az EasyOCR-nek
                img_array = np.array(pil_image)
                results = reader.readtext(img_array, detail=0)
                raw_text += f"\n--- {i+1}. Oldal ---\n" + "\n".join(results)
                
        # Kép feldolgozása
        else:
            image = Image.open(io.BytesIO(file_bytes))
            img_array = np.array(image)
            results = reader.readtext(img_array, detail=0)
            raw_text = "\n".join(results)
            
    except Exception as e:
        return jsonify({"detail": f"Hiba a fájl feldolgozásakor: {str(e)}"}), 500
    
    # Adatok Excelbe konvertálása
    items = parse_invoice_text(raw_text)
    df = pd.DataFrame(items)
    df = df.astype(str)
    
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Tételek')
    except Exception as e:
        return jsonify({"detail": f"Hiba az Excel generálásakor: {str(e)}"}), 500
    
    output.seek(0)
    
    # Letöltés küldése
    return send_file(
        output,
        as_attachment=True,
        download_name="feldolgozott_szamla.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )