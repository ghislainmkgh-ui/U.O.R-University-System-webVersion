"""Modèle Historique de Transfert"""
from core.models.base_model import BaseModel
from datetime import datetime


class TransferHistory(BaseModel):
    """Modèle pour l'Historique des Transferts Inter-Universitaires"""
    
    def __init__(self, transfer_code: str, student_id: int, transfer_type: str,
                 transfer_date: datetime, source_university: str = None,
                 source_university_code: str = None, destination_university: str = None,
                 destination_university_code: str = None, status: str = 'PENDING',
                 records_count: int = 0, documents_count: int = 0,
                 total_credits: int = 0, initiated_by: str = None,
                 validated_by: str = None, validation_date: datetime = None,
                 api_endpoint: str = None, auth_token_hash: str = None,
                 transfer_data_json: str = None, response_json: str = None,
                 error_message: str = None, notes: str = None):
        super().__init__()
        self.id: int = None
        self.transfer_code: str = transfer_code
        self.student_id: int = student_id
        self.transfer_type: str = transfer_type  # 'OUTGOING', 'INCOMING'
        self.source_university: str = source_university
        self.source_university_code: str = source_university_code
        self.destination_university: str = destination_university
        self.destination_university_code: str = destination_university_code
        self.transfer_date: datetime = transfer_date
        self.status: str = status  # 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'REJECTED', 'CANCELLED'
        self.records_count: int = records_count
        self.documents_count: int = documents_count
        self.total_credits: int = total_credits
        self.initiated_by: str = initiated_by
        self.validated_by: str = validated_by
        self.validation_date: datetime = validation_date
        self.api_endpoint: str = api_endpoint
        self.auth_token_hash: str = auth_token_hash
        self.transfer_data_json: str = transfer_data_json
        self.response_json: str = response_json
        self.error_message: str = error_message
        self.notes: str = notes
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'transfer_code': self.transfer_code,
            'student_id': self.student_id,
            'transfer_type': self.transfer_type,
            'source_university': self.source_university,
            'source_university_code': self.source_university_code,
            'destination_university': self.destination_university,
            'destination_university_code': self.destination_university_code,
            'transfer_date': str(self.transfer_date) if self.transfer_date else None,
            'status': self.status,
            'records_count': self.records_count,
            'documents_count': self.documents_count,
            'total_credits': self.total_credits,
            'initiated_by': self.initiated_by,
            'validated_by': self.validated_by,
            'validation_date': str(self.validation_date) if self.validation_date else None,
            'error_message': self.error_message,
            'notes': self.notes
        }
