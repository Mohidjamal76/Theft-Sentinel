# Theft Sentinel – Live Streaming Infrastructure Setup (Complete Guide)

This documentation provides a **step-by-step, reproducible setup** for deploying a real-time video streaming pipeline using a VPS and MediaMTX. It is tailored for the Theft Sentinel system, where CCTV/mobile feeds are streamed to a backend for monitoring and AI processing.

---

# 1. VPS Setup (DigitalOcean)

## 1.1 Create Account

1. Go to: https://www.digitalocean.com/
2. Sign up and verify your account
3. Add payment method (required even for trials)

---

## 1.2 Create a Droplet (VPS)

### Recommended Specifications

| Parameter      | Value                                      |
| -------------- | ------------------------------------------ |
| OS             | Ubuntu 22.04 LTS                           |
| CPU            | 2 vCPU                                     |
| RAM            | 4 GB                                       |
| Disk           | 50–80 GB SSD                               |
| Region         | Closest to your location (e.g., Bangalore) |
| Authentication | SSH Key (recommended)                      |

---

### Steps

1. Click **Create → Droplets**
2. Select:

   * Ubuntu 22.04 LTS
3. Choose plan:

   * Basic → Regular → 2 vCPU / 4GB RAM
4. Choose datacenter region (low latency)
5. Add SSH key (or use password)
6. Click **Create Droplet**

---

## 1.3 Connect to VPS

```bash
ssh root@YOUR_VPS_IP
```

---

## 1.4 Initial Server Setup

Update system:

```bash
apt update && apt upgrade -y
```

Install basic tools:

```bash
apt install -y curl wget unzip nano
```

---

# 2. Install MediaMTX (Streaming Server)

## 2.1 Download Latest Version

```bash
wget https://github.com/bluenviron/mediamtx/releases/latest/download/mediamtx_linux_amd64.tar.gz
```

---

## 2.2 Extract Files

```bash
tar -xvzf mediamtx_linux_amd64.tar.gz
cd mediamtx
```

---

## 2.3 Run MediaMTX

```bash
./mediamtx
```

You should see logs like:

```
MediaMTX started
RTSP listener opened on :8554
WebRTC listener opened on :8889
```

---

## 2.4 Run in Background (Important)

```bash
nohup ./mediamtx &
```

---

# 3. Configure MediaMTX

Edit config file:

```bash
nano mediamtx.yml
```

---

## 3.1 Minimal Working Configuration

```yaml
logLevel: info

rtsp: true
rtmp: true
hls: true
webrtc: true
srt: true

hlsVariant: lowLatency
hlsSegmentDuration: 1s
hlsPartDuration: 200ms

webrtcAdditionalHosts:
  - YOUR_VPS_PUBLIC_IP

webrtcICEServers:
  - stun:stun.l.google.com:19302

paths:
  all_others:
```

---

## 3.2 Restart MediaMTX

```bash
pkill mediamtx
./mediamtx
```

---

# 4. Open Required Ports

## 4.1 DigitalOcean Firewall

Allow:

| Port | Protocol | Purpose    |
| ---- | -------- | ---------- |
| 8554 | TCP      | RTSP       |
| 1935 | TCP      | RTMP       |
| 8888 | TCP      | HLS        |
| 8889 | TCP      | WebRTC     |
| 8189 | UDP      | WebRTC ICE |
| 8890 | UDP      | SRT        |

---

## 4.2 Ubuntu Firewall

```bash
ufw allow 8554/tcp
ufw allow 1935/tcp
ufw allow 8888/tcp
ufw allow 8889/tcp
ufw allow 8189/udp
ufw allow 8890/udp
ufw enable
```

---

# 5. Streaming from Mobile (Larix Broadcaster)

## 5.1 Install App

Download **Larix Broadcaster** from Play Store / App Store

---

## 5.2 Configure SRT Stream

### Connection Settings

| Field | Value                                   |
| ----- | --------------------------------------- |
| URL   | srt://YOUR_VPS_IP:8890?streamid=publish |

---

## 5.3 IMPORTANT: Bitrate Settings (Based on Your Internet)

### If Upload Speed = 0.38 Mbps

Set:

| Setting       | Value        |
| ------------- | ------------ |
| Resolution    | 640x360      |
| FPS           | 15–20        |
| Video Bitrate | 250–300 Kbps |
| Audio Bitrate | 32–64 Kbps   |

---

# 6. Access the Stream

## 6.1 RTSP (Primary Method Used in Application)

```bash
rtsp://YOUR_VPS_IP:8554/cam1
```

Used directly in the application to preserve existing logic and avoid custom player implementation.
*Note: The backend's `CameraStreamManager` automatically detects the protocol (via `urllib.parse`) and natively supports direct HTTP MJPEG webcams as well, without mutating the URL.*

---

## 6.2 WebRTC (Optional)

```
http://YOUR_VPS_IP:8889/cam1
```

---

## 6.3 HLS (Optional)

```
http://YOUR_VPS_IP:8888/cam1/index.m3u8
```

---

# 7. Common Errors & Fixes

---

## Error: "reader is too slow, discarding frames"

### Cause:

* Upload bandwidth is too low

### Fix:

* Reduce bitrate (MOST IMPORTANT)

---

## Error: "no stream available"

### Cause:

* Stream not published yet

### Fix:

* Start Larix stream first

---

## Error: High latency / lag

### Causes:

1. High bitrate
2. Poor internet upload
3. RTSP over TCP

### Fix:

* Lower bitrate
* Optimize RTSP settings or consider WebRTC if needed

---

# 8. System Architecture (Theft Sentinel)

```
Mobile Camera / CCTV
        ↓
     SRT Stream
        ↓
     MediaMTX VPS
        ↓
        RTSP
 (Primary Streaming Protocol)
        ↓
   Django Backend
        ↓
   AI Processing (YOLO, Tracking)
        ↓
   Theft Alerts System
```

---

# 9. Recommended Improvements (Production)

## 9.1 Upgrade Internet

Minimum:

```
Upload Speed ≥ 2 Mbps
```

---

## 9.2 Add TURN Server (for WebRTC)

Improves connectivity in restricted networks (optional if WebRTC is used).

---

## 9.3 Use NGINX Reverse Proxy

For:

* HTTPS
* Domain access

---

## 9.4 Enable Recording

```yaml
record: true
recordPath: ./recordings/%path/%Y-%m-%d_%H-%M-%S
```

---

# 10. Final Checklist

✅ VPS created
✅ MediaMTX installed
✅ Ports opened
✅ Stream publishing via SRT
✅ Playback working (RTSP)
✅ Bitrate optimized

---

# 🎯 Final Note

The performance of the system depends heavily on:

```
Upload Bandwidth ≥ Stream Bitrate
```

If this condition is not met, **frame drops and lag are unavoidable**.

---

End of Documentation
