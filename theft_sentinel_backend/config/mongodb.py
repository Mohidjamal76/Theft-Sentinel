"""
MongoDB Connection Utility
Provides MongoDB database connection for the application
"""
from django.conf import settings
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import logging

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection singleton"""
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self.connect()
    
    def connect(self):
        """Establish MongoDB connection"""
        try:
            self._client = MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=10000,
                retryWrites=True
            )
            
            # Test connection
            self._client.admin.command('ping')
            
            self._db = self._client[settings.MONGODB_NAME]
            logger.info(f"✅ MongoDB connected successfully to database: {settings.MONGODB_NAME}")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ MongoDB connection failed: {str(e)}")
            self._client = None
            self._db = None
    
    @property
    def db(self):
        """Get database instance"""
        if self._db is None:
            self.connect()
        return self._db
    
    @property
    def client(self):
        """Get MongoDB client"""
        if self._client is None:
            self.connect()
        return self._client
    
    def get_collection(self, collection_name):
        """Get a specific collection"""
        if self._db is not None:
            return self._db[collection_name]
        return None
    
    def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB connection closed")


# Global MongoDB instance
mongodb = MongoDB()


def get_db():
    """Get MongoDB database instance"""
    return mongodb.db


def get_collection(collection_name):
    """Get MongoDB collection"""
    return mongodb.get_collection(collection_name)

