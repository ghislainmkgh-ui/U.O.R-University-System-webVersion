"""Configuration du logging centralisé"""
import logging
import os
from config.settings import LOG_LEVEL, LOG_DIR

# Créer le répertoire logs s'il n'existe pas
os.makedirs(LOG_DIR, exist_ok=True)

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'uor_system.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("Logging system initialized")
