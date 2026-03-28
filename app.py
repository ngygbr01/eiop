from flask import Flask
from dotenv import load_dotenv

# Modulok importálása
from modulok.bejelentkezes.login_vegpontok import auth_bp
from modulok.raktar.keszlet_vegpontok import raktar_bp
from modulok.frontend.oldal_megjelenito import frontend_bp
from modulok.szkenner.szkenner_vegpontok import szkenner_bp

load_dotenv()

app = Flask(__name__)

# Blueprintek regisztrálása
app.register_blueprint(auth_bp)
app.register_blueprint(raktar_bp)
app.register_blueprint(frontend_bp)
app.register_blueprint(szkenner_bp)

if __name__ == '__main__':
    print("🚀 EIOP Rendszer Indítása...")
    # host='0.0.0.0' -> Hálózati elérés
    # threaded=True -> Párhuzamos szálak (SSE-hez kötelező!)
    app.run(host='0.0.0.0', debug=True, port=5000, threaded=True)