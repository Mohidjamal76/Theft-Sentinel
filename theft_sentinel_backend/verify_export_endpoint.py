"""
Quick script to verify the export endpoint is properly configured
Run this from the theft_sentinel_backend directory: python verify_export_endpoint.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.urls import reverse, NoReverseMatch
from apps.dashboard.urls import urlpatterns

print("=" * 60)
print("Verifying Export Endpoint Configuration")
print("=" * 60)

# Check if the view can be imported
try:
    from apps.dashboard.views import IncidentReportExportView
    print("✅ IncidentReportExportView imported successfully")
except ImportError as e:
    print(f"❌ Failed to import IncidentReportExportView: {e}")
    sys.exit(1)

# Check if the URL pattern exists
export_url_found = False
for pattern in urlpatterns:
    if 'export-incidents' in str(pattern.pattern):
        export_url_found = True
        print(f"✅ URL pattern found: {pattern.pattern}")
        print(f"   View: {pattern.callback}")
        break

if not export_url_found:
    print("❌ export-incidents URL pattern not found in urlpatterns")
    print("Available patterns:")
    for pattern in urlpatterns:
        print(f"   - {pattern.pattern}")
    sys.exit(1)

# Try to reverse the URL
try:
    url = reverse('export_incidents')
    print(f"✅ URL reverse successful: {url}")
except NoReverseMatch as e:
    print(f"❌ Failed to reverse URL: {e}")
    sys.exit(1)

print("=" * 60)
print("✅ All checks passed! The endpoint should be available at:")
print(f"   /api/dashboard{url}")
print("=" * 60)
print("\n⚠️  If you're still getting 404 errors:")
print("   1. Make sure the Django server has been restarted")
print("   2. Check the Django server console for any import errors")
print("   3. Verify the server is running the latest code")
print("=" * 60)

