"""Modèle Document Étudiant"""
from core.models.base_model import BaseModel
from datetime import date
from decimal import Decimal


class StudentDocument(BaseModel):
    """Modèle pour les Documents et Ouvrages des Étudiants"""
    
    def __init__(self, student_id: int, document_type: str, title: str,
                 description: str = None, author: str = None, isbn: str = None,
                 category: str = None, file_path: str = None, file_blob: bytes = None,
                 file_size_mb: Decimal = None, issue_date: date = None,
                 return_date: date = None, status: str = 'ACTIVE',
                 library_code: str = None, is_transferred: bool = False,
                 source_university: str = None):
        super().__init__()
        self.id: int = None
        self.student_id: int = student_id
        self.document_type: str = document_type  # 'BOOK', 'THESIS', 'REPORT', 'CERTIFICATE', 'DIPLOMA', 'OTHER'
        self.title: str = title
        self.description: str = description
        self.author: str = author
        self.isbn: str = isbn
        self.category: str = category
        self.file_path: str = file_path
        self.file_blob: bytes = file_blob
        self.file_size_mb: Decimal = file_size_mb
        self.issue_date: date = issue_date
        self.return_date: date = return_date
        self.status: str = status  # 'ACTIVE', 'RETURNED', 'LOST', 'TRANSFERRED'
        self.library_code: str = library_code
        self.is_transferred: bool = is_transferred
        self.source_university: str = source_university
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire (sans le blob pour économiser)"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'document_type': self.document_type,
            'title': self.title,
            'description': self.description,
            'author': self.author,
            'isbn': self.isbn,
            'category': self.category,
            'file_path': self.file_path,
            'file_size_mb': float(self.file_size_mb) if self.file_size_mb else None,
            'issue_date': str(self.issue_date) if self.issue_date else None,
            'return_date': str(self.return_date) if self.return_date else None,
            'status': self.status,
            'library_code': self.library_code,
            'is_transferred': self.is_transferred,
            'source_university': self.source_university
        }
