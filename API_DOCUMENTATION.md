# Theft Sentinel — API Documentation
> **Architecture Snapshot:** This document reflects the stable, post-deprecation codebase.
> The standalone **Tracking** and **AI History** UI pages and their exclusive endpoints
> have been permanently removed. This file documents every **active** endpoint only.

## Base URL
```
http://localhost:8000/api
```

## Authentication
All endpoints (except `health/` and `realtime-tracking/`) require JWT Bearer authentication.

```
Authorization: Bearer <access_token>
```

JWT tokens are obtained via the login endpoint. The `access_token` key is used when reading from `localStorage` on the frontend.

---

## 1. Authentication Endpoints

### Register User
**POST** `/auth/register/`

**Body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "securepass123",
  "password2": "securepass123",
  "role": "SECURITY_GUARD"
}
```

**Response (201):**
```json
{
  "user": {
    "id": "6629abc...",
    "username": "john_doe",
    "email": "john@example.com",
    "role": "SECURITY_GUARD",
    "is_active": true,
    "created_at": "2026-04-28T10:00:00Z"
  },
  "message": "User registered successfully"
}
```

---

### Login
**POST** `/auth/login/`

**Body:**
```json
{
  "username": "john_doe",
  "password": "securepass123"
}
```

**Response (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": "6629abc...",
    "username": "john_doe",
    "email": "john@example.com",
    "role": "SECURITY_GUARD",
    "is_active": true,
    "created_at": "2026-04-28T10:00:00Z"
  }
}
```

---

### Refresh Token
**POST** `/auth/refresh/`

**Body:**
```json
{ "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..." }
```

**Response (200):**
```json
{ "access": "eyJ0eXAiOiJKV1QiLCJhbGc..." }
```

---

### Logout
**POST** `/auth/logout/`

**Body:**
```json
{ "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..." }
```

**Response (200):**
```json
{ "message": "Logout successful" }
```

---

## 2. Camera Endpoints

### List Cameras
**GET** `/cameras/`

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `zone` | string | Filter by zone |
| `status` | string | `ONLINE` or `OFFLINE` |

**Response (200):**
```json
{
  "count": 3,
  "results": [
    {
      "id": "6629abc...",
      "name": "Main Entrance Camera",
      "rtsp_url": "rtsp://192.168.1.100:554/stream",
      "location": "Building A - Main Entrance",
      "zone": "Zone A",
      "status": "ONLINE",
      "ai_monitoring_enabled": true,
      "created_at": "2026-04-01T10:00:00Z"
    }
  ]
}
```

---

### Create Camera
**POST** `/cameras/` *(ADMIN only)*

**Body:**
```json
{
  "name": "Main Entrance Camera",
  "rtsp_url": "rtsp://192.168.1.100:554/stream",
  "location": "Building A - Main Entrance",
  "zone": "Zone A",
  "status": "ONLINE"
}
```

---

### Get Camera Detail
**GET** `/cameras/{id}/`

---

### Update Camera
**PUT / PATCH** `/cameras/{id}/` *(ADMIN only)*

---

### Delete Camera
**DELETE** `/cameras/{id}/` *(ADMIN only)*

---

### Update Camera Status
**PATCH** `/cameras/{id}/status/`

**Body:**
```json
{ "status": "OFFLINE" }
```

---

### Live MJPEG Feed
**GET** `/cameras/{id}/feed/`

**Auth:** None required (public, browser `<img>` compatible).  
Streams a Motion-JPEG video feed directly from the camera RTSP source.  
The `CameraFeedWithOverlay` React component consumes this URL as the `<img src>`.

---

## 3. Alert Endpoints

### List Alerts
**GET** `/alerts/`

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `status` | string | `ACTIVE`, `ACKED`, `RESOLVED` |
| `camera_id` | string | Filter by camera ObjectId |
| `alert_type` | string | e.g. `THEFT_DETECTED` |
| `start_date` | ISO string | Range filter |
| `end_date` | ISO string | Range filter |

**Response (200):**
```json
{
  "count": 5,
  "results": [
    {
      "id": "6629def...",
      "camera_id": "6629abc...",
      "camera_details": {
        "id": "6629abc...",
        "name": "Main Entrance Camera",
        "location": "Building A - Main Entrance"
      },
      "alert_type": "THEFT_DETECTED",
      "severity": "HIGH",
      "timestamp": "2026-04-28T14:30:00Z",
      "status": "ACTIVE",
      "video_url": "https://res.cloudinary.com/...mp4",
      "metadata": {
        "confidence": 0.95,
        "detected_by": "CONTINUOUS_MONITOR",
        "fps": 28.5
      }
    }
  ]
}
```

---

### Get Alert Detail
**GET** `/alerts/{id}/`

---

### Acknowledge Alert
**PATCH** `/alerts/{id}/acknowledge/`

**Body:**
```json
{ "status": "ACKED" }
```

---

### Get Active Alerts
**GET** `/alerts/active/`

Returns all alerts with `status=ACTIVE`.

---

## 4. Incident Endpoints

### List Incidents
**GET** `/incidents/`

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `status` | string | `CREATED`, `ASSIGNED`, `ACKNOWLEDGED`, `RESOLVED` |
| `assigned_to` | integer | Filter by user ID |
| `my_incidents` | string | `"true"` to return only own incidents (Guard use) |

**Response (200):**
```json
{
  "count": 3,
  "results": [
    {
      "id": "6629ghi...",
      "alert_id": "6629def...",
      "alert_details": {
        "id": "6629def...",
        "alert_type": "THEFT_DETECTED",
        "severity": "HIGH"
      },
      "assigned_to": "6629xyz...",
      "assigned_to_details": {
        "username": "guard_john",
        "role": "SECURITY_GUARD"
      },
      "status": "ASSIGNED",
      "notes": "Investigating the incident",
      "created_at": "2026-04-28T14:35:00Z",
      "updated_at": "2026-04-28T15:00:00Z"
    }
  ]
}
```

---

### Assign Incident
**PATCH** `/incidents/{id}/assign/`

**Body:**
```json
{
  "assigned_to": "6629xyz...",
  "notes": "Assigning to guard on duty"
}
```

---

### Update Incident Status
**PATCH** `/incidents/{id}/status/`

**Body:**
```json
{
  "status": "ACKNOWLEDGED",
  "notes": "On-site, investigating"
}
```

---

## 5. Surveillance Endpoints

### Ingest AI Event
**POST** `/surveillance/ingest/`

Bridges the AI engine's output to the Alert + Incident creation pipeline.

**Body:**
```json
{
  "camera_id": "6629abc...",
  "event_type": "theft_detected",
  "frame_url": "http://storage.example.com/frames/frame123.jpg",
  "ai_data": {
    "confidence": 0.95,
    "bounding_boxes": [[100, 200, 300, 400]],
    "detected_objects": ["person"]
  }
}
```

**Response (201):**
```json
{
  "surveillance_event": { "id": "6629jkl...", "event_type": "theft_detected" },
  "alert_created": true,
  "incident_created": true
}
```

---

## 6. Tracking Ingest Endpoint

> **Note:** The old Tracking UI page (list/detail/stats endpoints) has been deprecated and removed.
> Only the **ingest** endpoint remains, used exclusively by the AI pipeline.

### Ingest Tracking Data *(AI Pipeline — internal)*
**POST** `/tracking/ingest/`

**Auth:** `Bearer <access_token>` (service-to-service from pipeline)

**Body:**
```json
{
  "camera_id": "6629abc...",
  "vector": [0.123, 0.456, 0.789],
  "person_id": "PERSON_abc123"
}
```

> If `person_id` is omitted, one is auto-generated from the vector hash.

**Response (201):**
```json
{
  "tracking_record": {
    "id": "6629mno...",
    "person_id": "PERSON_abc123",
    "camera_id": "6629abc...",
    "timestamp": "2026-04-28T14:00:00Z"
  },
  "message": "Tracking data ingested successfully"
}
```

---

## 7. Mobile / Notification Endpoints

### Send SMS
**POST** `/mobile/send-sms/` *(ADMIN / SECURITY_INCHARGE only)*

**Body:**
```json
{
  "phone_number": "+1234567890",
  "message": "Alert: Theft detected at Main Entrance"
}
```

---

### Send Email
**POST** `/mobile/send-email/` *(ADMIN / SECURITY_INCHARGE only)*

**Body:**
```json
{
  "email_address": "guard@example.com",
  "subject": "Security Alert",
  "message": "Theft detected at Main Entrance at 14:30"
}
```

---

### Send Bulk Notification
**POST** `/mobile/send-bulk/` *(ADMIN / SECURITY_INCHARGE only)*

**Body:**
```json
{
  "user_ids": ["6629abc...", "6629def..."],
  "subject": "System Alert",
  "message": "Multiple alerts detected in Zone A",
  "send_sms": true,
  "send_email": true
}
```

---

## 8. Dashboard Endpoints

### Dashboard Overview
**GET** `/dashboard/overview/`

**Response (200):**
```json
{
  "cameras": { "total": 10, "online": 8, "offline": 2, "online_percentage": 80.0 },
  "alerts": { "total": 150, "active": 5, "today": 12, "this_week": 45,
              "by_severity": { "HIGH": 20, "MEDIUM": 80, "LOW": 50 } },
  "incidents": { "total": 50, "active": 3, "resolved": 45, "resolution_rate": 90.0 },
  "personnel": { "total_personnel": 15, "total_users": 20 },
  "surveillance_events": { "today": 50, "this_week": 300 },
  "timestamp": "2026-04-28T15:00:00Z"
}
```

---

### Alert Statistics
**GET** `/dashboard/alerts-stats/`

**Query Parameters:** `days` (default: 30)

---

### Incident Statistics
**GET** `/dashboard/incidents-stats/`

**Query Parameters:** `days` (default: 30)

---

### Recent Activity
**GET** `/dashboard/recent-activity/`

**Query Parameters:** `limit` (default: 20)

---

### Historical Reporting
**GET** `/dashboard/historical-reporting/`

Returns aggregated alert / incident data for the historical chart views.

---

## 9. Feedback Endpoints

### Submit Feedback
**POST** `/feedback/`

**Types:** `GENERAL`, `INCIDENT`, `FALSE_POSITIVE`, `TRUE_POSITIVE`

**Body:**
```json
{
  "type": "FALSE_POSITIVE",
  "message": "The 14:30 alert was a maintenance worker."
}
```

---

### List My Feedback
**GET** `/feedback/me/`

---

### Feedback Statistics
**GET** `/feedback/stats/` *(ADMIN only)*

---

## 10. Personnel Endpoints

### List Personnel
**GET** `/personnel/` *(ADMIN only)*

### Create Personnel
**POST** `/personnel/` *(ADMIN only)*

### Update Personnel
**PUT / PATCH** `/personnel/{id}/` *(ADMIN only)*

### Delete Personnel
**DELETE** `/personnel/{id}/` *(ADMIN only)*

---

## 11. AI Engine Endpoints

Base prefix: `/api/ai/`

> All AI endpoints require `Authorization: Bearer <access_token>` **except**
> `health/` (public) and `cameras/<pk>/realtime-tracking/` (public — same
> policy as the MJPEG feed, needed so the browser's native `EventSource` can
> open it without CORS pre-flight headers).

---

### Analyze Single Frame
**POST** `/ai/analyze-frame/`

Runs one-shot inference on a base64-encoded image. Enforces branch-level authorization for the given camera.

**Body:**
```json
{
  "frame": "<base64-encoded JPEG>",
  "camera_id": "6629abc...",
  "create_alert_on_theft": true,
  "save_to_db": true
}
```

**Response (200):**
```json
{
  "classification": "theft",
  "confidence": 0.87,
  "persons": 2,
  "tracks": 2,
  "alert_created": true,
  "alert_id": "6629def...",
  "tracks_data": [
    {
      "track_id": 1,
      "global_id": 5,
      "bbox": [120, 45, 260, 380],
      "x3d_score": 0.87,
      "confidence": 0.93,
      "is_suspicious": true
    }
  ],
  "suspicious_tracks": [{ "track_id": 1, "global_id": 5, "x3d_score": 0.87 }]
}
```

---

### Process Camera Frame
**POST** `/ai/process-camera/`

Captures a live frame from the camera's RTSP URL and runs inference. Enforces branch-level authorization.

**Body:**
```json
{ "camera_id": "6629abc..." }
```

**Response:** Same structure as `/ai/analyze-frame/`.

---

### Full Pipeline (Combined)
**POST** `/ai/full-pipeline/`

Accepts either `frame` (base64) **or** `camera_id`. Routes internally to the appropriate view.

---

### Start Continuous Monitor
**POST** `/ai/monitor/start/` *(ADMIN / SECURITY_INCHARGE only)*

Starts a background thread pair (`_capture_loop` + `_monitor_loop`) that
processes the live camera stream at full camera FPS and publishes SSE events.
The `ai_monitoring_enabled` flag is persisted to MongoDB so the state
survives server restarts. Enforces branch-level authorization (users can only start monitoring for cameras in their assigned branch, unless SUPER_ADMIN).

**Body:**
```json
{ "camera_id": "6629abc...", "restart": false }
```

**Response (200):**
```json
{
  "success": true,
  "message": "Started continuous monitoring",
  "already_running": false,
  "camera_id": "6629abc...",
  "camera_name": "Entrance Cam",
  "ai_monitoring_enabled": true
}
```

---

### Stop Continuous Monitor
**POST** `/ai/monitor/stop/` *(ADMIN / SECURITY_INCHARGE only)*

Enforces branch-level authorization.

**Body:**
```json
{ "camera_id": "6629abc..." }
```

**Response (200):**
```json
{
  "success": true,
  "message": "Stopped monitoring",
  "was_running": true,
  "camera_id": "6629abc...",
  "ai_monitoring_enabled": false
}
```

> Always returns HTTP 200, even if the monitor was already stopped, so
> the frontend toggle is never left in a stuck state.

---

### Monitor Status
**GET** `/ai/monitor/status/?camera_id=6629abc...`

Returns live process stats and the persisted `ai_monitoring_enabled` DB flag.

**Response (200):**
```json
{
  "camera_id": "6629abc...",
  "monitor": {
    "camera_id": "6629abc...",
    "is_running": true,
    "frames_processed": 1523,
    "frames_captured": 3041,
    "fps": 28.5,
    "capture_fps": 30.1,
    "elapsed_seconds": 53.4,
    "error_count": 0,
    "last_result": { "classification": "normal", "confidence": 0.12 }
  },
  "ai_monitoring_enabled": true
}
```

> When called without `camera_id`, returns all running monitors:
```json
{
  "monitors": { "6629abc...": { ... } },
  "total_monitors": 1
}
```

---

### Real-Time Tracking SSE Stream *(Canvas Overlay)*
**GET** `/api/ai/cameras/<camera_id>/realtime-tracking/`

**Auth:** None required (public — same policy as the MJPEG feed).  
Open with the browser's native `EventSource` API — DRF content negotiation
is intentionally bypassed by using a plain Django view instead of `APIView`
(which caused a 406 Not Acceptable on the browser's `Accept: text/event-stream` header).

**Protocol:** Server-Sent Events (`text/event-stream`).  
The connection stays open indefinitely. A `: keepalive` comment is sent
every 25 seconds when there is no new data so proxies do not time out.

**Initial handshake event** (sent once on connection):
```
data: {"type": "connected", "camera_id": "6629abc..."}
```

**Tracking event** (sent at up to 10 FPS while the monitor is running):
```json
{
  "camera_id":      "6629abc...",
  "timestamp":      "2026-04-28T10:00:00.123Z",
  "frame_width":    640,
  "frame_height":   480,
  "classification": "theft",
  "confidence":     0.87,
  "alert_triggered": true,
  "suspicious_ids": [1],
  "tracks": [
    {
      "track_id":     1,
      "global_id":    5,
      "bbox":         [120, 45, 260, 380],
      "x3d_score":    0.87,
      "confidence":   0.93,
      "is_suspicious": true
    }
  ]
}
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `camera_id` | string | Camera MongoDB ObjectId |
| `timestamp` | ISO-8601 | Server-side timestamp of the processed frame |
| `frame_width` | integer | **Native width** of the AI-processed frame (e.g. 640). Frames are downscaled to 640×480 before inference. |
| `frame_height` | integer | **Native height** of the AI-processed frame (e.g. 480). |
| `tracks` | array | All active DeepSORT tracks in this frame |
| `tracks[].track_id` | integer | Short-lived DeepSORT local track ID |
| `tracks[].global_id` | integer | Cross-camera Re-ID persistent identity |
| `tracks[].bbox` | `[x1, y1, x2, y2]` | Bounding box in **native 640×480 pixel coordinates** |
| `tracks[].x3d_score` | float 0–1 | X3D activity score: ≥ 0.50 = suspicious, ≥ 0.80 = theft |
| `tracks[].confidence` | float 0–1 | YOLO detection confidence |
| `tracks[].is_suspicious` | boolean | **True** if the backend has flagged this track as a thief (via registry or score threshold). Properly serialized in every SSE payload. |
| `suspicious_ids` | integer[] | `track_id` values whose `x3d_score ≥ 0.50` |
| `alert_triggered` | boolean | `true` when `classification == "theft"` (x3d_score ≥ 0.80) |
| `classification` | string | `"theft"` or `"normal"` |
| `confidence` | float | Highest X3D score across all tracks in this frame |

> **Resolution Bridge:** `frame_width` / `frame_height` are 640 / 480 (the
> post-downscale size passed to YOLO/DeepSORT). The displayed video element
> may be a different CSS pixel size. The frontend **must** scale every bbox
> coordinate before drawing.

**Coordinate scaling — exact frontend formula:**
```javascript
const scaleX = canvas.clientWidth  / frame_width;   // e.g. 800 / 640 = 1.25
const scaleY = canvas.clientHeight / frame_height;  // e.g. 600 / 480 = 1.25

const drawX = bbox[0] * scaleX;
const drawY = bbox[1] * scaleY;
const drawW = (bbox[2] - bbox[0]) * scaleX;
const drawH = (bbox[3] - bbox[1]) * scaleY;

ctx.strokeRect(drawX, drawY, drawW, drawH);
```

**Error (404) — camera not found:**
```json
{ "error": "Camera 6629abc... not found" }
```

---

### Stop Tracking Suspect
**POST** `/ai/suspects/<global_id>/stop-tracking/`

**Auth:** `Bearer <access_token>` (required)  
**Roles:** Any authenticated user (enforces JWT but not a role restriction).

Clears a specific `global_id` from the `active_thief_global_ids` in-memory
registry, immediately stopping bounding boxes and alerts for that identity
across all cameras. The frontend must **also** dispatch the
`ai-suspect-cleared` CustomEvent to wipe `knownThievesRef` instantly.

**Response (200):**
```json
{
  "success": true,
  "message": "Stopped tracking suspect 5"
}
```

Or if the suspect was not actively tracked:
```json
{
  "success": true,
  "message": "Suspect 5 was not actively tracked"
}
```

---

### Model Info
**GET** `/ai/model-info/`

Returns load status of YOLO, OSNet, and X3D models.

**Response (200):**
```json
{
  "yolo": { "name": "YOLOv8m", "loaded": true },
  "osnet": { "name": "OSNet-AIN", "loaded": true },
  "x3d": { "name": "X3D-M (custom)", "loaded": true },
  "device": "cuda"
}
```

---

### AI Health Check
**GET** `/ai/health/` *(public)*

```json
{ "status": "healthy", "models_loaded": true, "device": "cuda" }
```

---

## Error Responses

| Code | Meaning | Body |
|------|---------|------|
| 400 | Bad Request | `{ "error": "...", "details": {...} }` |
| 401 | Unauthorized | `{ "detail": "Authentication credentials were not provided." }` |
| 403 | Forbidden | `{ "detail": "You do not have permission to perform this action." }` |
| 404 | Not Found | `{ "error": "Resource not found" }` |
| 503 | AI Not Ready | `{ "error": "AI service not initialized. Models may still be loading." }` |

---

## Role Permissions Summary

| Endpoint Group | ADMIN | SECURITY_INCHARGE | SECURITY_GUARD |
|----------------|-------|-------------------|----------------|
| Auth | ✅ | ✅ | ✅ |
| Cameras (Read) | ✅ | ✅ | ✅ |
| Cameras (Write) | ✅ | ❌ | ❌ |
| Alerts (Read) | ✅ | ✅ | ✅ (own) |
| Alerts (Acknowledge) | ✅ | ✅ | ❌ |
| Incidents (Read All) | ✅ | ✅ | Own only |
| Incidents (Assign) | ✅ | ✅ | ❌ |
| Dashboard | ✅ | ✅ | Limited |
| Notifications | ✅ | ✅ | ❌ |
| Feedback | ✅ | ✅ | ✅ |
| AI Monitor Start/Stop | ✅ | ✅ | ❌ |
| AI Monitor Status | ✅ | ✅ | ✅ |
| Stop Tracking Suspect | ✅ | ✅ | ❌ |
| SSE Real-Time Stream | Public | Public | Public |
| MJPEG Feed | Public | Public | Public |

---

*For architecture details and AI pipeline internals, see `AI_ENGINE_INTEGRATION.md`.*
*For onboarding and project structure, see `PROJECT_SUMMARY.md`.*
