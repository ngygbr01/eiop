from flask import Blueprint, Response, stream_with_context
from config import SYSTEMS
from .excel_letolto import excel_szinkronizacio_stream

raktar_bp = Blueprint('raktar', __name__)

@raktar_bp.route('/api/stream_inventory')
def stream_inventory():
    """
    SSE végpont a készlet szinkronizáláshoz.
    """
    # Az SZVG sessionjét használjuk
    state_file = SYSTEMS['szvg']['state_file']
    
    return Response(
        stream_with_context(excel_szinkronizacio_stream(state_file)), 
        mimetype='text/event-stream'
    )