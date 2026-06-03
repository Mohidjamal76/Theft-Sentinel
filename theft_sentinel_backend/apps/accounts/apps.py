from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AccountsConfig(AppConfig):
    """
    Accounts app configuration for MongoDB compatibility.
    
    Uses ObjectIdAutoField as default auto field for MongoDB compatibility.
    Disconnects Django's default permission creation signal to prevent
    "unhashable model instances" errors with MongoDB ObjectId fields.
    """
    default_auto_field = 'django_mongodb_backend.fields.ObjectIdAutoField'
    name = 'apps.accounts'

    def ready(self):
        """
        Disconnect post_migrate signal for creating permissions.
        
        This prevents Django from trying to create default permissions
        for MongoDB models, which causes "unhashable model instances" errors
        because Django's permission system expects hashable primary keys.
        """
        try:
            from django.contrib.auth.management import create_permissions
            # Disconnect the create_permissions signal to avoid MongoDB compatibility issues
            post_migrate.disconnect(
                create_permissions,
                dispatch_uid='django.contrib.auth.management.create_permissions'
            )
        except (ValueError, TypeError):
            # Signal might not be connected, which is fine
            pass

