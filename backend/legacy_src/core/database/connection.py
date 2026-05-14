"""Gestion des connexions à la base de données avec pool de connexions"""
import mysql.connector
from mysql.connector import Error, pooling
import logging
from config.settings import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Pool de connexions MySQL sécurisé (Singleton)"""
    
    _instance = None
    _connection_pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._init_pool()
        return cls._instance
    
    @classmethod
    def _init_pool(cls):
        """Initialise le pool de connexions"""
        try:
            cls._connection_pool = pooling.MySQLConnectionPool(
                pool_name="uor_pool",
                pool_size=20,
                pool_reset_session=True,
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                port=DB_PORT,
                autocommit=False
            )
            logger.info("Connection pool initialized successfully")
        except Error as e:
            logger.error(f"Error initializing connection pool: {e}")
            raise
    
    def get_connection(self):
        """
        Récupère une connexion du pool
        
        Returns:
            Connexion MySQL
        """
        try:
            connection = self._connection_pool.get_connection()
            if connection.is_connected():
                return connection
        except Error as e:
            logger.error(f"Error getting connection from pool: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = None):
        """
        Exécute une requête SELECT
        
        Args:
            query: Requête SQL
            params: Paramètres de la requête
            
        Returns:
            Résultats de la requête
        """
        connection = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            result = cursor.fetchall()
            cursor.close()
            return result
        except Error as e:
            logger.error(f"Error executing query: {e}")
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """
        Exécute une requête UPDATE/INSERT/DELETE
        
        Args:
            query: Requête SQL
            params: Paramètres de la requête
            
        Returns:
            Nombre de lignes affectées
        """
        connection = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            connection.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows
        except Error as e:
            if connection:
                connection.rollback()
            logger.error(f"Error executing update: {e}")
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
    
    def close_all_connections(self):
        """Ferme tous les pools de connexions"""
        if self._connection_pool:
            self._connection_pool._reset_connections()
            logger.info("All connections closed")
    
    def close_connection(self, connection):
        """
        Ferme une connexion
        
        Args:
            connection: Connexion à fermer
        """
        try:
            if connection and connection.is_connected():
                connection.close()
        except Error as e:
            logger.error(f"Error closing connection: {e}")

