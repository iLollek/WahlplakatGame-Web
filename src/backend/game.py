import threading
import logging
import random
from typing import Dict, Optional
import eventlet

logger = logging.getLogger(__name__)


class GameLobby:
    """Zentrale Spiel-Lobby"""
    
    def __init__(self, db_service, game_service_callback):
        self.db_service = db_service
        self.game_service_callback = game_service_callback  # Callback für Timer
        self.players: Dict[str, dict] = {}  # session_token -> player_info
        self.sid_to_token: Dict[str, str] = {}  # sid -> session_token
        self.current_wahlspruch = None
        self.current_quelle = None
        self.current_answers: Dict[str, str] = {}  # session_token -> partei
        self.round_timer = None
        self.round_active = False
        self.round_number = 0
        self.lock = threading.Lock()
    
    def add_player(self, session_token: str, user_id: int, nickname: str, sid: str, points: int):
        """Spieler hinzufügen"""
        with self.lock:
            self.players[session_token] = {
                'user_id': user_id,
                'nickname': nickname,
                'sid': sid,
                'answered': False,
                'points': points,
                'can_answer': True
            }
            self.sid_to_token[sid] = session_token
            
            # Wenn Runde aktiv, kann neuer Spieler diese Runde nicht antworten
            if self.round_active:
                self.players[session_token]['can_answer'] = False
    
    def remove_player(self, session_token: str = None, sid: str = None) -> Optional[dict]:
        """Spieler entfernen"""
        with self.lock:
            # Token finden falls nur SID gegeben
            if sid and not session_token:
                session_token = self.sid_to_token.get(sid)
            
            if not session_token:
                return None
            
            player_info = None
            if session_token in self.players:
                player_info = self.players[session_token].copy()
                del self.players[session_token]
                
                if player_info['sid'] in self.sid_to_token:
                    del self.sid_to_token[player_info['sid']]
                
                if session_token in self.current_answers:
                    del self.current_answers[session_token]
            
            return player_info
    
    def get_player_list(self):
        """Spielerliste holen"""
        with self.lock:
            return [
                {
                    'nickname': p['nickname'],
                    'points': p['points'],
                    'answered': p['answered'],
                    'can_answer': p['can_answer']
                }
                for p in self.players.values()
            ]
    
    def start_new_round(self):
        """Neue Runde starten"""
        with self.lock:
            self.round_number += 1
            self.round_active = True
            self.current_answers = {}
            
            # Reset answered status
            for player in self.players.values():
                player['answered'] = False
                player['can_answer'] = True
            
            # Zufälligen Wahlspruch wählen
            self.current_wahlspruch = self.db_service.get_random_wahlspruch()
            
            if not self.current_wahlspruch:
                self.round_active = False
                return None
            
            self.current_quelle = self.current_wahlspruch.quelle
            
            # 15 Sekunden Timer - EVENTLET VERSION
            if self.round_timer:
                self.round_timer.cancel()
            
            # ← WICHTIG: Nutze eventlet.spawn_after statt threading.Timer
            self.round_timer = eventlet.spawn_after(15.0, self.game_service_callback)
            
            return {
                'round_number': self.round_number,
                'wahlspruch': self.current_wahlspruch.spruch,
                'wahlspruch_id': self.current_wahlspruch.id
            }
    
    def submit_answer(self, session_token: str, partei: str):
        """Antwort registrieren"""
        with self.lock:
            if not self.round_active:
                return False, "Keine aktive Runde"
            
            if session_token not in self.players:
                return False, "Nicht in der Lobby"
            
            player = self.players[session_token]
            
            if not player['can_answer']:
                return False, "Du bist während der laufenden Runde beigetreten"
            
            if player['answered']:
                return False, "Du hast bereits geantwortet"
            
            self.current_answers[session_token] = partei
            player['answered'] = True
            
            return True, "Antwort registriert"
    
    def end_round(self):
        """Runde beenden"""
        with self.lock:
            if not self.round_active:
                return None
            
            self.round_active = False
            
            if not self.current_wahlspruch:
                return None
            
            correct_partei = self.current_wahlspruch.partei
            results = []
            
            # Ergebnisse berechnen
            for session_token, player in self.players.items():
                answered_partei = self.current_answers.get(session_token, None)
                
                if player['can_answer']:
                    is_correct = answered_partei == correct_partei if answered_partei else False
                    points_earned = 1 if is_correct else 0
                    
                    if is_correct:
                        new_points = player['points'] + points_earned
                        self.db_service.update_user_points(player['user_id'], new_points)
                        player['points'] = new_points
                else:
                    is_correct = None
                    points_earned = 0
                
                results.append({
                    'nickname': player['nickname'],
                    'answered': answered_partei,
                    'correct': is_correct,
                    'points_earned': points_earned,
                    'total_points': player['points'],
                    'could_answer': player['can_answer']
                })
            
            return {
                'correct_partei': correct_partei,
                'results': results,
                'quelle': self.current_quelle
            }


class GameService:
    """Game Service - verwaltet Spiel-Logik"""
    
    def __init__(self, db_service, socketio):
        self.db_service = db_service
        self.socketio = socketio
        self.lobby = GameLobby(db_service, self.end_current_round)
    
    def add_player(self, session_token: str, user_id: int, nickname: str, sid: str, points: int):
        """Spieler zur Lobby hinzufügen"""
        # Entferne falls schon drin (reconnect)
        self.lobby.remove_player(session_token)
        
        # Hinzufügen
        self.lobby.add_player(session_token, user_id, nickname, sid, points)
        
        # Spielerliste broadcasten
        player_list = self.lobby.get_player_list()
        self.socketio.emit('player_list_update', {'players': player_list})
        
        # Anderen Bescheid geben
        self.socketio.emit('player_joined', {
            'nickname': nickname,
            'points': points
        }, skip_sid=sid)
        
        # Success an Spieler senden
        self.socketio.emit('join_success', {
            'players': player_list,
            'your_nickname': nickname,
            'round_active': self.lobby.round_active,
            'round_number': self.lobby.round_number
        }, room=sid)
        
        # Wenn aktive Runde, sende Wahlspruch
        if self.lobby.round_active and self.lobby.current_wahlspruch:
            self.socketio.emit('new_round', {
                'round_number': self.lobby.round_number,
                'wahlspruch': self.lobby.current_wahlspruch.spruch,
                'wahlspruch_id': self.lobby.current_wahlspruch.id
            }, room=sid)
        
        # Erste Runde starten wenn erster Spieler
        if len(self.lobby.players) == 1 and not self.lobby.round_active:
            round_data = self.lobby.start_new_round()
            if round_data:
                self.socketio.emit('new_round', round_data)
        
        logger.info(f"✅ {nickname} ist beigetreten")
    
    def remove_player(self, token: str, sid: str, reason: str = 'request'):
        """Spieler entfernen"""
        player_info = self.lobby.remove_player(token, sid)
        
        if player_info:
            nickname = player_info['nickname']
            
            # Anderen Bescheid geben
            self.socketio.emit('player_left', {
                'nickname': nickname,
                'reason': reason
            })
            
            # Spielerliste updaten
            player_list = self.lobby.get_player_list()
            self.socketio.emit('player_list_update', {'players': player_list})
            
            logger.info(f"👋 {nickname} hat verlassen ({reason})")
    
    def handle_disconnect(self, sid: str):
        """Handle automatisches Disconnect"""
        player_info = self.lobby.remove_player(sid=sid)
        
        if player_info:
            nickname = player_info['nickname']
            
            self.socketio.emit('player_left', {
                'nickname': nickname,
                'reason': 'disconnect'
            })
            
            player_list = self.lobby.get_player_list()
            self.socketio.emit('player_list_update', {'players': player_list})
            
            logger.info(f"🔌 {nickname} disconnected")
    
    def submit_answer(self, token: str, partei: str, sid: str):
        """Antwort abgeben"""
        success, message = self.lobby.submit_answer(token, partei)
        
        if success:
            player = self.lobby.players[token]
            
            # Bestätigung an Spieler
            self.socketio.emit('answer_accepted', {'partei': partei}, room=sid)
            
            # Anderen Bescheid geben
            self.socketio.emit('player_answered', {
                'nickname': player['nickname']
            }, skip_sid=sid)
            
            # Spielerliste updaten
            player_list = self.lobby.get_player_list()
            self.socketio.emit('player_list_update', {'players': player_list})
            
            logger.info(f"✓ {player['nickname']} antwortete: {partei}")
            
            # Prüfen ob alle geantwortet haben und Runde beenden
            players_who_can_answer = [p for p in self.lobby.players.values() if p['can_answer']]
            all_answered = all(p['answered'] for p in players_who_can_answer)
            
            if all_answered and len(players_who_can_answer) > 0:
                if self.lobby.round_timer:
                    # ← WICHTIG: eventlet greenthread killen
                    eventlet.kill(self.lobby.round_timer)
                # Runde sofort beenden
                self.end_current_round()
        else:
            self.socketio.emit('error', {'message': message}, room=sid)
    
    def auto_start_next_round(self):
        """Nächste Runde automatisch starten"""
        if len(self.lobby.players) > 0:
            round_data = self.lobby.start_new_round()
            if round_data:
                self.socketio.emit('new_round', round_data)
    
    def end_current_round(self):
        """Aktuelle Runde beenden"""
        result = self.lobby.end_round()
        
        if result:
            # Ergebnisse senden
            self.socketio.emit('round_end', result)
            
            # Nach 5 Sekunden nächste Runde - EVENTLET VERSION
            eventlet.spawn_after(5.0, self.auto_start_next_round)
