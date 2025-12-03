from flask import Flask, render_template, send_from_directory, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os
import logging
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix

from auth import AuthService
from game import GameService
from database import DatabaseService

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bestimme Pfade basierend auf aktuellem Verzeichnis
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(BASE_DIR) == 'backend':
    # Gestartet aus backend/ Ordner
    FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')
else:
    # Gestartet aus Hauptordner
    FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

FRONTEND_DIR = os.path.abspath(FRONTEND_DIR)
logger.info(f"📁 Frontend Directory: {FRONTEND_DIR}")

# Flask App ohne static_folder (wir routen manuell)
app = Flask(__name__, 
            template_folder=FRONTEND_DIR,
            static_folder=None)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['APPLICATION_ROOT'] = '/wahlplakatgame'
app.config['PREFERRED_URL_SCHEME'] = 'https'  # <-- Fügen Sie diese Zeile hinzu
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

CORS(app, resources={r"/*": {"origins": "*"}})

# WICHTIG: async_mode='eventlet' für stabile WebSocket Verbindungen
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='eventlet', 
    logger=False, 
    engineio_logger=False, 
    path='/wahlplakatgame/socket.io',
    ping_timeout=60,      # ← NEU: Warte 60s auf Pong
    ping_interval=25      # ← NEU: Sende alle 25s ein Ping
)

# Services initialisieren
db_service = DatabaseService()
auth_service = AuthService(db_service)
game_service = GameService(db_service, socketio)

# ==================== HTTP ROUTES ====================

@app.route('/')
@app.route('/wahlplakatgame')
@app.route('/wahlplakatgame/')
def index():
    """Hauptseite"""
    return render_template('index.html')

@app.route('/css/<path:filename>')
@app.route('/wahlplakatgame/css/<path:filename>')
def serve_css(filename):
    """CSS Dateien ausliefern"""
    css_dir = os.path.join(FRONTEND_DIR, 'css')
    return send_from_directory(css_dir, filename)

@app.route('/js/<path:filename>')
@app.route('/wahlplakatgame/js/<path:filename>')
def serve_js(filename):
    """JavaScript Dateien ausliefern"""
    js_dir = os.path.join(FRONTEND_DIR, 'js')
    return send_from_directory(js_dir, filename)

@app.route('/assets/<path:filename>')
@app.route('/wahlplakatgame/assets/<path:filename>')
def serve_assets(filename):
    """Assets ausliefern"""
    assets_dir = os.path.join(FRONTEND_DIR, 'assets')
    return send_from_directory(assets_dir, filename)

@app.route('/health')
@app.route('/wahlplakatgame/health')
def health():
    """Health Check Endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'players_online': len(game_service.lobby.players)
    })

# ==================== AUTH API ====================

@app.route('/api/auth/register', methods=['POST'])
@app.route('/wahlplakatgame/api/auth/register', methods=['POST'])
def register():
    """Registrierung"""
    data = request.get_json()
    nickname = data.get('nickname', '').strip()
    password = data.get('password', '')
    
    result = auth_service.register_account(nickname, password)
    return jsonify(result), 200 if result['success'] else 400

@app.route('/api/auth/login', methods=['POST'])
@app.route('/wahlplakatgame/api/auth/login', methods=['POST'])
def login():
    """Login"""
    data = request.get_json()
    nickname = data.get('nickname', '').strip()
    password = data.get('password', '')
    ip_address = request.remote_addr
    
    result = auth_service.login(nickname, password, ip_address)
    return jsonify(result), 200 if result['success'] else 400

@app.route('/api/auth/logout', methods=['POST'])
@app.route('/wahlplakatgame/api/auth/logout', methods=['POST'])
def logout():
    """Logout"""
    data = request.get_json()
    token = data.get('token', '')
    
    result = auth_service.logout(token)
    return jsonify(result)

@app.route('/api/auth/validate', methods=['POST'])
@app.route('/wahlplakatgame/api/auth/validate', methods=['POST'])
def validate_token():
    """Token validieren"""
    data = request.get_json()
    token = data.get('token', '')
    
    result = auth_service.validate_token(token)
    return jsonify(result)

@app.route('/api/auth/check-username', methods=['POST'])
@app.route('/wahlplakatgame/api/auth/check-username', methods=['POST'])
def check_username():
    """Username Verfügbarkeit prüfen"""
    data = request.get_json()
    nickname = data.get('nickname', '')
    
    result = auth_service.check_username_available(nickname)
    return jsonify(result)

# ==================== GAME API ====================

@app.route('/api/game/parteien', methods=['GET'])
@app.route('/wahlplakatgame/api/game/parteien', methods=['GET'])
def get_parteien():
    """Alle Parteien holen"""
    try:
        parteien = db_service.get_alle_parteien()
        return jsonify({'success': True, 'parteien': parteien})
    except Exception as e:
        logger.error(f"Fehler beim Holen der Parteien: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/game/leaderboard', methods=['GET'])
@app.route('/wahlplakatgame/api/game/leaderboard', methods=['GET'])
def get_leaderboard():
    """Leaderboard holen"""
    limit = request.args.get('limit', 10, type=int)
    try:
        top_users = db_service.get_top_users(limit=limit)
        
        leaderboard = []
        for i, user in enumerate(top_users, 1):
            leaderboard.append({
                'rank': i,
                'nickname': user.nickname,
                'points': user.points
            })
        
        return jsonify({'success': True, 'leaderboard': leaderboard})
    except Exception as e:
        logger.error(f"Fehler beim Holen des Leaderboards: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== SOCKETIO EVENTS ====================

@socketio.on('connect')
def handle_connect():
    """Client verbunden"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Verbindung erfolgreich'})

@socketio.on('disconnect')
def handle_disconnect():
    """Client getrennt"""
    logger.info(f"Client disconnected: {request.sid}")
    game_service.handle_disconnect(request.sid)

@socketio.on('join_game')
def handle_join_game(data):
    """Spiel beitreten"""
    try:
        token = data.get('token')
        user_info = auth_service.validate_token(token)
        
        if not user_info.get('valid'):
            emit('error', {'message': 'Ungültiger Token'})
            return
        
        game_service.add_player(
            session_token=token,
            user_id=user_info['user_id'],
            nickname=user_info['nickname'],
            sid=request.sid,
            points=user_info['points']
        )
        
    except Exception as e:
        logger.exception(f"Fehler bei join_game: {e}")
        emit('error', {'message': str(e)})

@socketio.on('leave_game')
def handle_leave_game(data):
    """Spiel verlassen"""
    try:
        token = data.get('token')
        reason = data.get('reason', 'request')
        game_service.remove_player(token, request.sid, reason)
    except Exception as e:
        logger.exception(f"Fehler bei leave_game: {e}")

@socketio.on('submit_answer')
def handle_submit_answer(data):
    """Antwort abgeben"""
    try:
        token = data.get('token')
        partei = data.get('partei')
        game_service.submit_answer(token, partei, request.sid)
    except Exception as e:
        logger.exception(f"Fehler bei submit_answer: {e}")
        emit('error', {'message': str(e)})

@socketio.on('request_leaderboard')
def handle_request_leaderboard():
    """Leaderboard anfordern"""
    try:
        top_users = db_service.get_top_users(limit=10)
        
        leaderboard = []
        for i, user in enumerate(top_users, 1):
            leaderboard.append({
                'rank': i,
                'nickname': user.nickname,
                'points': user.points
            })
        
        emit('leaderboard_update', {'leaderboard': leaderboard})
    except Exception as e:
        logger.exception(f"Fehler bei request_leaderboard: {e}")

# ==================== SERVER START ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"🚀 Starting WahlplakatGame Server on port {port}")
    logger.info(f"🗳️  Debug mode: {debug}")
    logger.info(f"⚡ Using eventlet async_mode for stable WebSockets")
    
    # Wichtig: allow_unsafe_werkzeug nicht in Produktion verwenden!
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)