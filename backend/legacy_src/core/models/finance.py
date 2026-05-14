"""Modèle Profil Financier"""
from core.models.base_model import BaseModel
from decimal import Decimal


class FinanceProfile(BaseModel):
    """Modèle pour les Profils Financiers des Étudiants"""
    
    def __init__(self, student_id: int, threshold_required: Decimal = Decimal("0.00")):
        super().__init__()
        self.id: int = None
        self.student_id: int = student_id
        self.amount_paid: Decimal = Decimal("0.00")
        self.threshold_required: Decimal = threshold_required
        self.last_payment_date = None
        self.is_eligible: bool = False
    
    def is_threshold_reached(self) -> bool:
        """Vérifie si le seuil financier est atteint"""
        self.is_eligible = self.amount_paid >= self.threshold_required
        return self.is_eligible
    
    def get_remaining_amount(self) -> Decimal:
        """Retourne le montant restant à payer"""
        remaining = self.threshold_required - self.amount_paid
        return max(remaining, Decimal("0.00"))
