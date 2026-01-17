import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_dashboard.settings')
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model

def reset():
    print("--- Starting Database Reset ---")
    
    # 1. Flush Data
    print("1. Flushing database (removing all data)...")
    call_command('flush', '--no-input')
    
    # 2. Migrate (Ensure schema is correct)
    print("2. Applying migrations...")
    call_command('migrate')
    
    # 3. Create Users
    print("3. Creating default users...")
    User = get_user_model()
    
    # Admin
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin')
        print("   ✅ Superuser created: admin / admin")
    
    # User
    if not User.objects.filter(username='user').exists():
        User.objects.create_user('user', 'user@example.com', 'user')
        print("   ✅ Normal user created: user / user")

    print("\n--- Reset Complete! ---")
    print("You can now login with the accounts above.")

if __name__ == '__main__':
    reset()
