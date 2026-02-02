from flask import Blueprint, render_template

frontend_bp = Blueprint('frontend', __name__)

@frontend_bp.route('/')
def index():
    return render_template('index.html')

@frontend_bp.route('/raktar_info')
def raktar_info():
    return render_template('raktar_info.html')

@frontend_bp.route('/kollazs')
def kollazs():
    return render_template('kollazs.html')