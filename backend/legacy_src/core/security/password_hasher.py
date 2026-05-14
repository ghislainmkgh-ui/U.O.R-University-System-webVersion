"""Gestion sécurisée des mots de passe avec bcrypt"""
import bcrypt
import secrets
import string
from config.settings import PASSWORD_MIN_LENGTH


class PasswordHasher:
    """Service de hachage et validation de mots de passe"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hache un mot de passe avec bcrypt
        
        Args:
            password: Mot de passe en clair
            
        Returns:
            Hash bcrypt du mot de passe
        """
        if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
        
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode(), salt).decode()
    
    @staticmethod
    def verify_password(password: str, hash_stored: str) -> bool:
        """
        Vérifie un mot de passe contre son hash
        
        Args:
            password: Mot de passe en clair
            hash_stored: Hash stocké en base
            
        Returns:
            True si le mot de passe correspond, False sinon
        """
        try:
            return bcrypt.checkpw(password.encode(), hash_stored.encode())
        except Exception:
            return False
    
    @staticmethod
    def generate_numeric_password(length: int = 6) -> str:
        """
        Génère un mot de passe numérique sécurisé
        
        Args:
            length: Longueur du mot de passe (défaut 6)
            
        Returns:
            Mot de passe numérique aléatoire
        """
        if length < PASSWORD_MIN_LENGTH:
            length = PASSWORD_MIN_LENGTH
        
        digits = string.digits
        return ''.join(secrets.choice(digits) for _ in range(length))
    
    @staticmethod
    def generate_unique_password(existing_passwords: list, length: int = 6) -> str:
        """
        Génère un mot de passe numérique unique
        
        Args:
            existing_passwords: Liste des mots de passe existants
            length: Longueur du mot de passe
            
        Returns:
            Mot de passe unique
        """
        existing_hashes = set(existing_passwords) if existing_passwords else set()
        
        while True:
            pwd = PasswordHasher.generate_numeric_password(length)
            if pwd not in existing_hashes:
                return pwd
