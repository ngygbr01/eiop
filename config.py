import os
from dotenv import load_dotenv

load_dotenv()

# Mappák beállítása
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGIN_DATA_DIR = os.path.join(BASE_DIR, "login_data")

if not os.path.exists(LOGIN_DATA_DIR):
    os.makedirs(LOGIN_DATA_DIR)

# Hitelesítési adatok
ADMIN_USER = os.environ.get("ADMIN_USERNAME")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD")

# Rendszerek definíciója
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