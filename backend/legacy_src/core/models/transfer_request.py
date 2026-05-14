"""Modèle Demande de Transfert"""
from core.models.base_model import BaseModel
from datetime import datetime


class TransferRequest(BaseModel):
    """Modèle pour les Demandes de Transfert en Attente"""
    
    def __init__(self, request_code: str, transfer_type: str, source_university: str,
                 requested_date: datetime = None, student_id: int = None,
                 external_student_number: str = None, external_firstname: str = None,
                 external_lastname: str = None, external_email: str = None,
                 external_phone: str = None, source_university_code: str = None,
                 destination_university: str = None, destination_university_code: str = None,
                 target_faculty_id: int = None, target_department_id: int = None,
                 target_promotion_id: int = None, status: str = 'PENDING_REVIEW',
                 reviewed_date: datetime = None, reviewed_by: str = None,
                 received_data_json: str = None, approval_notes: str = None):
        super().__init__()
        self.id: int = None
        self.request_code: str = request_code
        self.transfer_type: str = transfer_type  # 'OUTGOING', 'INCOMING'
        self.student_id: int = student_id
        self.external_student_number: str = external_student_number
        self.external_firstname: str = external_firstname
        self.external_lastname: str = external_lastname
        self.external_email: str = external_email
        self.external_phone: str = external_phone
        self.source_university: str = source_university
        self.source_university_code: str = source_university_code
        self.destination_university: str = destination_university
        self.destination_university_code: str = destination_university_code
        self.target_faculty_id: int = target_faculty_id
        self.target_department_id: int = target_department_id
        self.target_promotion_id: int = target_promotion_id
        self.status: str = status  # 'PENDING_REVIEW', 'APPROVED', 'REJECTED', 'COMPLETED'
        self.requested_date: datetime = requested_date if requested_date else datetime.now()
        self.reviewed_date: datetime = reviewed_date
        self.reviewed_by: str = reviewed_by
        self.received_data_json: str = received_data_json
        self.approval_notes: str = approval_notes
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'request_code': self.request_code,
            'transfer_type': self.transfer_type,
            'student_id': self.student_id,
            'external_student_number': self.external_student_number,
            'external_firstname': self.external_firstname,
            'external_lastname': self.external_lastname,
            'external_email': self.external_email,
            'external_phone': self.external_phone,
            'source_university': self.source_university,
            'source_university_code': self.source_university_code,
            'destination_university': self.destination_university,
            'destination_university_code': self.destination_university_code,
            'target_faculty_id': self.target_faculty_id,
            'target_department_id': self.target_department_id,
            'target_promotion_id': self.target_promotion_id,
            'status': self.status,
            'requested_date': str(self.requested_date) if self.requested_date else None,
            'reviewed_date': str(self.reviewed_date) if self.reviewed_date else None,
            'reviewed_by': self.reviewed_by,
            'approval_notes': self.approval_notes
        }
