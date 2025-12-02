import sillyorm
import os
import random
import logging
from datetime import datetime
from models import User, Wahlspruch

logger = logging.getLogger(__name__)


class DatabaseService:
    """Database Service für WahlplakatGame"""
    
    def __init__(self):
        self.env = self._get_environment()
    
    def _get_environment(self):
        """Environment initialisieren"""
        # Versuche PostgreSQL Connection String aus Umgebungsvariable
        pg_connection = os.environ.get('DATABASE_URL')
        print(f'PG connection ist: {pg_connection}')
        
        if pg_connection:
            logger.info("📊 Verwende PostgreSQL Datenbank")
            registry = sillyorm.Registry(pg_connection)
        else:
            logger.info("📊 Verwende SQLite Datenbank (Fallback)")
            registry = sillyorm.Registry("sqlite:///wahlplakatgame.db")
        
        registry.register_model(User)
        registry.register_model(Wahlspruch)
        registry.resolve_tables()
        registry.init_db_tables()
        
        return registry.get_environment(autocommit=True)
    
    # ==================== USER METHODS ====================
    
    def create_new_user(self, nickname: str, password: str) -> bool:
        """User erstellen"""
        try:
            existing = self.env["user"].search([("nickname", "=", nickname)])
            if existing:
                return False
            
            user_data = {
                "nickname": nickname,
                "password": password,
                "points": 0,
                "registered_at": datetime.now()
            }
            self.env["user"].create(user_data)
            return True
        except Exception as e:
            logger.exception(f"Fehler beim Erstellen des Users: {e}")
            raise e
    
    def get_user_by_nickname(self, nickname: str):
        """User by Nickname"""
        return self.env["user"].search([("nickname", "=", nickname)])
    
    def get_user_by_id(self, user_id: int):
        """User by ID"""
        return self.env["user"].search([("id", "=", user_id)])
    
    def get_user_by_session_token(self, session_token: str):
        """User by Session Token"""
        return self.env["user"].search([("session_token", "=", session_token)])
    
    def update_user_points(self, user_id: int, new_points: int) -> bool:
        """User Punkte updaten"""
        try:
            user = self.env["user"].search([("id", "=", user_id)])
            if not user:
                return False
            
            user.write({"points": new_points})
            return True
        except Exception as e:
            logger.exception(f"Fehler beim Updaten der Punkte: {e}")
            raise e
    
    def update_user_session(self, user_id: int, session_token: str, ip_address: str) -> bool:
        """User Session updaten"""
        try:
            user = self.env["user"].search([("id", "=", user_id)])
            if not user:
                return False
            
            user.write({
                "session_token": session_token,
                "last_login_ip": ip_address,
                "last_login_time": datetime.now()
            })
            return True
        except Exception as e:
            logger.exception(f"Fehler beim Updaten der Session: {e}")
            raise e
    
    def get_top_users(self, limit: int = 10):
        """Top Users by Points"""
        return self.env["user"].search([], order_by="points", order_asc=False, limit=limit)
    
    # ==================== WAHLSPRUCH METHODS ====================
    
    def create_new_wahlspruch(self, text: str, partei: str, wahl: str = None, 
                             datum = None, quelle: str = None) -> bool:
        """Wahlspruch erstellen"""
        try:
            existing = self.env["wahlspruch"].search([("spruch", "=", text)])
            if existing:
                return False
            
            wahlspruch_data = {
                "spruch": text,
                "partei": partei,
                "wahl": wahl,
                "datum": datum,
                "quelle": quelle
            }
            self.env["wahlspruch"].create(wahlspruch_data)
            return True
        except Exception as e:
            logger.exception(f"Fehler beim Erstellen des Wahlspruchs: {e}")
            raise e
    
    def get_all_wahlsprueche(self):
        """Alle Wahlsprüche"""
        return self.env["wahlspruch"].search([])
    
    def get_alle_parteien(self) -> list:
        """Alle einzigartigen Parteien"""
        wahlsprueche = self.env["wahlspruch"].search([])
        parteien = set()
        
        for wahlspruch in wahlsprueche:
            if wahlspruch.partei:
                parteien.add(wahlspruch.partei)
        
        return sorted(list(parteien))
    
    def get_wahlspruch_by_id(self, wahlspruch_id: int):
        """Wahlspruch by ID"""
        return self.env["wahlspruch"].search([("id", "=", wahlspruch_id)])
    
    def get_random_wahlspruch(self):
        """Zufälliger Wahlspruch"""
        wahlsprueche = self.env["wahlspruch"].search([])
        if wahlsprueche:
            return random.choice(list(wahlsprueche))
        return None
    
    def count_wahlsprueche(self) -> int:
        """Anzahl Wahlsprüche"""
        return self.env["wahlspruch"].search_count([])
