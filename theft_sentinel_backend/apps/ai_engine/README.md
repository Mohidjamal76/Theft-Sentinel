# AI Engine Module

> **Complete AI Pipeline Integration for Theft Detection**

This module integrates your existing AI pipeline (YOLOv8 Detection + Pose + DeepSORT + ML Classifier) into the Django REST Framework backend without modifying any existing code.

## 🎯 Features

- ✅ Real-time theft detection
- ✅ Multi-object tracking (DeepSORT)
- ✅ Pose-based behavior analysis
- ✅ ML-powered classification
- ✅ Automatic alert creation
- ✅ RESTful API endpoints
- ✅ Database storage of results

## 📁 Module Structure

```
ai_engine/
├── api/
│   ├── serializers.py    # Request/response validation
│   ├── views.py          # API endpoint handlers
│   └── urls.py           # URL routing
├── services/
│   ├── ai_service.py     # Model lifecycle manager
│   └── inference_runner.py  # Pipeline wrapper
├── utils/
│   └── frame_utils.py    # Frame encoding/decoding
├── migrations/
│   └── 0001_initial.py   # Database schema
├── models.py             # AIInference, DetectionTrack
├── admin.py              # Django admin interface
├── apps.py               # App configuration
└── README.md             # This file
```

## 🚀 Quick Start

### 1. Initialize
```bash
# Migrations are auto-run on app initialization
python manage.py migrate ai_engine
```

### 2. Start Server
```bash
python manage.py runserver
```

Models load automatically on startup.

### 3. Test
```bash
curl http://localhost:8000/api/ai/health/
```

## 📡 API Endpoints

### Analyze Frame
```bash
POST /api/ai/analyze-frame/
Content-Type: application/json
Authorization: Bearer <token>

{
  "frame": "base64_encoded_image",
  "camera_id": "optional",
  "save_to_db": true,
  "create_alert_on_theft": true
}
```

### Process Camera
```bash
POST /api/ai/process-camera/
Content-Type: application/json
Authorization: Bearer <token>

{
  "camera_id": "camera_123",
  "save_to_db": true,
  "create_alert_on_theft": true
}
```

### Model Info
```bash
GET /api/ai/model-info/
Authorization: Bearer <token>
```

### Inference History
```bash
GET /api/ai/inference-history/?limit=10&classification=theft
Authorization: Bearer <token>
```

### Health Check
```bash
GET /api/ai/health/
# No authentication required
```

## 🔗 Integration Points

### Alert Creation (Non-Destructive)
```python
# In api/views.py
from apps.alerts.serializers import AlertCreateSerializer

# Uses existing alert creation logic
alert_serializer = AlertCreateSerializer(data=alert_data)
alert = alert_serializer.save()
```

### Camera Access
```python
# In api/views.py
from apps.cameras.models import Camera

camera = Camera.objects.get(pk=camera_id)
frame = capture_frame_from_rtsp(camera.rtsp_url)
```

## 🗄️ Database Models

### AIInference
Stores complete inference results.

**Fields:**
- `camera_id` - ForeignKey to Camera
- `detections` - JSON array of detected objects
- `poses` - JSON array of pose keypoints
- `tracks` - JSON array of tracking data
- `classification` - "theft" or "normal"
- `confidence` - ML model confidence (0-1)
- `alert` - ForeignKey to Alert (if created)
- `timestamp` - When inference occurred

### DetectionTrack
Stores per-track behavioral data.

**Fields:**
- `camera_id` - ForeignKey to Camera
- `track_id` - DeepSORT track ID
- `object_type` - "person", "bag", "object"
- `ml_theft_score` - Latest ML prediction
- `hand_in_bag_frames` - Behavioral counter
- `concealment_events` - Suspicious actions
- `is_suspicious` - Flag for suspicious tracks

## 🧠 AI Pipeline

### Models Used (YOUR EXISTING PIPELINE)
1. **YOLOv8-L Detection** - `ModelExport/yolov8l.pt`
2. **YOLOv8-L Pose** - `ModelExport/yolov8l-pose.pt`
3. **DeepSORT Tracking** - Built-in
4. **ML Classifier** - `ModelExport/trained_models/theft_classifier.pkl`

### Processing Flow
```
Frame → YOLO Detection → DeepSORT Tracking → 
Pose Estimation → Behavioral Analysis → 
ML Classification → Alert Creation (if theft)
```

### Behavioral Features
- Hand in bag detection
- Hand in torso region
- Fast wrist motion
- Near object interaction
- Concealment events

## 🔧 Configuration

### Model Paths
Defined in `services/ai_service.py`:
```python
det_model_path = ModelExport / "yolov8l.pt"
pose_model_path = ModelExport / "yolov8l-pose.pt"
ml_model_path = ModelExport / "trained_models/theft_classifier.pkl"
```

### Inference Parameters
Defined in `services/inference_runner.py`:
```python
det_conf = 0.45      # Detection confidence
det_iou = 0.50       # Detection IoU
pose_conf = 0.30     # Pose confidence
```

### Theft Threshold
Adjust in `services/inference_runner.py`:
```python
if ml_score > 0.5:  # Theft threshold
    theft_detected = True
```

## 📊 Usage Examples

### Python Client
```python
import requests
import base64
import cv2

# Authenticate
token = "your_jwt_token"

# Load and encode frame
frame = cv2.imread("test.jpg")
_, buffer = cv2.imencode('.jpg', frame)
frame_b64 = base64.b64encode(buffer).decode('utf-8')

# Analyze
response = requests.post(
    "http://localhost:8000/api/ai/analyze-frame/",
    headers={"Authorization": f"Bearer {token}"},
    json={"frame": frame_b64, "save_to_db": False}
)

result = response.json()
print(f"Classification: {result['classification']}")
print(f"Confidence: {result['confidence']}")
```

### Direct Pipeline Usage
```python
from apps.ai_engine.services.inference_runner import InferenceRunner
import cv2

runner = InferenceRunner()
frame = cv2.imread("test.jpg")

result = runner.process_frame(frame, camera_id="cam_1")

if result['classification'] == 'theft':
    print(f"Theft detected! Confidence: {result['confidence']}")
    for track in result['suspicious_tracks']:
        print(f"Suspicious track: {track['track_id']}")
```

## 🧪 Testing

### Run Test Suite
```bash
# From project root
python test_ai_engine.py
```

### Manual Testing
```bash
# Health check
curl http://localhost:8000/api/ai/health/

# Model info (requires auth)
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/ai/model-info/
```

## 🐛 Troubleshooting

### Models Not Loading
**Symptoms:** "AI service not initialized"

**Check:**
1. Model files exist in `ModelExport/`
2. CUDA is available: `python -c "import torch; print(torch.cuda.is_available())"`
3. Sufficient GPU memory

**Solution:**
```bash
# Verify files
ls ModelExport/yolov8l.pt
ls ModelExport/yolov8l-pose.pt
ls ModelExport/trained_models/theft_classifier.pkl
```

### Slow Processing
**Symptoms:** Processing time > 500ms

**Check:**
1. GPU is being used: `nvidia-smi`
2. CUDA available in PyTorch
3. Too many workers

**Solution:**
```python
# In settings.py
# Reduce workers or use CPU if GPU unavailable
```

### Frame Decoding Error
**Symptoms:** "Failed to decode frame"

**Check:**
1. Base64 encoding is correct
2. Image format is JPEG or PNG
3. Data URL prefix removed

**Solution:**
```python
# Correct encoding
_, buffer = cv2.imencode('.jpg', frame)
frame_b64 = base64.b64encode(buffer).decode('utf-8')
# Don't add 'data:image/jpeg;base64,' prefix
```

## 📈 Performance

### Expected Processing Times (GPU)
- Detection: 30-50ms
- Detection + Pose: 80-120ms
- Full Pipeline: 100-150ms

### Optimization Tips
1. Use GPU (CUDA)
2. Batch process multiple frames
3. Resize large frames before sending
4. Reuse InferenceRunner instance

## 🔒 Security

### Authentication
- All endpoints require JWT token (except `/health/`)
- Uses existing RBAC system

### Permissions
- Admin: Full access
- Security In-Charge: Full access
- Security Guard: Read-only

## 📚 Documentation

See project root for complete documentation:
- `AI_ENGINE_INTEGRATION.md` - Complete guide
- `AI_ENGINE_QUICKSTART.md` - Quick reference
- `DEPLOYMENT_CHECKLIST.md` - Production deployment
- `example_usage.py` - Code examples

## 🎉 Features in Detail

### Real-Time Detection
- YOLOv8-L object detection
- 80 COCO object classes
- Confidence-based filtering

### Pose Estimation
- 17 keypoint detection
- Per-person pose tracking
- Skeleton visualization

### Tracking
- DeepSORT multi-object tracking
- Persistent track IDs
- Occlusion handling

### Behavioral Analysis
- Hand-in-bag detection
- Concealment event detection
- Fast motion detection
- Object interaction tracking

### ML Classification
- Random Forest classifier
- Sequence-based prediction
- Behavioral feature integration

## 🚀 Production Ready

- ✅ Error handling
- ✅ Logging
- ✅ Database transactions
- ✅ API documentation
- ✅ Performance optimized
- ✅ GPU accelerated
- ✅ Scalable architecture

## 📞 Support

For issues or questions:
1. Check documentation in project root
2. Review test suite: `test_ai_engine.py`
3. Check logs: `journalctl -u theft_sentinel`
4. Verify health: `/api/ai/health/`

---

**Module Version:** 1.0.0  
**Django Version:** 4.2+  
**Python Version:** 3.8+  
**PyTorch Version:** 2.0+

