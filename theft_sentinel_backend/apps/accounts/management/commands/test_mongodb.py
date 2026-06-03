"""
Test MongoDB Connection Command
"""
from django.core.management.base import BaseCommand
from config.mongodb import get_db, get_collection
from datetime import datetime


class Command(BaseCommand):
    help = 'Test MongoDB Atlas connection and operations'
    
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Testing MongoDB Atlas Connection...'))
        
        try:
            # Get database
            db = get_db()
            if db is None:
                self.stdout.write(self.style.ERROR('❌ Failed to connect to MongoDB'))
                return
            
            self.stdout.write(self.style.SUCCESS(f'✅ Connected to database: {db.name}'))
            
            # List collections
            collections = db.list_collection_names()
            self.stdout.write(self.style.SUCCESS(f'📁 Existing collections: {collections if collections else "None"}'))
            
            # Test insert
            test_collection = get_collection('test_connection')
            test_doc = {
                'test': 'data',
                'timestamp': datetime.now(),
                'message': 'MongoDB Atlas connection test from Django'
            }
            
            result = test_collection.insert_one(test_doc)
            self.stdout.write(self.style.SUCCESS(f'✅ Test insert successful! ID: {result.inserted_id}'))
            
            # Test find
            found_doc = test_collection.find_one({'_id': result.inserted_id})
            self.stdout.write(self.style.SUCCESS(f'✅ Test find successful! Doc: {found_doc["message"]}'))
            
            # Clean up
            test_collection.delete_one({'_id': result.inserted_id})
            self.stdout.write(self.style.SUCCESS('✅ Test cleanup successful!'))
            
            # Database stats
            stats = db.command('dbstats')
            self.stdout.write(self.style.SUCCESS(f'\n📊 Database Statistics:'))
            self.stdout.write(f'   - Collections: {stats["collections"]}')
            self.stdout.write(f'   - Data Size: {stats["dataSize"] / 1024:.2f} KB')
            self.stdout.write(f'   - Storage Size: {stats["storageSize"] / 1024:.2f} KB')
            
            self.stdout.write(self.style.SUCCESS('\n✅ All MongoDB tests passed!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ MongoDB test failed: {str(e)}'))

