"""Service de notification par email et WhatsApp"""
import logging
import smtplib
import os
import html
import requests
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import (
    EMAIL_SERVICE, EMAIL_ADDRESS, EMAIL_PASSWORD, 
    WHATSAPP_ACCOUNT_SID, WHATSAPP_AUTH_TOKEN, WHATSAPP_FROM,
    ULTRAMSG_INSTANCE_ID, ULTRAMSG_TOKEN,
    EMAIL_LOGO_PATH
)

try:
    from twilio.rest import Client
except ImportError:  # pragma: no cover - optional dependency
    Client = None

logger = logging.getLogger(__name__)


class NotificationService:
    """Service pour envoyer des notifications"""
    
    def __init__(self):
        self.email_address = EMAIL_ADDRESS
        self.email_password = EMAIL_PASSWORD
        self.whatsapp_sid = WHATSAPP_ACCOUNT_SID
        self.whatsapp_token = WHATSAPP_AUTH_TOKEN
        self.whatsapp_from = WHATSAPP_FROM
        self.ultramsg_instance = ULTRAMSG_INSTANCE_ID
        self.ultramsg_token = ULTRAMSG_TOKEN
        self.email_logo_path = EMAIL_LOGO_PATH
        
        # Log configuration status
        logger.info(f"NotificationService initialized - Email: {bool(self.email_address)}, Ultramsg: {bool(self.ultramsg_instance)}")
        if not self.ultramsg_instance or not self.ultramsg_token:
            logger.warning(f"Ultramsg not fully configured - Instance: {bool(self.ultramsg_instance)}, Token: {bool(self.ultramsg_token)}")

    def get_channel_status(self) -> dict:
        """Retourne l'état de configuration des notifications"""
        email_ok = bool(self.email_address and self.email_password)
        whatsapp_ok = bool(self.ultramsg_instance and self.ultramsg_token)
        return {
            "email_configured": email_ok,
            "whatsapp_configured": whatsapp_ok
        }

    def _normalize_notification_text(self, text: str) -> str:
        """Normalise le texte pour un rendu cohérent Email/WhatsApp."""
        if text is None:
            return ""
        # Supprimer les espaces de fin de ligne sans casser la structure
        lines = [line.rstrip() for line in str(text).splitlines()]
        # Réduire les blocs de lignes vides successives (max 1 ligne vide)
        normalized = []
        empty_streak = 0
        for line in lines:
            if line.strip() == "":
                empty_streak += 1
                if empty_streak > 1:
                    continue
            else:
                empty_streak = 0
            normalized.append(line)
        return "\n".join(normalized).strip()

    def _build_html_from_plain_text(self, body: str) -> str:
        """Construit un HTML lisible à partir du texte brut pour garder la même structure."""
        normalized = self._normalize_notification_text(body)
        escaped = html.escape(normalized)
        return (
            "<div style=\"font-family:Arial, sans-serif; color:#111; line-height:1.5;\">"
            "<div style=\"background:#f8fafc; border:1px solid #e5e7eb; border-radius:10px; padding:14px;\">"
            f"<pre style=\"margin:0; white-space:pre-wrap; word-break:break-word; font-family:Arial, sans-serif; font-size:14px;\">{escaped}</pre>"
            "</div>"
            "</div>"
        )
    
    def send_payment_notification(self, student_email: str, student_phone: str,
                                 student_name: str, amount_paid: float,
                                 remaining_amount: float, final_fee: float,
                                 threshold_amount: float = None,
                                 threshold_reached: bool = None,
                                 promotion_info: str = None) -> bool:
        """Envoie une notification de paiement par email et WhatsApp
        
        Args:
            promotion_info: Chaîne formatée "Faculté / Département / Promotion" pour affichage
        """
        try:
            logger.info(f"Sending payment notification to {student_email} / {student_phone}")
            amount_paid_usd = float(amount_paid)
            remaining_usd = float(max(remaining_amount, 0))
            final_fee_usd = float(final_fee)
            threshold_usd = float(threshold_amount) if threshold_amount is not None else None

            completion_msg = ""
            if remaining_amount <= 0:
                completion_msg = "\n\nFélicitations! Vous avez fini les frais académiques."

            threshold_status = None
            if threshold_reached is not None:
                threshold_status = "Atteint" if threshold_reached else "Non atteint"

            subject = "Notification de Paiement - U.O.R"
            table_rows = []
            
            # Ajouter info de promotion en premier si disponible
            if promotion_info:
                table_rows.append(("Promotion", promotion_info))
            
            table_rows.extend([
                ("Montant payé", f"${amount_paid_usd:,.2f}"),
                ("Total des frais académiques", f"${final_fee_usd:,.2f}"),
                ("Montant restant", f"${remaining_usd:,.2f}"),
            ])
            if threshold_usd is not None:
                table_rows.append(("Seuil requis", f"${threshold_usd:,.2f}"))
            if threshold_status:
                table_rows.append(("Statut du seuil", threshold_status))

            body = f"""
Bonjour {student_name},

Votre paiement a été reçu avec succès.

{self._build_text_table(table_rows)}{completion_msg}
""".strip()

            if threshold_status == "Non atteint":
                body += "\n\nNote: Vous n'avez pas encore atteint le seuil financier requis pour l'accès aux examens."

            body += "\n\nCordialement,\nU.O.R - Système de Contrôle d'Accès"

            whatsapp_msg = self._normalize_notification_text(body)

            html_body = self._build_payment_email_html(
                student_name=student_name,
                amount_paid=amount_paid_usd,
                final_fee=final_fee_usd,
                remaining=remaining_usd,
                completion_msg=completion_msg,
                threshold_amount=threshold_usd,
                threshold_status=threshold_status,
                promotion_info=promotion_info,
            )
            email_ok = self._send_email(student_email, subject, body, html_body=html_body, logo_path=self.email_logo_path)
            logger.info(f"Email notification result: {email_ok}")
            
            whatsapp_ok = self._send_whatsapp(student_phone, whatsapp_msg)
            logger.info(f"WhatsApp notification result: {whatsapp_ok}")
            
            result = email_ok or whatsapp_ok
            logger.info(f"Payment notification overall result: {result} (email: {email_ok}, whatsapp: {whatsapp_ok})")
            return result
            
        except Exception as e:
            logger.error(f"Error preparing payment notification: {e}")
            return False
    
    def send_access_denied_notification(self, student_email: str, student_name: str,
                                       reason: str) -> bool:
        """Envoie une notification d'accès refusé"""
        try:
            subject = "Accès Refusé - U.O.R"
            body = f"""
Bonjour {student_name},

Votre tentative d'accès à la salle d'examen a été refusée.
Raison: {reason}

Veuillez contacter l'administration pour plus d'informations.

Cordialement,
U.O.R - Système de Contrôle d'Accès
            """.strip()
            
            return self._send_email(student_email, subject, body)
            
        except Exception as e:
            logger.error(f"Error preparing access denied notification: {e}")
            return False

    def send_welcome_notification(self, student_email: str, student_phone: str,
                                  student_name: str, student_number: str,
                                  threshold_required: float, final_fee: float) -> bool:
        """Envoie une notification de bienvenue au nouvel étudiant"""
        try:
            subject = "Bienvenue à U.O.R - Informations importantes"
            body = f"""
Bonjour {student_name},

Bienvenue à l'Université Officielle de Ruwenzori (U.O.R) !

Votre inscription a été enregistrée avec succès.

📋 INFORMATIONS DE VOTRE COMPTE:
• Matricule étudiant: {student_number}
• Email: {student_email}
• Téléphone: {student_phone}

💰 INFORMATIONS FINANCIÈRES:
• Seuil pour accès aux examens: ${threshold_required:,.2f}
• Frais académiques totaux: ${final_fee:,.2f}

ℹ️ IMPORTANT:
Pour accéder aux salles d'examens, vous devez:
1. Effectuer un paiement atteignant au moins le seuil requis
2. Un code d'accès vous sera automatiquement envoyé par email/WhatsApp
3. Présentez ce code au terminal d'accès le jour de l'examen

Vous recevrez une notification automatique après chaque paiement.

En cas de question, contactez l'administration.

Cordialement,
U.O.R - Système de Contrôle d'Accès
            """.strip()

            whatsapp_msg = self._normalize_notification_text(body)

            email_ok = self._send_email(student_email, subject, body)
            whatsapp_ok = self._send_whatsapp(student_phone, whatsapp_msg)

            logger.info(f"Welcome notification sent to {student_name} - Email: {email_ok}, WhatsApp: {whatsapp_ok}")
            return email_ok or whatsapp_ok

        except Exception as e:
            logger.error(f"Error preparing welcome notification: {e}")
            return False

    def send_access_code_notification(self, student_email: str, student_phone: str,
                                      student_name: str, access_code: str,
                                      code_type: str, expires_at: str) -> bool:
        """Envoie le code d'accès au étudiant par email et WhatsApp"""
        try:
            validity_msg = ""
            if code_type == 'full':
                validity_msg = "Ce code est valable durant toutes les périodes d'examens de l'année académique."
            else:
                validity_msg = "Ce code est valable jusqu'à modification du seuil financier."
            
            subject = "Votre code d'accès - U.O.R"
            body = f"""
Bonjour {student_name},

Félicitations! Votre code d'accès a été généré avec succès.

Code d'accès: {access_code}
{validity_msg}

Utilisez ce code pour accéder à la salle d'examen.

Cordialement,
U.O.R - Système de Contrôle d'Accès
            """.strip()
            
            whatsapp_msg = self._normalize_notification_text(body)
            
            email_ok = self._send_email(student_email, subject, body)
            whatsapp_ok = self._send_whatsapp(student_phone, whatsapp_msg)
            
            logger.info(f"Access code notification sent to {student_name} - Email: {email_ok}, WhatsApp: {whatsapp_ok}")
            return email_ok or whatsapp_ok
            
        except Exception as e:
            logger.error(f"Error preparing access code notification: {e}")
            return False

    def send_threshold_change_notification(self, student_email: str, student_phone: str,
                                          student_name: str, old_threshold: float = None,
                                          new_threshold: float = None, old_final_fee: float = None,
                                          new_final_fee: float = None, amount_paid: float = None,
                                          remaining_amount: float = None, threshold_reached: bool = None) -> bool:
        """Notifie l'étudiant du changement de seuil financier"""
        try:
            old_usd = float(old_threshold) if old_threshold is not None else None
            new_usd = float(new_threshold) if new_threshold is not None else None
            old_fee_usd = float(old_final_fee) if old_final_fee is not None else None
            new_fee_usd = float(new_final_fee) if new_final_fee is not None else None
            amount_paid_usd = float(amount_paid) if amount_paid is not None else None
            remaining_usd = float(remaining_amount) if remaining_amount is not None else None

            threshold_status = None
            if threshold_reached is not None:
                threshold_status = "Atteint" if threshold_reached else "Non atteint"

            subject = "Mise à jour du seuil financier - Action requise - U.O.R"
            body_lines = [
                f"Bonjour {student_name},",
                "",
                "Le seuil financier pour l'accès aux examens a été mis à jour.",
                ""
            ]

            table_rows = []
            if old_usd is not None:
                table_rows.append(("Ancien seuil", f"${old_usd:,.2f}"))
            if new_usd is not None:
                table_rows.append(("Nouveau seuil", f"${new_usd:,.2f}"))
            if old_fee_usd is not None:
                table_rows.append(("Anciens frais", f"${old_fee_usd:,.2f}"))
            if new_fee_usd is not None:
                table_rows.append(("Nouveaux frais", f"${new_fee_usd:,.2f}"))
            if amount_paid_usd is not None:
                table_rows.append(("Montant payé", f"${amount_paid_usd:,.2f}"))
            if remaining_usd is not None:
                table_rows.append(("Montant restant", f"${max(remaining_usd, 0):,.2f}"))
            if threshold_status:
                table_rows.append(("Statut du seuil", threshold_status))

            if table_rows:
                body_lines.append(self._build_text_table(table_rows))

            body_lines.extend([
                "",
                "IMPORTANT: Si vous aviez un code d'accès temporaire (paiement partiel), celui-ci a été invalidé.",
                "Veuillez effectuer un nouveau paiement pour atteindre le nouveau seuil et obtenir un code valide.",
                "",
                "Les étudiants ayant payé intégralement conservent leur code valable toute l'année.",
                "",
                "Cordialement,",
                "U.O.R - Système de Contrôle d'Accès"
            ])
            body = "\n".join(body_lines).strip()

            whatsapp_msg = self._normalize_notification_text(body)

            html_body = self._build_threshold_change_email_html(
                student_name=student_name,
                rows=table_rows,
                threshold_status=threshold_status
            )

            email_ok = self._send_email(student_email, subject, body, html_body=html_body, logo_path=self.email_logo_path)
            whatsapp_ok = self._send_whatsapp(student_phone, whatsapp_msg)

            logger.info(f"Threshold change notification sent to {student_name} - Email: {email_ok}, WhatsApp: {whatsapp_ok}")
            return email_ok or whatsapp_ok

        except Exception as e:
            logger.error(f"Error preparing threshold change notification: {e}")
            return False
    
    def _send_email(self, recipient: str, subject: str, body: str, html_body: str = None, logo_path: str = None) -> bool:
        """Envoie un email"""
        try:
            if not self.email_address or not self.email_password:
                logger.warning("Email service not configured")
                return False

            if not html_body:
                html_body = self._build_html_from_plain_text(body)

            use_logo = bool(logo_path and os.path.exists(logo_path))
            if html_body or use_logo:
                msg = MIMEMultipart('related')
                alt = MIMEMultipart('alternative')
                alt.attach(MIMEText(body, 'plain'))
                if html_body:
                    alt.attach(MIMEText(html_body, 'html'))
                msg.attach(alt)
                if use_logo:
                    with open(logo_path, 'rb') as f:
                        img = MIMEImage(f.read())
                    img.add_header('Content-ID', '<uor_logo>')
                    img.add_header('Content-Disposition', 'inline', filename=os.path.basename(logo_path))
                    msg.attach(img)
            else:
                msg = MIMEMultipart()
                msg.attach(MIMEText(body, 'plain'))
            msg['From'] = self.email_address
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Configurer le serveur SMTP
            smtp_server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
            smtp_server.starttls()
            smtp_server.login(self.email_address, self.email_password)
            
            smtp_server.send_message(msg)
            smtp_server.quit()
            
            logger.info(f"Email sent successfully to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    def _send_whatsapp(self, student_phone: str, message: str) -> bool:
        """Envoie un message WhatsApp via Ultramsg"""
        try:
            if not student_phone:
                logger.warning("No phone number provided")
                return False
                
            if not self.ultramsg_instance or not self.ultramsg_token:
                logger.error(f"Ultramsg WhatsApp service not configured - Instance: {bool(self.ultramsg_instance)}, Token: {bool(self.ultramsg_token)}")
                return False

            # Normaliser le numéro de téléphone
            original_phone = str(student_phone).strip()
            to_number = original_phone
            if to_number.lower().startswith("whatsapp:"):
                to_number = to_number.split("whatsapp:", 1)[1]
            to_number = to_number.replace(" ", "").replace("-", "")
            
            # S'assurer que le numéro commence par +
            if not to_number.startswith("+"):
                to_number = "+" + to_number
            
            raw_instance = str(self.ultramsg_instance).strip().strip("/")
            instance_candidates = []

            def add_candidate(value: str):
                cleaned = str(value or "").strip().strip("/")
                if cleaned and cleaned not in instance_candidates:
                    instance_candidates.append(cleaned)

            # Priorité au format configuré (ne pas casser ce qui fonctionne déjà)
            add_candidate(raw_instance)

            # Fallbacks utiles si l'instance est mal formatée
            if raw_instance.lower().startswith("instance"):
                suffix = raw_instance[len("instance"):].strip()
                add_candidate(suffix)
            else:
                add_candidate(f"instance{raw_instance}")

            payload = {
                "token": self.ultramsg_token,
                "to": to_number,
                "body": message
            }

            logger.info(
                f"Sending WhatsApp - Original: {original_phone}, Normalized: {to_number}, "
                f"Instance candidates: {instance_candidates}"
            )

            last_error_detail = None
            for idx, instance_id in enumerate(instance_candidates, start=1):
                url = f"https://api.ultramsg.com/{instance_id}/messages/chat"
                logger.debug(f"Ultramsg attempt {idx}/{len(instance_candidates)} URL: {url}")

                response = requests.post(url, data=payload, timeout=10)
                response_text = response.text
                try:
                    result = response.json()
                except Exception:
                    result = {"raw": response_text}

                # Succès HTTP
                if response.ok:
                    logger.info(f"Ultramsg API response ({instance_id}): {result}")
                    if result.get("sent") == "true" or result.get("sent") is True:
                        logger.info(f"WhatsApp sent successfully to {to_number} via instance '{instance_id}'")
                        return True

                    logger.error(f"Ultramsg sent=false via instance '{instance_id}' - Response: {result}")
                    last_error_detail = f"sent=false via {instance_id}: {result}"
                    # sent=false = échec métier, ne pas réessayer avec d'autres formats
                    break

                # Erreur HTTP
                logger.error(
                    f"Ultramsg HTTP {response.status_code} via instance '{instance_id}' - "
                    f"Response: {response_text}"
                )
                lower_text = str(response_text).lower()
                if "stopped due to non-payment" in lower_text or "non-payment" in lower_text:
                    last_error_detail = (
                        "instance stopped due to non-payment. "
                        "Reactivate Ultramsg subscription, then retry sending."
                    )
                    break

                last_error_detail = f"http={response.status_code} via {instance_id}: {response_text}"

                # Sur 404 on tente un autre format d'instance, sinon on arrête
                if response.status_code != 404:
                    break

            logger.error(f"WhatsApp send failed. Last detail: {last_error_detail}")
            return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"WhatsApp API network error via Ultramsg: {type(e).__name__}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp via Ultramsg: {type(e).__name__}: {e}", exc_info=True)
            return False

    def _build_payment_email_html(self, student_name: str, amount_paid: float, final_fee: float,
                                   remaining: float, completion_msg: str,
                                   threshold_amount: float = None, threshold_status: str = None,
                                   promotion_info: str = None) -> str:
        """Construit le HTML pour l'email de paiement"""
        logo_html = ""
        if self.email_logo_path and os.path.exists(self.email_logo_path):
            logo_html = "<div style='margin-bottom:16px;'><img src='cid:uor_logo' alt='U.O.R' style='height:64px;'/></div>"

        completion_html = ""
        if completion_msg:
            completion_html = "<p style='color:#059669;font-weight:600;'>Félicitations ! Vous avez fini les frais académiques.</p>"

        promotion_row = ""
        if promotion_info:
            promotion_row = f"<tr><td style=\"padding:6px 12px;\">Promotion</td><td style=\"padding:6px 12px;\"><strong>{promotion_info}</strong></td></tr>"
        
        threshold_row = ""
        if threshold_amount is not None:
            threshold_row += f"<tr><td style=\"padding:6px 12px;\">Seuil requis</td><td style=\"padding:6px 12px;\"><strong>${threshold_amount:,.2f}</strong></td></tr>"
        if threshold_status:
            threshold_row += f"<tr><td style=\"padding:6px 12px;\">Statut du seuil</td><td style=\"padding:6px 12px;\"><strong>{threshold_status}</strong></td></tr>"

        return f"""
<div style="font-family:Arial, sans-serif; color:#111;">
    {logo_html}
    <p>Bonjour <strong>{student_name}</strong>,</p>
    <p>Votre paiement a été reçu avec succès.</p>
    <table style="border-collapse:collapse; margin:12px 0;">
        {promotion_row}
        <tr><td style="padding:6px 12px;">Montant payé</td><td style="padding:6px 12px;"><strong>${amount_paid:,.2f}</strong></td></tr>
        <tr><td style="padding:6px 12px;">Total des frais académiques</td><td style="padding:6px 12px;"><strong>${final_fee:,.2f}</strong></td></tr>
        <tr><td style="padding:6px 12px;">Montant restant</td><td style="padding:6px 12px;"><strong>${remaining:,.2f}</strong></td></tr>
        {threshold_row}
    </table>
    {completion_html}
    <p>Cordialement,<br/>U.O.R - Système de Contrôle d'Accès</p>
</div>
                """.strip()

    def _build_threshold_change_email_html(self, student_name: str, rows: list,
                                           threshold_status: str = None) -> str:
        """Construit le HTML pour l'email de changement de seuil"""
        logo_html = ""
        if self.email_logo_path and os.path.exists(self.email_logo_path):
            logo_html = "<div style='margin-bottom:16px;'><img src='cid:uor_logo' alt='U.O.R' style='height:64px;'/></div>"

        table_html = ""
        if rows:
            table_rows = "".join(
                f"<tr><td style='padding:6px 12px;'>{label}</td><td style='padding:6px 12px;'><strong>{value}</strong></td></tr>"
                for label, value in rows
            )
            table_html = f"<table style='border-collapse:collapse; margin:12px 0;'>{table_rows}</table>"

        threshold_note = ""
        if threshold_status == "Non atteint":
            threshold_note = "<p style='color:#b45309;font-weight:600;'>Vous n'avez pas encore atteint le nouveau seuil.</p>"

        return f"""
<div style="font-family:Arial, sans-serif; color:#111;">
    {logo_html}
    <p>Bonjour <strong>{student_name}</strong>,</p>
    <p>Le seuil financier pour l'accès aux examens a été mis à jour.</p>
    {table_html}
    {threshold_note}
    <p style="margin-top:12px;">IMPORTANT: Si vous aviez un code d'accès temporaire (paiement partiel), celui-ci a été invalidé.</p>
    <p>Veuillez effectuer un nouveau paiement pour atteindre le nouveau seuil et obtenir un code valide.</p>
    <p>Les étudiants ayant payé intégralement conservent leur code valable toute l'année.</p>
    <p>Cordialement,<br/>U.O.R - Système de Contrôle d'Accès</p>
</div>
                """.strip()

    def _build_text_table(self, rows: list) -> str:
        """Construit une table texte robuste (lisible en email/WhatsApp)."""
        if not rows:
            return ""

        def _truncate(value: str, max_len: int) -> str:
            value = str(value)
            if len(value) <= max_len:
                return value
            return value[: max_len - 1] + "…"

        header = ["Élément", "Valeur"]
        max_col1 = 20
        max_col2 = 26

        table_rows = [header] + [[str(label), str(value)] for label, value in rows]
        col1 = min(max(len(r[0]) for r in table_rows), max_col1)
        col2 = min(max(len(r[1]) for r in table_rows), max_col2)

        def fmt_row(left: str, right: str) -> str:
            left = _truncate(left, col1).ljust(col1)
            right = _truncate(right, col2).ljust(col2)
            return f"│ {left} │ {right} │"

        top = f"┌{'─' * (col1 + 2)}┬{'─' * (col2 + 2)}┐"
        mid = f"├{'─' * (col1 + 2)}┼{'─' * (col2 + 2)}┤"
        bot = f"└{'─' * (col1 + 2)}┴{'─' * (col2 + 2)}┘"

        parts = [top, fmt_row(header[0], header[1]), mid]
        for label, value in rows:
            parts.append(fmt_row(label, value))
        parts.append(bot)
        return "\n".join(parts)

    def send_whatsapp_with_template(self, student_phone: str, template_sid: str, 
                                   template_variables: list = None) -> bool:
        """Envoie un message WhatsApp via template Twilio (pour messages pré-approuvés)"""
        try:
            if not student_phone or not template_sid:
                logger.warning("Phone or template_sid missing")
                return False
                
            if not self.whatsapp_sid or not self.whatsapp_token or not self.whatsapp_from:
                logger.warning("WhatsApp service not configured")
                return False

            try:
                from twilio.rest import Client
            except ImportError:
                logger.warning("Twilio library not installed")
                return False

            client = Client(self.whatsapp_sid, self.whatsapp_token)
            
            # Format variables as JSON string if provided
            import json
            variables_json = ""
            if template_variables:
                # Convert list to Twilio format: {"1": "var1", "2": "var2", ...}
                variables_json = json.dumps({str(i+1): str(v) for i, v in enumerate(template_variables)})
            
            msg = client.messages.create(
                from_=f"whatsapp:{self.whatsapp_from}",
                content_sid=template_sid,
                content_variables=variables_json if variables_json else None,
                to=f"whatsapp:{student_phone}"
            )
            
            logger.info(f"WhatsApp template sent to {student_phone} (SID: {msg.sid})")
            return True
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp template: {e}")
            return False
