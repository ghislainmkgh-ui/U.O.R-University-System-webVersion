"""Configuration centralisée pour l'application U.O.R"""
import os
from pathlib import Path

from dotenv import load_dotenv

WEB_ROOT = Path(__file__).resolve().parents[3]
WEB_BACKEND_ROOT = WEB_ROOT / "backend"

load_dotenv(WEB_ROOT / ".env", override=True)
load_dotenv(WEB_BACKEND_ROOT / ".env", override=True)

# Base de données
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "uor_university")
DB_PORT = int(os.getenv("DB_PORT", 3306))

# Sécurité
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
JWT_EXPIRATION = int(os.getenv("JWT_EXPIRATION", 3600))
PASSWORD_MIN_LENGTH = 6  # 6 chiffres minimum

# Seuils financiers
FINANCIAL_THRESHOLD = float(os.getenv("FINANCIAL_THRESHOLD", 0.0))

# Taux de conversion FC -> USD pour affichage
USD_EXCHANGE_RATE_FC = float(os.getenv("USD_EXCHANGE_RATE_FC", 2700.0))

# Email
EMAIL_SERVICE = os.getenv("EMAIL_SERVICE", "gmail")  # ou autre
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

# Validation distante des demandes d'accès (Super Admin via e-mail)
# Exemple (production): https://admin.uor.example.com
ACCESS_APPROVAL_BASE_URL = os.getenv("ACCESS_APPROVAL_BASE_URL", "")
ACCESS_APPROVAL_TOKEN_TTL_HOURS = int(os.getenv("ACCESS_APPROVAL_TOKEN_TTL_HOURS", 72))
ACCESS_APPROVAL_TOKEN_SECRET = os.getenv("ACCESS_APPROVAL_TOKEN_SECRET", SECRET_KEY)
ACCESS_APPROVAL_API_HOST = os.getenv("ACCESS_APPROVAL_API_HOST", "0.0.0.0")
ACCESS_APPROVAL_API_PORT = int(os.getenv("ACCESS_APPROVAL_API_PORT", 5002))
ACCESS_APPROVAL_API_DEBUG = os.getenv("ACCESS_APPROVAL_API_DEBUG", "False").lower() == "true"
ACCESS_APPROVAL_AUTOSTART = os.getenv("ACCESS_APPROVAL_AUTOSTART", "True").lower() == "true"
ACCESS_APPROVAL_TUNNEL_AUTOSTART = os.getenv("ACCESS_APPROVAL_TUNNEL_AUTOSTART", "True").lower() == "true"
ACCESS_APPROVAL_TUNNEL_PROVIDER = os.getenv("ACCESS_APPROVAL_TUNNEL_PROVIDER", "localtunnel")
ACCESS_APPROVAL_TUNNEL_HOST = os.getenv("ACCESS_APPROVAL_TUNNEL_HOST", "127.0.0.1")
ACCESS_APPROVAL_TUNNEL_PORT = int(os.getenv("ACCESS_APPROVAL_TUNNEL_PORT", 8000))
ACCESS_APPROVAL_TUNNEL_SUBDOMAIN = os.getenv("ACCESS_APPROVAL_TUNNEL_SUBDOMAIN", "")

# WhatsApp (Twilio - legacy)
WHATSAPP_ACCOUNT_SID = os.getenv("WHATSAPP_ACCOUNT_SID", os.getenv("TWILIO_ACCOUNT_SID", ""))
WHATSAPP_AUTH_TOKEN = os.getenv("WHATSAPP_AUTH_TOKEN", os.getenv("TWILIO_AUTH_TOKEN", ""))
WHATSAPP_FROM = os.getenv("WHATSAPP_FROM", os.getenv("TWILIO_WHATSAPP_FROM", ""))

# Ultramsg WhatsApp API
ULTRAMSG_INSTANCE_ID = os.getenv("ULTRAMSG_INSTANCE_ID", "")
ULTRAMSG_TOKEN = os.getenv("ULTRAMSG_TOKEN", "")

# WhatsApp Templates (optional - for pre-approved content Messages)
WHATSAPP_TEMPLATE_ACCESS_CODE = os.getenv("WHATSAPP_TEMPLATE_ACCESS_CODE", "")
WHATSAPP_TEMPLATE_THRESHOLD_ALERT = os.getenv("WHATSAPP_TEMPLATE_THRESHOLD_ALERT", "")
WHATSAPP_USE_TEMPLATES = os.getenv("WHATSAPP_USE_TEMPLATES", "False").lower() == "true"

# Email branding
EMAIL_LOGO_PATH = os.getenv("EMAIL_LOGO_PATH", "")

# Arduino (OBSOLÈTE — conservé pour rétro-compatibilité)
ARDUINO_PORT      = os.getenv("ARDUINO_PORT",      "COM3")
ARDUINO_BAUD_RATE = int(os.getenv("ARDUINO_BAUD_RATE", 9600))

# ESP32 (Wi-Fi Socket) — serveur d'accès
ESP32_HOST              = os.getenv("ESP32_HOST",              "127.0.0.1")
ESP32_PORT              = int(os.getenv("ESP32_PORT",          5050))
ESP32_SOCKET_TIMEOUT    = float(os.getenv("ESP32_SOCKET_TIMEOUT", 1.5))
ESP32_STATUS_REFRESH_MS = int(os.getenv("ESP32_STATUS_REFRESH_MS", 5000))

# Serveur d'accès HTTP (access_server.py)
ACCESS_SERVER_HOST = os.getenv("ACCESS_SERVER_HOST", "0.0.0.0")
ACCESS_SERVER_AUTOSTART = os.getenv("ACCESS_SERVER_AUTOSTART", "True").lower() == "true"

# Caméra IP (nouvelle architecture — remplace ESP32-CAM)
IP_CAMERA_TYPE         = os.getenv("IP_CAMERA_TYPE",         "v720")
IP_CAMERA_URL          = os.getenv("IP_CAMERA_URL",          "")   # URL flux RTSP
IP_CAMERA_SNAPSHOT_URL = os.getenv("IP_CAMERA_SNAPSHOT_URL", "")   # URL snapshot HTTP
IP_CAMERA_USERNAME     = os.getenv("IP_CAMERA_USERNAME",     "")
IP_CAMERA_PASSWORD     = os.getenv("IP_CAMERA_PASSWORD",     "")
CAMERA_DEVICE_ID       = os.getenv("CAMERA_DEVICE_ID",       "")
IP_CAMERA_CAPTURE_PRIORITY = os.getenv("IP_CAMERA_CAPTURE_PRIORITY", "snapshot,rtsp,ftp")

# Caméra Yi IoT (fallback FTP image locale)
IP_CAMERA_FTP_ENABLED  = os.getenv("IP_CAMERA_FTP_ENABLED", "False").lower() == "true"
IP_CAMERA_FTP_HOST     = os.getenv("IP_CAMERA_FTP_HOST", "")
IP_CAMERA_FTP_PORT     = int(os.getenv("IP_CAMERA_FTP_PORT", 21))
IP_CAMERA_FTP_PATH     = os.getenv("IP_CAMERA_FTP_PATH", "/tmp/motion.jpg")
IP_CAMERA_FTP_USERNAME = os.getenv("IP_CAMERA_FTP_USERNAME", "")
IP_CAMERA_FTP_PASSWORD = os.getenv("IP_CAMERA_FTP_PASSWORD", "")

# Auto-découverte caméra Yi (utile si l'IP change après reboot DHCP)
IP_CAMERA_AUTO_DISCOVERY_ENABLED = os.getenv("IP_CAMERA_AUTO_DISCOVERY_ENABLED", "False").lower() == "true"
IP_CAMERA_DISCOVERY_SUBNET       = os.getenv("IP_CAMERA_DISCOVERY_SUBNET", "192.168.1.")
IP_CAMERA_DISCOVERY_IP_RANGE     = os.getenv("IP_CAMERA_DISCOVERY_IP_RANGE", "1-254")
IP_CAMERA_DISCOVERY_TIMEOUT      = float(os.getenv("IP_CAMERA_DISCOVERY_TIMEOUT", 0.35))
IP_CAMERA_DISCOVERY_MAX_WORKERS  = int(os.getenv("IP_CAMERA_DISCOVERY_MAX_WORKERS", 48))
IP_CAMERA_FTP_STALE_THRESHOLD    = max(1, int(os.getenv("IP_CAMERA_FTP_STALE_THRESHOLD", 3)))
IP_CAMERA_FTP_BYPASS_SEC         = max(3, int(os.getenv("IP_CAMERA_FTP_BYPASS_SEC", 30)))
IP_CAMERA_FTP_USE_LATEST_JPG     = os.getenv("IP_CAMERA_FTP_USE_LATEST_JPG", "True").lower() == "true"

# Reconnaissance faciale
FACE_RECOGNITION_TOLERANCE = float(os.getenv("FACE_RECOGNITION_TOLERANCE", 0.50))
FACE_CAPTURE_ATTEMPTS = max(1, int(os.getenv("FACE_CAPTURE_ATTEMPTS", 3)))
FACE_CAPTURE_RETRY_DELAY_MS = max(0, int(os.getenv("FACE_CAPTURE_RETRY_DELAY_MS", 350)))
FACE_REJECT_MULTIPLE_FACES = os.getenv("FACE_REJECT_MULTIPLE_FACES", "True").lower() == "true"
FACE_MIN_MATCH_SUCCESSES = max(1, int(os.getenv("FACE_MIN_MATCH_SUCCESSES", 3)))
FACE_MAX_PROCESSING_WIDTH = max(320, int(os.getenv("FACE_MAX_PROCESSING_WIDTH", 640)))
FACE_REFERENCE_CACHE_TTL_SEC = max(5, int(os.getenv("FACE_REFERENCE_CACHE_TTL_SEC", 300)))
FACE_ENABLE_CLAHE_FALLBACK = os.getenv("FACE_ENABLE_CLAHE_FALLBACK", "True").lower() == "true"

# Application
APP_NAME = "U.O.R - Plateforme d'Accès aux Examens"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("WEB_LOG_DIR") or str(WEB_ROOT / "logs")
