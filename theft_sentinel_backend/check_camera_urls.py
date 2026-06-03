"""
Check current camera URLs in database
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.cameras.models import Camera

print("=" * 60)
print("CURRENT CAMERA URLs IN DATABASE")
print("=" * 60)
print()

cameras = Camera.objects.all()

for camera in cameras:
    print(f"📹 {camera.name}")
    print(f"   ID: {camera.id}")
    print(f"   Status: {camera.status}")
    print(f"   URL: {camera.rtsp_url}")
    print()
    
    # Check for issues
    if '/video/video' in camera.rtsp_url:
        print(f"   ⚠️  WARNING: URL has duplicate /video!")
        print(f"   Should be: {camera.rtsp_url.replace('/video/video', '/video')}")
    elif camera.rtsp_url.startswith('http://') and not camera.rtsp_url.endswith('/video'):
        if ':8080' in camera.rtsp_url or ':4747' in camera.rtsp_url:
            print(f"   ⚠️  WARNING: Missing /video endpoint!")
            print(f"   Should be: {camera.rtsp_url}/video")
    else:
        print(f"   ✅ URL looks correct")
    
    print()

print("=" * 60)

