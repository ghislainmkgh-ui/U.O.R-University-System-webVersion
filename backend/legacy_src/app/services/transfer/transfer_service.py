"""Service de Transfert Inter-Universitaire"""
import json
import hashlib
import uuid
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from decimal import Decimal

from core.database.connection import DatabaseConnection
from core.models.student import Student
from core.models.academic_record import AcademicRecord
from core.models.student_document import StudentDocument
from core.models.transfer_history import TransferHistory
from core.models.transfer_request import TransferRequest
import logging

logger = logging.getLogger(__name__)


class JSONSerializableEncoder(json.JSONEncoder):
    """Encodeur JSON personnalisé pour gérer les types non sérialisables"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class TransferService:
    def update_delivery_status(self, transfer_code: str, status: str, message: str = None) -> bool:
        """Met à jour le statut de livraison et le message dans transfer_history"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                UPDATE transfer_history
                SET delivery_status = %s, delivery_message = %s, updated_at = NOW()
                WHERE transfer_code = %s
            """
            cursor.execute(query, (status, message, transfer_code))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erreur mise à jour statut livraison: {e}", exc_info=True)
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.close_connection(conn)

    """Service pour gérer les transferts de données étudiantes entre universités"""
    def __init__(self):
        self.db = DatabaseConnection()
        self.university_code = "UOR"  # Code de notre université
        self.university_name = "Université Officielle de Ruwenzori"
    
    # ========== EXPORT / OUTGOING TRANSFERS ==========
    
    def prepare_student_transfer_package(self, student_id: int, include_documents: bool = True) -> Dict:
        """
        Prépare le package complet de données d'un étudiant pour transfert
        Exclut les données de paiement
        
        Returns:
            Dict contenant toutes les données formatées
        """
        try:
            logger.info(f"Préparation du package de transfert pour l'étudiant ID: {student_id}")
            
            # 1. Récupérer les informations de l'étudiant
            student_data = self._get_student_data(student_id)
            if not student_data:
                logger.error(f"Étudiant {student_id} non trouvé")
                return None
            
            # 2. Récupérer les notes académiques
            academic_records = self._get_student_academic_records(student_id)
            
            # 3. Récupérer les documents et ouvrages
            documents = []
            if include_documents:
                documents = self._get_student_documents(student_id)
            
            # 4. Calculer les statistiques
            total_credits = sum(rec.get('credits', 0) for rec in academic_records)
            average_grade = self._calculate_average_grade(academic_records)
            
            # 5. Créer le package
            transfer_code = self._generate_transfer_code(student_id)
            package = {
                "transfer_metadata": {
                    "transfer_code": transfer_code,
                    "source_university": self.university_name,
                    "source_university_code": self.university_code,
                    "transfer_date": datetime.now().isoformat(),
                    "format_version": "1.0",
                    "certification": "Certifié par le Bureau Académique de l'U.O.R"
                },
                "student_info": student_data,
                "academic_records": {
                    "total_courses": len(academic_records),
                    "total_credits": total_credits,
                    "average_grade": average_grade,
                    "records": academic_records
                },
                "documents": {
                    "total_documents": len(documents),
                    "items": documents
                },
                "academic_profile": {
                    "faculty": student_data.get('faculty_name'),
                    "department": student_data.get('department_name'),
                    "promotion": student_data.get('promotion_name'),
                    "year": student_data.get('promotion_year')
                }
            }
            
            logger.info(f"Package préparé avec succès: {len(academic_records)} notes, {len(documents)} documents")
            return package
            
        except Exception as e:
            logger.error(f"Erreur lors de la préparation du package de transfert: {e}", exc_info=True)
            return None
    
    def initiate_outgoing_transfer(self, student_id: int, destination_university: str,
                                  destination_code: str, initiated_by: str,
                                  include_documents: bool = True, notes: str = None) -> Tuple[bool, str]:
        """
        Initie un transfert sortant d'un étudiant
        
        Returns:
            Tuple (success: bool, transfer_code or error_message: str)
        """
        try:
            logger.info(f"Initiation du transfert sortant - Étudiant: {student_id}, Destination: {destination_university}")
            
            # 1. Préparer le package
            package = self.prepare_student_transfer_package(student_id, include_documents)
            if not package:
                return False, "Impossible de préparer les données de l'étudiant"
            
            transfer_code = package['transfer_metadata']['transfer_code']
            
            # 2. Enregistrer dans l'historique
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO transfer_history (
                    transfer_code, student_id, transfer_type, source_university,
                    source_university_code, destination_university, destination_university_code,
                    transfer_date, status, records_count, documents_count, total_credits,
                    initiated_by, transfer_data_json, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                transfer_code,
                student_id,
                'OUTGOING',
                self.university_name,
                self.university_code,
                destination_university,
                destination_code,
                datetime.now(),
                'PENDING',
                package['academic_records']['total_courses'],
                package['documents']['total_documents'],
                package['academic_records']['total_credits'],
                initiated_by,
                json.dumps(package, ensure_ascii=False, cls=JSONSerializableEncoder),
                notes
            ))
            
            conn.commit()
            logger.info(f"Transfert sortant créé avec succès: {transfer_code}")
            
            return True, transfer_code
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initiation du transfert sortant: {e}", exc_info=True)
            if conn:
                conn.rollback()
            return False, str(e)
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.close_connection(conn)
    
    # ========== IMPORT / INCOMING TRANSFERS ==========
    
    def receive_transfer_request(self, transfer_data: Dict, target_promotion_id: int = None) -> Tuple[bool, str]:
        """
        Reçoit une demande de transfert d'une autre université
        Crée une demande en attente de validation
        
        Returns:
            Tuple (success: bool, request_code or error_message: str)
        """
        try:
            logger.info(f"Réception d'une demande de transfert depuis {transfer_data.get('transfer_metadata', {}).get('source_university', 'Unknown')}")
            
            # Valider les données reçues
            if not self._validate_transfer_data(transfer_data):
                return False, "Données de transfert invalides ou incomplètes"
            
            metadata = transfer_data.get('transfer_metadata', {})
            student_info = transfer_data.get('student_info', {})
            
            # Générer un code de demande
            request_code = f"REQ-{uuid.uuid4().hex[:12].upper()}"
            
            # Enregistrer la demande
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO transfer_request (
                    request_code, transfer_type, external_student_number,
                    external_firstname, external_lastname, external_email, external_phone,
                    source_university, source_university_code,
                    destination_university, destination_university_code,
                    target_promotion_id, status, requested_date, received_data_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                request_code,
                'INCOMING',
                student_info.get('student_number'),
                student_info.get('firstname'),
                student_info.get('lastname'),
                student_info.get('email'),
                student_info.get('phone_number'),
                metadata.get('source_university'),
                metadata.get('source_university_code'),
                self.university_name,
                self.university_code,
                target_promotion_id,
                'PENDING_REVIEW',
                datetime.now(),
                json.dumps(transfer_data, ensure_ascii=False, cls=JSONSerializableEncoder)
            ))
            
            conn.commit()
            logger.info(f"Demande de transfert enregistrée: {request_code}")
            
            return True, request_code
            
        except Exception as e:
            logger.error(f"Erreur lors de la réception de la demande de transfert: {e}", exc_info=True)
            if conn:
                conn.rollback()
            return False, str(e)
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.close_connection(conn)
    
    def approve_incoming_transfer(self, request_id: int, approved_by: str,
                                 target_promotion_id: int, approval_notes: str = None) -> Tuple[bool, str]:
        """
        Approuve une demande de transfert entrant et crée l'étudiant + importe les données
        
        Returns:
            Tuple (success: bool, student_id or error_message: str)
        """
        try:
            logger.info(f"Approbation de la demande de transfert ID: {request_id}")
            
            # 1. Récupérer la demande
            request_data = self._get_transfer_request(request_id)
            if not request_data:
                return False, "Demande de transfert non trouvée"
            
            if request_data['status'] != 'PENDING_REVIEW':
                return False, f"La demande est déjà {request_data['status']}"
            
            # 2. Désérialiser les données JSON
            transfer_data = json.loads(request_data['received_data_json'])
            student_info = transfer_data.get('student_info', {})
            academic_records = transfer_data.get('academic_records', {}).get('records', [])
            documents = transfer_data.get('documents', {}).get('items', [])
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # 3. Créer l'étudiant
            student_number = self._generate_student_number()
            insert_student = """
                INSERT INTO student (
                    student_number, firstname, lastname, email, phone_number,
                    promotion_id, password_hash, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Mot de passe temporaire (doit être changé par l'étudiant)
            temp_password_hash = hashlib.sha256("ChangeMe123!".encode()).hexdigest()
            
            cursor.execute(insert_student, (
                student_number,
                student_info.get('firstname'),
                student_info.get('lastname'),
                student_info.get('email'),
                student_info.get('phone_number'),
                target_promotion_id,
                temp_password_hash,
                True
            ))
            
            student_id = cursor.lastrowid
            logger.info(f"Étudiant créé avec ID: {student_id}, Numéro: {student_number}")
            
            # 4. Importer les notes académiques
            records_imported = 0
            for record in academic_records:
                try:
                    insert_record = """
                        INSERT INTO academic_record (
                            student_id, promotion_id, course_name, course_code, credits,
                            grade, grade_letter, semester, status, is_transferred,
                            source_university
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_record, (
                        student_id,
                        target_promotion_id,
                        record.get('course_name'),
                        record.get('course_code'),
                        record.get('credits', 0),
                        record.get('grade'),
                        record.get('grade_letter'),
                        record.get('semester', 'Annual'),
                        'VALIDATED',  # Les notes transférées sont validées
                        True,
                        transfer_data['transfer_metadata']['source_university']
                    ))
                    records_imported += 1
                except Exception as e:
                    logger.warning(f"Erreur lors de l'import d'une note: {e}")
            
            # 5. Importer les documents
            documents_imported = 0
            for doc in documents:
                try:
                    insert_doc = """
                        INSERT INTO student_document (
                            student_id, document_type, title, description, author,
                            isbn, category, status, is_transferred, source_university
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_doc, (
                        student_id,
                        doc.get('document_type', 'OTHER'),
                        doc.get('title'),
                        doc.get('description'),
                        doc.get('author'),
                        doc.get('isbn'),
                        doc.get('category'),
                        'TRANSFERRED',
                        True,
                        transfer_data['transfer_metadata']['source_university']
                    ))
                    documents_imported += 1
                except Exception as e:
                    logger.warning(f"Erreur lors de l'import d'un document: {e}")
            
            # 6. Créer l'historique de transfert
            transfer_code = transfer_data['transfer_metadata']['transfer_code']
            insert_history = """
                INSERT INTO transfer_history (
                    transfer_code, student_id, transfer_type, source_university,
                    source_university_code, destination_university, destination_university_code,
                    transfer_date, status, records_count, documents_count,
                    validated_by, validation_date, transfer_data_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_history, (
                transfer_code,
                student_id,
                'INCOMING',
                transfer_data['transfer_metadata']['source_university'],
                transfer_data['transfer_metadata']['source_university_code'],
                self.university_name,
                self.university_code,
                datetime.now(),
                'COMPLETED',
                records_imported,
                documents_imported,
                approved_by,
                datetime.now(),
                json.dumps(transfer_data, ensure_ascii=False, cls=JSONSerializableEncoder)
            ))
            
            # 7. Mettre à jour la demande
            update_request = """
                UPDATE transfer_request
                SET status = 'COMPLETED', student_id = %s, reviewed_by = %s,
                    reviewed_date = %s, approval_notes = %s
                WHERE id = %s
            """
            cursor.execute(update_request, (
                student_id, approved_by, datetime.now(), approval_notes, request_id
            ))
            
            conn.commit()
            logger.info(f"Transfert entrant complété: {records_imported} notes, {documents_imported} documents importés")
            
            return True, str(student_id)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'approbation du transfert: {e}", exc_info=True)
            if conn:
                conn.rollback()
            return False, str(e)
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.close_connection(conn)
    
    def reject_incoming_transfer(self, request_id: int, rejected_by: str, rejection_reason: str) -> bool:
        """Rejette une demande de transfert entrant"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            update_query = """
                UPDATE transfer_request
                SET status = 'REJECTED', reviewed_by = %s, reviewed_date = %s, approval_notes = %s
                WHERE id = %s
            """
            cursor.execute(update_query, (rejected_by, datetime.now(), rejection_reason, request_id))
            
            conn.commit()
            logger.info(f"Demande de transfert {request_id} rejetée par {rejected_by}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du rejet de la demande: {e}", exc_info=True)
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.close_connection(conn)
    
    # ========== QUERY METHODS ==========
    
    def get_pending_transfer_requests(self) -> List[Dict]:
        """Récupère toutes les demandes de transfert en attente"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT tr.*, 
                       f.name as target_faculty_name,
                       d.name as target_department_name,
                       p.name as target_promotion_name
                FROM transfer_request tr
                LEFT JOIN promotion p ON tr.target_promotion_id = p.id
                LEFT JOIN department d ON p.department_id = d.id
                LEFT JOIN faculty f ON d.faculty_id = f.id
                WHERE tr.status = 'PENDING_REVIEW'
                ORDER BY tr.requested_date DESC
            """
            
            cursor.execute(query)
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des demandes: {e}", exc_info=True)
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.close_connection(conn)
    
    def get_transfer_history(self, student_id: int = None, limit: int = 50) -> List[Dict]:
        """Récupère l'historique des transferts"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            if student_id:
                query = """
                    SELECT th.*, s.student_number, s.firstname, s.lastname
                    FROM transfer_history th
                    LEFT JOIN student s ON th.student_id = s.id
                    WHERE th.student_id = %s
                    ORDER BY th.transfer_date DESC
                    LIMIT %s
                """
                cursor.execute(query, (student_id, limit))
            else:
                query = """
                    SELECT th.*, s.student_number, s.firstname, s.lastname
                    FROM transfer_history th
                    LEFT JOIN student s ON th.student_id = s.id
                    ORDER BY th.transfer_date DESC
                    LIMIT %s
                """
                cursor.execute(query, (limit,))
            
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique: {e}", exc_info=True)
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.close_connection(conn)
    
    def get_student_academic_summary(self, student_id: int) -> Dict:
        """Récupère le résumé académique d'un étudiant pour affichage"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    COUNT(*) as total_courses,
                    SUM(credits) as total_credits,
                    AVG(grade) as average_grade,
                    SUM(CASE WHEN status = 'PASSED' THEN 1 ELSE 0 END) as courses_passed,
                    SUM(CASE WHEN is_transferred = TRUE THEN 1 ELSE 0 END) as transferred_courses
                FROM academic_record
                WHERE student_id = %s
            """
            cursor.execute(query, (student_id,))
            summary = cursor.fetchone()
            
            # Obtenir les documents
            doc_query = """
                SELECT COUNT(*) as total_documents,
                       SUM(CASE WHEN is_transferred = TRUE THEN 1 ELSE 0 END) as transferred_documents
                FROM student_document
                WHERE student_id = %s
            """
            cursor.execute(doc_query, (student_id,))
            doc_summary = cursor.fetchone()
            
            if summary:
                summary.update(doc_summary)
            
            return summary if summary else {}
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du résumé: {e}", exc_info=True)
            return {}
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.close_connection(conn)
    
    # ========== HELPER METHODS ==========
    
    def _get_student_data(self, student_id: int) -> Optional[Dict]:
        """Récupère les données complètes d'un étudiant"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT s.*, 
                       f.name as faculty_name, f.code as faculty_code,
                       d.name as department_name, d.code as department_code,
                       p.name as promotion_name, p.year as promotion_year
                FROM student s
                LEFT JOIN promotion p ON s.promotion_id = p.id
                LEFT JOIN department d ON p.department_id = d.id
                LEFT JOIN faculty f ON d.faculty_id = f.id
                WHERE s.id = %s
            """
            cursor.execute(query, (student_id,))
            result = cursor.fetchone()
            
            if result:
                # Enlever les champs sensibles
                result.pop('password_hash', None)
                result.pop('face_encoding', None)
                result.pop('passport_photo_blob', None)
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données étudiant: {e}", exc_info=True)
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.close_connection(conn)
    
    def _get_student_academic_records(self, student_id: int) -> List[Dict]:
        """Récupère toutes les notes d'un étudiant"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT course_name, course_code, credits, grade, grade_letter,
                       semester, exam_date, professor_name, status, remarks
                FROM academic_record
                WHERE student_id = %s
                ORDER BY exam_date DESC
            """
            cursor.execute(query, (student_id,))
            records = cursor.fetchall()
            
            # Convertir les Decimal en float pour JSON
            for record in records:
                if record.get('grade'):
                    record['grade'] = float(record['grade'])
                if record.get('exam_date'):
                    record['exam_date'] = str(record['exam_date'])
            
            return records
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des notes: {e}", exc_info=True)
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.close_connection(conn)
    
    def _get_student_documents(self, student_id: int) -> List[Dict]:
        """Récupère tous les documents d'un étudiant (sans les blobs)"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT document_type, title, description, author, isbn, category,
                       file_size_mb, issue_date, return_date, status, library_code
                FROM student_document
                WHERE student_id = %s AND status IN ('ACTIVE', 'RETURNED')
                ORDER BY issue_date DESC
            """
            cursor.execute(query, (student_id,))
            documents = cursor.fetchall()
            
            # Convertir les dates
            for doc in documents:
                if doc.get('file_size_mb'):
                    doc['file_size_mb'] = float(doc['file_size_mb'])
                if doc.get('issue_date'):
                    doc['issue_date'] = str(doc['issue_date'])
                if doc.get('return_date'):
                    doc['return_date'] = str(doc['return_date'])
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des documents: {e}", exc_info=True)
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.close_connection(conn)
    
    def _get_transfer_request(self, request_id: int) -> Optional[Dict]:
        """Récupère une demande de transfert"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = "SELECT * FROM transfer_request WHERE id = %s"
            cursor.execute(query, (request_id,))
            return cursor.fetchone()
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la demande: {e}", exc_info=True)
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.close_connection(conn)
    
    def _generate_transfer_code(self, student_id: int) -> str:
        """Génère un code unique de transfert"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"{self.university_code}-{student_id}-{timestamp}"
    
    def _generate_student_number(self) -> str:
        """Génère un nouveau numéro d'étudiant unique"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_part = uuid.uuid4().hex[:6].upper()
        return f"TRF{timestamp[-8:]}{random_part}"
    
    def _calculate_average_grade(self, records: List[Dict]) -> Optional[float]:
        """Calcule la moyenne des notes"""
        grades = [float(r['grade']) for r in records if r.get('grade') is not None]
        if not grades:
            return None
        return round(sum(grades) / len(grades), 2)
    
    def _validate_transfer_data(self, data: Dict) -> bool:
        """Valide la structure des données de transfert"""
        required_fields = ['transfer_metadata', 'student_info', 'academic_records']
        
        for field in required_fields:
            if field not in data:
                logger.warning(f"Champ requis manquant: {field}")
                return False
        
        metadata = data.get('transfer_metadata', {})
        if not metadata.get('transfer_code') or not metadata.get('source_university'):
            logger.warning("Métadonnées de transfert invalides")
            return False
        
        student_info = data.get('student_info', {})
        if not student_info.get('firstname') or not student_info.get('lastname'):
            logger.warning("Informations étudiant incomplètes")
            return False
        
        return True

    def get_partner_api_url(self, university_code: str) -> Optional[str]:
        """Récupère l'URL d'API d'une université partenaire"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT api_url FROM partner_university WHERE university_code = %s", (university_code,))
            result = cursor.fetchone()
            return result['api_url'] if result and result['api_url'] else None
        except Exception as e:
            logger.error(f"Erreur récupération API partenaire: {e}", exc_info=True)
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.close_connection(conn)

    def set_partner_api_url(self, university_code: str, api_url: str) -> bool:
        """Met à jour l'URL d'API d'une université partenaire"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE partner_university SET api_url = %s WHERE university_code = %s", (api_url, university_code))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erreur mise à jour API partenaire: {e}", exc_info=True)
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.close_connection(conn)
