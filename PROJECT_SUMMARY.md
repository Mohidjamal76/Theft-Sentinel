> **Onboarding Guide for New Developers**
> Architecture Snapshot — Stable Milestone (April 2026)

---

## 1. What Is Theft Sentinel?

Theft Sentinel is a real-time AI-powered retail security monitoring system.
It ingests live RTSP camera streams, runs a multi-model computer vision
pipeline to detect theft behavior, and surfaces alerts to security personnel
through a role-stratified web dashboard. Suspect bounding boxes are drawn
live on camera feeds via WebSocket-free Server-Sent Events.

---

## 2. Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 4.x + Django REST Framework |
| **Database** | MongoDB (via `django-mongodb-backend`) |
| **AI / CV** | PyTorch · OpenCV · YOLOv8 · DeepSORT · OSNet · X3D |
| **Re-ID Index** | FAISS (Facebook AI Similarity Search) |
| **Video Storage** | Cloudinary (alert clip hosting) |
| **Frontend** | React 18 + Vite |
| **State Management** | Recoil |
| **Styling** | Tailwind CSS + custom design tokens |
| **Real-Time Push** | Server-Sent Events (SSE) — native Django `StreamingHttpResponse` |
| **Auth** | JWT (Simple JWT — `access_token` / `refresh_token` stored in `localStorage`) |

---

## 3. Project Structure

```
Final_FYP_Project/
│
├── theft_sentinel_backend/          # Django project root
│   │
│   ├── config/                      # Django configuration
│   │   ├── settings.py
│   │   ├── urls.py                  # Root URL router
│   │   └── mongodb.py               # MongoDB connection
│   │
│   ├── apps/
│   │   ├── accounts/                # Custom User model + JWT auth + RBAC
│   │   ├── cameras/                 # Camera model + MJPEG feed + RTSP proxy
│   │   ├── alerts/                  # Alert model + Cloudinary clip
│   │   ├── incidents/               # Incident management
│   │   ├── tracking/                # TrackingRecord model + ingest endpoint
│   │   │                            #   ⚠ Standalone Tracking UI (list/detail/
│   │   │                            #     stats endpoints) was DEPRECATED and
│   │   │                            #     removed. Only the AI pipeline's
│   │   │                            #     POST /tracking/ingest/ remains.
│   │   ├── ai_engine/               # AI engine app
│   │   │   ├── api/
│   │   │   │   ├── views.py         # All AI HTTP views (monitor, SSE, stop-tracking)
│   │   │   │   └── urls.py          # AI endpoint router
│   │   │   ├── services/
│   │   │   │   ├── continuous_monitor.py  # Capture loop + inference loop + clip upload
│   │   │   │   ├── inference_runner.py    # AI orchestration (YOLO→DeepSORT→OSNet→X3D)
│   │   │   │   ├── ai_service.py          # Singleton model loader + shared state
│   │   │   │   ├── sse_registry.py        # SSE pub/sub broker
│   │   │   │   └── clip_encoding.py       # OpenCV VideoWriter wrapper
│   │   │   └── models.py            # AIInference, DetectionTrack
│   │   ├── surveillance/            # SurveillanceEvent ingest
│   │   ├── dashboard/               # Aggregate stats endpoints
│   │   ├── feedback/                # Guard feedback submission
│   │   ├── personnel/               # Personnel management (admin only)
│   │   └── mobile/                  # SMS / Email notification
│   │
│   ├── ai_pipeline/                 # Pure-Python ML modules (no Django ORM)
│   │   ├── ai_config/config.py      # Thresholds & hyper-parameters
│   │   ├── detection/               # YOLOv8 wrapper
│   │   ├── tracking/                # DeepSORT tracker
│   │   ├── reid/                    # OSNet feature extractor
│   │   ├── matching/                # FAISS matcher + identity DB
│   │   └── x3d/                     # X3D theft classifier
│   │
│   ├── API_DOCUMENTATION.md         # ← Full endpoint reference (this repo)
│   ├── AI_ENGINE_INTEGRATION.md     # ← Pipeline + architecture gotchas
│   └── PROJECT_SUMMARY.md           # ← This file
│
└── theft-sentinel-frontend/         # React + Vite SPA
    └── src/
        ├── pages/
        │   ├── auth/                # Login, ForgotPassword, ResetPassword
        │   ├── dashboard/           # Overview, HistoricalReporting, GuardDashboard
        │   ├── cameras/             # List, Create, Edit, ControlRoom
        │   ├── alerts/              # List, View, GuardAlerts
        │   ├── incidents/           # List, View, MyIncidents, Unassigned
        │   ├── ai/
        │   │   └── Dashboard.jsx    # AI Dashboard (health + model info + frame analyzer)
        │   │   # ⚠ ai/History.jsx was DEPRECATED and removed.
        │   ├── tracking/
        │   │   # ⚠ tracking/Records.jsx and tracking/PersonPath.jsx were
        │   │   #   DEPRECATED and removed. The tracking/ directory is empty.
        │   ├── feedback/
        │   └── personnel/
        ├── components/
        │   ├── CameraFeedWithOverlay.jsx  # MJPEG <img> + SSE canvas overlay
        │   ├── LiveTrackingNodeGraph.jsx  # Suspect node graph (React Portal)
        │   ├── Sidebar.jsx               # Role-filtered navigation
        │   └── AI/                       # FrameAnalyzer, AIHealthStatus, etc.
        ├── router/
        │   └── AppRouter.jsx             # Role-protected routes
        ├── hooks/
        │   ├── useRealtimeTracking.js    # SSE EventSource hook
        │   └── useAIEngine.js            # AI API hook
        └── api/                          # Axios client modules
```

---

## 4. Database Schema

All models use MongoDB via `django-mongodb-backend`. Each model uses an
`ObjectIdAutoField` as its primary key.

### `User` (`accounts_user`)

| Field | Type | Notes |
|-------|------|-------|
| `id` | ObjectId (PK) | Auto-generated |
| `username` | CharField | Unique, indexed |
| `email` | EmailField | Unique, indexed |
| `role` | CharField | `ADMIN`, `SECURITY_INCHARGE`, `SECURITY_GUARD` |
| `is_active` | BooleanField | Default: `True` |
| `created_at` | DateTimeField | Auto |

---

### `Camera` (`cameras`)

| Field | Type | Notes |
|-------|------|-------|
| `id` | ObjectId (PK) | |
| `name` | CharField | |
| `rtsp_url` | CharField | RTSP or HTTP stream URL |
| `location` | CharField | Human-readable location |
| `zone` | CharField | Indexed |
| `status` | CharField | `ONLINE` / `OFFLINE`, indexed |
| `ai_monitoring_enabled` | BooleanField | Persisted toggle — survives server restart |
| `last_feed_timestamp` | DateTimeField | Updated by external feed health checker |
| `created_at` | DateTimeField | |

---

### `Alert` (`alerts`)

| Field | Type | Notes |
|-------|------|-------|
| `id` | ObjectId (PK) | |
| `camera_id` | ForeignKey → Camera | CASCADE |
| `alert_type` | CharField | e.g. `THEFT_DETECTED` |
| `severity` | CharField | `HIGH` / `MEDIUM` / `LOW` |
| `status` | CharField | `ACTIVE`, `ACKED`, `RESOLVED` |
| `metadata` | JSONField | AI confidence, fps, suspicious tracks |
| `video_url` | URLField | Cloudinary clip URL (nullable) |
| `video_public_id` | CharField | Cloudinary asset ID (nullable) |
| `timestamp` | DateTimeField | Indexed |

---

### `AIInference` (`ai_inferences`)

| Field | Type | Notes |
|-------|------|-------|
| `id` | ObjectId (PK) | |
| `camera_id` | ForeignKey → Camera | |
| `detections` | JSONField | YOLO raw detections |
| `poses` | JSONField | Always `[]` in current pipeline |
| `tracks` | JSONField | Full tracks list from SSE payload |
| `classification` | CharField | `theft` / `normal` |
| `confidence` | FloatField | 0–1 |
| `frame_metadata` | JSONField | frame_index, num_persons, raw_x3d_score |
| `processing_time_ms` | FloatField | |
| `alert` | ForeignKey → Alert | `SET_NULL` |
| `timestamp` | DateTimeField | Indexed |

---

### `TrackingRecord` (`tracking_records`)

Written by the AI pipeline via `TrackingService.save_tracks()`. **Not exposed
via any UI page** (the standalone Tracking UI was deprecated).

| Field | Type | Notes |
|-------|------|-------|
| `id` | ObjectId (PK) | |
| `person_id` | CharField | Re-ID cross-camera identity string, indexed |
| `camera_id` | ForeignKey → Camera | |
| `global_id` | IntegerField | FAISS global identity integer (nullable) |
| `vector` | JSONField | OSNet 512-d embedding snapshot |
| `confidence` | FloatField | YOLO detection confidence |
| `x3d_score` | FloatField | Latest X3D score at record time |
| `bbox` | JSONField | `[x1, y1, x2, y2]` |
| `location` | CharField | Camera location snapshot |
| `timestamp` | DateTimeField | Indexed |

---

### `Incident` (`incidents`)

| Field | Type | Notes |
|-------|------|-------|
| `id` | ObjectId (PK) | |
| `alert_id` | ForeignKey → Alert | |
| `assigned_to` | ForeignKey → User | Nullable |
| `status` | CharField | `CREATED`, `ASSIGNED`, `ACKNOWLEDGED`, `RESOLVED` |
| `notes` | TextField | |
| `created_at` / `updated_at` | DateTimeField | |

---

### `Feedback` (`feedback`)

| Field | Type | Notes |
|-------|------|-------|
| `id` | ObjectId (PK) | |
| `type` | CharField | `GENERAL`, `INCIDENT`, `FALSE_POSITIVE`, `TRUE_POSITIVE` |
| `message` | TextField | |
| `submitted_by` | ForeignKey → User | |
| `created_at` | DateTimeField | |

---

## 5. Role-Based Access Control (RBAC)

### Roles

| Role | Description |
|------|-------------|
| `ADMIN` | Full system access. Can add/edit/delete cameras, manage personnel, start/stop AI monitoring, view all alerts and incidents. |
| `SECURITY_INCHARGE` | Can start/stop AI monitoring, view all alerts and incidents, access the Control Room. Cannot manage cameras or personnel. |
| `SECURITY_GUARD` | Limited access. Can view the Control Room (live feeds only), view their own assigned incidents and alerts. Cannot start AI monitoring or access the dashboard. |

---

### Frontend Route Protection (`AppRouter.jsx`)

All authenticated routes are wrapped in a `<ProtectedRoute allowedRoles={[...]}>`
component. Attempting to access a route outside your role redirects you to
your role's home page.

**Key route access matrix:**

| Route | ADMIN | SECURITY_INCHARGE | SECURITY_GUARD |
|-------|-------|-------------------|-|
| `/dashboard` | ✅ | ✅ | ❌ → `/dashboard/guard` |
| `/dashboard/guard` | ❌ | ❌ | ✅ |
| `/cameras/control-room` | ✅ | ✅ | ✅ |
| `/cameras` (list/edit) | ✅ | ✅ (read) | ❌ |
| `/alerts` | ✅ | ✅ | ❌ |
| `/alerts/guard` | ❌ | ❌ | ✅ |
| `/incidents` | ✅ | ✅ | ❌ |
| `/incidents/my` | ❌ | ❌ | ✅ |
| `/ai/dashboard` | ✅ | ✅ | ❌ |
| `/feedback` | ✅ | ❌ | ❌ |
| `/feedback/my` | ❌ | ❌ | ✅ |
| `/personnel` | ✅ | ❌ | ❌ |
| `/tracking/*` | **DEPRECATED — removed** | | |
| `/ai/history` | **DEPRECATED — removed** | | |

> **Note:** `/cameras/control-room` is intentionally accessible to all three
> roles. Guards see only live camera feeds; the AI monitoring toggle and node
> graph controls are role-gated inside the component itself
> (`hasPermission(user, 'control_ai_monitoring')`).

---

### Sidebar Navigation (`Sidebar.jsx`)

The sidebar renders a role-filtered `menuItems` map. Each role sees only the
pages it is permitted to access. The `Tracking` and `AI History` entries have
been permanently removed from all role menus.

| Role | Visible Menu Items |
|------|--------------------|
| `ADMIN` | Dashboard · Historical Reporting · Control Room · Alerts · Incidents · AI Dashboard · Feedback · Personnel |
| `SECURITY_INCHARGE` | Dashboard · Historical Reporting · Alerts · Incidents · Control Room · AI Dashboard |
| `SECURITY_GUARD` | Dashboard (Guard) · Control Room · Alerts (Guard) · My Incidents · Feedback |

---

## 6. Module Responsibilities (Quick Reference)

### Backend

| Module | Responsibility |
|--------|---------------|
| `continuous_monitor.py` | Opens RTSP or HTTP stream natively (auto-detects protocol), runs two threads (capture + inference), downscales to 640×480, manages rolling frame buffer, uploads alert clips to Cloudinary, publishes SSE events |
| `stream_manager.py` | Persistent thread-safe `CameraStreamManager` for MJPEG feeds. Maintains exactly one `cv2.VideoCapture` per camera for both RTSP and HTTP URLs. Prevents reconnect storms with exponential backoff. |
| `inference_runner.py` | Orchestrates per-camera AI pipeline: YOLO → DeepSORT → OSNet → FAISS → X3D. Maintains isolated tracker and embedding buffers per instance. Returns standardized result dict |
| `ai_service.py` | Singleton that loads and holds model references (YOLO, OSNet, X3D, FAISS matcher). Provides `inference_lock` and `state_lock` for thread safety. Manages `active_thief_global_ids` registry |
| `sse_registry.py` | Thread-safe pub/sub broker. Each SSE client gets its own `queue.Queue`. `publish()` fans out to all subscribers; `unsubscribe()` fires on client disconnect |
| `clip_encoding.py` | Wraps OpenCV `VideoWriter` to encode a list of BGR frames into an MP4 file |

### Frontend

| Component | Responsibility |
|-----------|---------------|
| `CameraFeedWithOverlay.jsx` | Renders MJPEG `<img>` + transparent canvas overlay. Consumes SSE via `useRealtimeTracking` hook. Draws LERP-smoothed RED bounding boxes for suspects (with 3.5s TTL). Manages `knownThievesRef` permanent thief memory |
| `LiveTrackingNodeGraph.jsx` | Displays the cross-camera path graph for active suspects. Uses `React.createPortal` to escape CSS containment. Calls `StopTrackingView` API + dispatches `ai-suspect-cleared` CustomEvent |
| `useRealtimeTracking.js` | Opens `EventSource` connection to the SSE endpoint. Auto-reconnects on disconnect. Exposes `{ trackingData, connected }` |
| `AppRouter.jsx` | Defines all routes with role-based `ProtectedRoute` guards. Handles role-based redirects on auth state |
| `Sidebar.jsx` | Renders role-filtered navigation menu. Uses `authUserState` from Recoil |

---

## 7. Deprecated & Removed Modules

The following pages, routes, and API endpoints were **permanently removed**
in the post-stable-milestone cleanup. They must not be re-added without
explicit architectural review.

| Removed Item | Type | Was Located At |
|--------------|------|----------------|
| Tracking Records page | React page | `src/pages/tracking/Records.jsx` |
| Person Path page | React page | `src/pages/tracking/PersonPath.jsx` |
| AI History page | React page | `src/pages/ai/History.jsx` |
| `/tracking` route | AppRouter route | Removed |
| `/tracking/person-path` route | AppRouter route | Removed |
| `/ai/history` route | AppRouter route | Removed |
| `Tracking` sidebar entry | Sidebar nav | Removed from ADMIN + SECURITY_INCHARGE |
| `AI History` sidebar entry | Sidebar nav | Removed from ADMIN + SECURITY_INCHARGE |
| `TrackingRecordListCreateView` | Django view | `apps/tracking/views.py` — removed |
| `TrackingRecordDetailView` | Django view | `apps/tracking/views.py` — removed |
| `PersonTrackingPathView` | Django view | `apps/tracking/views.py` — removed |
| `TrackingStatsView` | Django view | `apps/tracking/views.py` — removed |
| `GET /api/tracking/` | API endpoint | Removed |
| `GET /api/tracking/records/` | API endpoint | Removed |
| `GET /api/tracking/records/<pk>/` | API endpoint | Removed |
| `GET /api/tracking/person/<id>/path/` | API endpoint | Removed |
| `GET /api/tracking/stats/` | API endpoint | Removed |
| `InferenceHistoryView` | Django view | `apps/ai_engine/api/views.py` — removed |
| `GET /api/ai/inference-history/` | API endpoint | Removed |

---

## 8. Local Development Setup

### Backend
```bash
cd theft_sentinel_backend
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend
```bash
cd theft-sentinel-frontend
npm install
npm run dev
```

### Environment Variables (`.env` in `theft_sentinel_backend/`)
```
SECRET_KEY=...
MONGODB_URI=mongodb://localhost:27017/theft_sentinel
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
VITE_API_BASE_URL=http://localhost:8000
```

---

## 9. Key Data Flows at a Glance

```
User logs in → JWT stored in localStorage as 'access_token'
                │
                ▼
Control Room opens → CameraCardWithAI.jsx polls /ai/monitor/status/ (every 10s)
                   → Toggles AI monitoring via POST /ai/monitor/start|stop/
                │
                ▼
Monitor starts → ContinuousMonitor spawns capture + inference threads
                │
                ▼
Theft detected → Alert created in DB → Clip uploaded to Cloudinary
              → SSE event pushed to all subscribed EventSource clients
                │
                ▼
Frontend canvas → draws RED bounding box on CameraFeedWithOverlay
Frontend graph  → LiveTrackingNodeGraph shows camera path for suspect
                │
                ▼
Guard clicks "Stop Tracking" → POST /api/ai/suspects/<id>/stop-tracking/ (JWT)
                             → window.dispatchEvent('ai-suspect-cleared')
                             → All camera canvases instantly clear that suspect
```

---

*For complete API reference, see `API_DOCUMENTATION.md`.*  
*For AI pipeline internals and optimization details, see `AI_ENGINE_INTEGRATION.md`.*
