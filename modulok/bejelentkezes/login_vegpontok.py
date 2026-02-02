from flask import Blueprint, jsonify, request
from config import ADMIN_USER, ADMIN_PASS, SYSTEMS
from .session_szolgaltatas import futtat_bejelentkezes, ellenoriz_session_ervenyesseg

# Blueprint létrehozása
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    if not ADMIN_USER or not ADMIN_PASS:
        return jsonify({"status": "error", "message": "Nincs jelszó beállítva (.env)!"}), 500
    
    data = request.json
    system_key = data.get('system')
    
    if not system_key or system_key not in SYSTEMS:
        return jsonify({"status": "error", "message": "Érvénytelen rendszer azonosító!"}), 400

    result = futtat_bejelentkezes(ADMIN_USER, ADMIN_PASS, system_key)
    
    status_code = 200 if result["status"] == "success" else 500
    return jsonify(result), status_code

@auth_bp.route('/api/status', methods=['GET'])
def get_system_status():
    status_response = {}
    for key, config in SYSTEMS.items():
        is_online = ellenoriz_session_ervenyesseg(config["state_file"])
        status_response[key] = "connected" if is_online else "disconnected"
        
    return jsonify(status_response)