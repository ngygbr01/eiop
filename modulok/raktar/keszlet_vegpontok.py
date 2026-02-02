import os
import json
import time
from flask import Blueprint, Response, stream_with_context, jsonify
from config import SYSTEMS, LOGIN_DATA_DIR
from .excel_letolto import excel_szinkronizacio_stream

raktar_bp = Blueprint('raktar', __name__)

@raktar_bp.route('/api/stream_inventory')
def stream_inventory():
    """
    SSE végpont a készlet szinkronizáláshoz.
    """
    state_file = SYSTEMS['szvg']['state_file']
    return Response(
        stream_with_context(excel_szinkronizacio_stream(state_file)), 
        mimetype='text/event-stream'
    )

@raktar_bp.route('/api/get_inventory_cache', methods=['GET'])
def get_inventory_cache():
    """
    Visszaadja a lementett készlet adatokat és az időbélyeget.
    """
    cache_file = os.path.join(LOGIN_DATA_DIR, "inventory_cache.json")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify({"status": "success", "data": data["data"], "timestamp": data["timestamp"]})
        except Exception as e:
            return jsonify({"status": "error", "message": "Hiba a fájl olvasásakor"}), 500
    else:
        return jsonify({"status": "empty", "message": "Nincs mentett adat."}), 200

# --- ÚJ VÉGPONT: CSAK STÁTUSZ ELLENŐRZÉS (GYORS) ---
@raktar_bp.route('/api/check_inventory_status', methods=['GET'])
def check_inventory_status():
    """
    Gyorsan megnézi, létezik-e mentett adat, és mikor készült.
    Nem tölti be a nagy adatmennyiséget, csak a fájl meglétét ellenőrzi.
    """
    cache_file = os.path.join(LOGIN_DATA_DIR, "inventory_cache.json")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                # Csak az időbélyeg érdekel minket
                data = json.load(f)
                timestamp = data.get("timestamp", 0)
            return jsonify({"exists": True, "timestamp": timestamp})
        except:
            return jsonify({"exists": False})
    
    return jsonify({"exists": False})