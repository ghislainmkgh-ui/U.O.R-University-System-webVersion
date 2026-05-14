"""Modèle Note Académique"""
from core.models.base_model import BaseModel
from datetime import date
from decimal import Decimal


class AcademicRecord(BaseModel):
    """Modèle pour les Notes Académiques des Étudiants"""
    
    def __init__(self, student_id: int, promotion_id: int, course_name: str,
                 course_code: str = None, credits: int = 0, grade: Decimal = None,
                 grade_letter: str = None, semester: str = 'Annual',
                 academic_year_id: int = None, exam_date: date = None,
                 professor_name: str = None, status: str = 'IN_PROGRESS',
                 remarks: str = None, is_transferred: bool = False,
                 source_university: str = None):
        super().__init__()
        self.id: int = None
        self.student_id: int = student_id
        self.promotion_id: int = promotion_id
        self.academic_year_id: int = academic_year_id
        self.course_name: str = course_name
        self.course_code: str = course_code
        self.credits: int = credits
        self.grade: Decimal = grade
        self.grade_letter: str = grade_letter
        self.semester: str = semester  # '1', '2', 'Annual'
        self.exam_date: date = exam_date
        self.professor_name: str = professor_name
        self.status: str = status  # 'PASSED', 'FAILED', 'IN_PROGRESS', 'VALIDATED'
        self.remarks: str = remarks
        self.is_transferred: bool = is_transferred
        self.source_university: str = source_university
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'promotion_id': self.promotion_id,
            'academic_year_id': self.academic_year_id,
            'course_name': self.course_name,
            'course_code': self.course_code,
            'credits': self.credits,
            'grade': float(self.grade) if self.grade else None,
            'grade_letter': self.grade_letter,
            'semester': self.semester,
            'exam_date': str(self.exam_date) if self.exam_date else None,
            'professor_name': self.professor_name,
            'status': self.status,
            'remarks': self.remarks,
            'is_transferred': self.is_transferred,
            'source_university': self.source_university
        }
