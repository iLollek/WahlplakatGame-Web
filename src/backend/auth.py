import hashlib
import secrets
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Authentifizierungs-Service für Login und Registrierung"""
    
    def __init__(self, db_service):
        self.db_service = db_service
        self.active_sessions: Dict[str, int] = {}  # token -> user_id
    
    def _hash_password(self, password: str) -> str:
        """Passwort hashen mit SHA-256"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def _generate_session_token(self) -> str:
        """Sicheren Session-Token generieren"""
        return secrets.token_urlsafe(32)
    
    def register_account(self, nickname: str, password: str) -> Dict:
        """
        Neues Konto erstellen
        
        Returns:
            {"success": bool, "message": str}
        """
        try:
            # Validierung
            if not nickname or len(nickname) > 18:
                return {
                    "success": False,
                    "message": "Nickname muss zwischen 1 und 18 Zeichen lang sein."
                }
            
            if not password or len(password) < 6:
                return {
                    "success": False,
                    "message": "Passwort muss mindestens 6 Zeichen lang sein."
                }
            
            # Passwort hashen
            hashed_password = self._hash_password(password)
            
            # User erstellen
            success = self.db_service.create_new_user(nickname, hashed_password)
            
            if success:
                user = self.db_service.get_user_by_nickname(nickname)
                logger.info(f"Neues Konto erstellt: {nickname}")
                return {
                    "success": True,
                    "message": "Konto erfolgreich erstellt!",
                    "user_id": user[0].id
                }
            else:
                return {
                    "success": False,
                    "message": "Nickname bereits vergeben."
                }
                
        except Exception as e:
            logger.exception(f"Fehler bei Registrierung: {e}")
            return {
                "success": False,
                "message": f"Fehler beim Erstellen des Kontos: {str(e)}"
            }
    
    def login(self, nickname: str, password: str, ip_address: str = "unknown") -> Dict:
        """
        User anmelden
        
        Returns:
            {"success": bool, "message": str, "token": str, "user_id": int, "nickname": str, "points": int}
        """
        try:
            # User aus DB holen
            user = self.db_service.get_user_by_nickname(nickname)
            
            if not user:
                return {
                    "success": False,
                    "message": "Ungültiger Nickname oder Passwort."
                }
            
            user = user[0]
            
            # Passwort prüfen
            hashed_password = self._hash_password(password)
            if user.password != hashed_password:
                return {
                    "success": False,
                    "message": "Ungültiger Nickname oder Passwort."
                }
            
            # Session Token generieren
            token = self._generate_session_token()
            
            # User Session updaten
            self.db_service.update_user_session(user.id, token, ip_address)
            
            # Session cachen
            self.active_sessions[token] = user.id
            
            logger.info(f"Login erfolgreich: {nickname} von {ip_address}")
            
            return {
                "success": True,
                "message": "Erfolgreich angemeldet!",
                "token": token,
                "user_id": user.id,
                "nickname": user.nickname,
                "points": user.points,
                "last_login_ip": user.last_login_ip,
                "last_login_time": user.last_login_time.isoformat() if user.last_login_time else None
            }
            
        except Exception as e:
            logger.exception(f"Fehler bei Login: {e}")
            return {
                "success": False,
                "message": f"Fehler beim Login: {str(e)}"
            }
    
    def logout(self, token: str) -> Dict:
        """
        User abmelden
        
        Returns:
            {"success": bool, "message": str}
        """
        try:
            user_id = self._validate_session(token)
            
            if not user_id:
                return {
                    "success": False,
                    "message": "Ungültige Session."
                }
            
            # Aus Cache entfernen
            if token in self.active_sessions:
                del self.active_sessions[token]
            
            # Session Token in DB löschen
            self.db_service.update_user_session(user_id, "", "")
            
            logger.info(f"Logout: User ID {user_id}")
            
            return {
                "success": True,
                "message": "Erfolgreich abgemeldet."
            }
            
        except Exception as e:
            logger.exception(f"Fehler bei Logout: {e}")
            return {
                "success": False,
                "message": f"Fehler beim Logout: {str(e)}"
            }
    
    def validate_token(self, token: str) -> Dict:
        """
        Token validieren
        
        Returns:
            {"valid": bool, "user_id": int, "nickname": str, "points": int}
        """
        try:
            user_id = self._validate_session(token)
            
            if user_id:
                user = self.db_service.get_user_by_id(user_id)
                if user:
                    return {
                        "valid": True,
                        "user_id": user[0].id,
                        "nickname": user[0].nickname,
                        "points": user[0].points
                    }
            
            return {"valid": False}
            
        except Exception as e:
            logger.exception(f"Fehler bei Token-Validierung: {e}")
            return {"valid": False, "error": str(e)}
    
    def check_username_available(self, nickname: str) -> Dict:
        """
        Username Verfügbarkeit prüfen
        
        Returns:
            {"available": bool, "message": str}
        """
        try:
            # Länge prüfen
            if not nickname or len(nickname) > 18:
                return {
                    "available": False,
                    "message": "Nickname muss zwischen 1 und 18 Zeichen lang sein."
                }
            
            # Existenz prüfen
            existing = self.db_service.get_user_by_nickname(nickname)
            
            if existing:
                return {
                    "available": False,
                    "message": "Nickname bereits vergeben."
                }
            else:
                return {
                    "available": True,
                    "message": "Nickname verfügbar!"
                }
                
        except Exception as e:
            logger.exception(f"Fehler bei Username-Check: {e}")
            return {
                "available": False,
                "message": f"Fehler beim Prüfen: {str(e)}"
            }
    
    def _validate_session(self, token: str) -> Optional[int]:
        """
        Session Token validieren und User ID zurückgeben
        
        Returns:
            user_id oder None
        """
        # Zuerst im Cache schauen
        if token in self.active_sessions:
            return self.active_sessions[token]
        
        # Sonst in DB prüfen
        user = self.db_service.get_user_by_session_token(token)
        if user:
            user_id = user[0].id
            self.active_sessions[token] = user_id
            return user_id
        
        return None
