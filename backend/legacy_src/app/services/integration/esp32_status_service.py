"""Service pour vérifier le statut de l'ESP32 via socket TCP."""
import socket
import logging
from dataclasses import dataclass
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class ESP32Status:
    text: str
    color: str


class ESP32StatusService:
    """Vérifie la disponibilité de l'ESP32 via un ping TCP."""

    def __init__(self, host: str = None, port: int = None, timeout: float = None):
        self.host = host or settings.ESP32_HOST
        self.port = port or settings.ESP32_PORT
        self.timeout = timeout if timeout is not None else settings.ESP32_SOCKET_TIMEOUT
        self.refresh_interval_ms = settings.ESP32_STATUS_REFRESH_MS

    def check_status(self) -> ESP32Status:
        """Retourne le statut courant de l'ESP32."""
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.settimeout(self.timeout)
                sock.sendall(b"PING")
                data = sock.recv(64)
                if data and b"PONG" in data.upper():
                    return ESP32Status("ESP32 connecté (Wi‑Fi OK)", "#10b981")
                return ESP32Status("ESP32 connecté (réponse inconnue)", "#f59e0b")
        except Exception as e:
            logger.debug(f"ESP32 status check failed: {e}")
            return ESP32Status("ESP32 non connecté (mode simulation)", "#f59e0b")
