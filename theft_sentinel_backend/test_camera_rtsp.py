"""
Test RTSP Camera Connectivity
Quick script to diagnose camera connection issues
"""
import os
import sys
import django
import cv2

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.cameras.models import Camera


def test_opencv():
    """Test if OpenCV is installed properly"""
    print("=" * 60)
    print("1. Testing OpenCV Installation")
    print("=" * 60)
    print(f"OpenCV Version: {cv2.__version__}")
    print(f"OpenCV Build Info:")
    print(f"  - Video I/O: {cv2.getBuildInformation().count('YES') > 0}")
    print("✓ OpenCV is installed")
    print()


def test_camera_rtsp(camera):
    """Test RTSP connection for a specific camera"""
    print("=" * 60)
    print(f"Testing Camera: {camera.name}")
    print("=" * 60)
    print(f"ID: {camera.id}")
    print(f"Location: {camera.location}")
    print(f"Status: {camera.status}")
    print(f"RTSP URL: {camera.rtsp_url[:50]}...")
    print()

    # Convert IP Webcam base URL to video stream URL
    processed_url = camera.rtsp_url
    
    # If it's an HTTP URL (IP Webcam) without a specific endpoint, add /video
    if camera.rtsp_url.startswith('http://'):
        # Check if URL ends with port only (like :8080 or :4747)
        if camera.rtsp_url.split('/')[-1].startswith(':') or \
           (camera.rtsp_url.count('/') == 2 and (':8080' in camera.rtsp_url or ':4747' in camera.rtsp_url)):
            processed_url = camera.rtsp_url.rstrip('/') + '/video'
            print(f"ℹ️  Using video stream: {processed_url}")
            print()
    
    # Test connection
    print("Attempting to connect...")
    cap = cv2.VideoCapture(processed_url)
    
    if not cap.isOpened():
        print("❌ FAILED: Could not open RTSP stream")
        print("\nPossible issues:")
        print("  1. Camera is offline")
        print("  2. RTSP URL is incorrect")
        print("  3. Wrong credentials")
        print("  4. Network/firewall blocking connection")
        print("  5. Camera not configured for RTSP")
        cap.release()
        return False
    
    print("✓ Stream opened successfully")
    
    # Try to read a frame
    print("Attempting to read frame...")
    ret, frame = cap.read()
    
    if not ret or frame is None:
        print("❌ FAILED: Could not read frame")
        print("\nPossible issues:")
        print("  1. Camera is connected but not streaming")
        print("  2. Stream format not supported")
        print("  3. Insufficient bandwidth")
        cap.release()
        return False
    
    print("✓ Frame captured successfully")
    print(f"  - Frame shape: {frame.shape}")
    print(f"  - Resolution: {frame.shape[1]}x{frame.shape[0]}")
    print(f"  - Channels: {frame.shape[2]}")
    
    # Save test frame
    filename = f"test_frame_{camera.id}.jpg"
    cv2.imwrite(filename, frame)
    print(f"✓ Test frame saved: {filename}")
    
    cap.release()
    print("\n✅ Camera is working correctly!")
    return True


def main():
    print("\n" + "=" * 60)
    print("RTSP CAMERA CONNECTIVITY TEST")
    print("=" * 60)
    print()

    # Test OpenCV
    test_opencv()

    # Get all cameras
    cameras = Camera.objects.all()
    
    if not cameras:
        print("⚠️  No cameras found in database")
        print("\nPlease add cameras through the admin interface or API")
        return

    print(f"Found {cameras.count()} camera(s) in database")
    print()

    # Test each camera
    results = {}
    for camera in cameras:
        success = test_camera_rtsp(camera)
        results[camera.name] = success
        print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    working = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Working cameras: {working}/{total}")
    print()
    
    for name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {name}")
    
    print()
    
    if working == 0:
        print("❌ No cameras are working!")
        print("\nTroubleshooting steps:")
        print("1. Verify camera RTSP URLs are correct")
        print("2. Check camera credentials")
        print("3. Ensure cameras are online and streaming")
        print("4. Test network connectivity to cameras")
        print("5. Check firewall rules")
        print("\nTo update camera RTSP URL:")
        print("  python manage.py shell")
        print("  >>> from apps.cameras.models import Camera")
        print("  >>> camera = Camera.objects.get(name='Camera Name')")
        print("  >>> camera.rtsp_url = 'rtsp://user:pass@ip:port/stream'")
        print("  >>> camera.save()")
    elif working < total:
        print("⚠️  Some cameras are not working")
        print("Check the errors above for each failed camera")
    else:
        print("✅ All cameras are working correctly!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

