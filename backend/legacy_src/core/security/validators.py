"""Validateurs pour les données d'entrée"""
import re
from typing import Tuple


class Validators:
    """Validateurs pour sécuriser les entrées utilisateur"""
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Valide le format d'un email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return True, "Email valid"
        return False, "Invalid email format"
    
    @staticmethod
    def validate_numeric_password(password: str, min_length: int = 6) -> Tuple[bool, str]:
        """Valide un mot de passe numérique"""
        if not password:
            return False, "Password cannot be empty"
        if not password.isdigit():
            return False, "Password must contain only digits"
        if len(password) < min_length:
            return False, f"Password must be at least {min_length} characters"
        return True, "Password valid"
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        """Valide un numéro de téléphone"""
        pattern = r'^\+?1?\d{9,15}$'
        if re.match(pattern, phone.replace(" ", "")):
            return True, "Phone valid"
        return False, "Invalid phone format"
    
    @staticmethod
    def sanitize_input(data: str, max_length: int = 255) -> str:
        """
        Nettoie les données d'entrée pour éviter les injections
        
        Args:
            data: Données à nettoyer
            max_length: Longueur maximale
            
        Returns:
            Données nettoyées
        """
        if not isinstance(data, str):
            return ""
        
        # Supprimer les espaces avant/après
        data = data.strip()
        
        # Limiter la longueur
        if len(data) > max_length:
            data = data[:max_length]
        
        # Épurer les caractères dangereux
        dangerous_chars = ['<', '>', '"', "'", '\\', ';', '--', '/*', '*/']
        for char in dangerous_chars:
            data = data.replace(char, '')
        
        return data
    
    @staticmethod
    def validate_student_number(number: str) -> Tuple[bool, str]:
        """Valide un numéro d'étudiant"""
        if not number or len(number) < 3:
            return False, "Invalid student number"
        return True, "Student number valid"
