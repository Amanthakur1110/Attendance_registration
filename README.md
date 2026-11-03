# Student Face-Photo Registration System

A robust, production-grade face-photo enrollment system for students with **Flask backend** and **React (Vite + TypeScript) frontend** organized as a clean monorepo.

The user flow mimics **Google / Apple Face ID enrollment**:
1. **Roll Number** input (e.g. `524cs0019`)
2. **Email OTP** verification (`<roll>@iiitk.ac.in` via Gmail SMTP_SSL; delivery runs in a background worker so the request responds immediately)
3. **Live-guided multi-pose face capture** (Front, Left, Right, Up) with automatic capture and backend-verified pose checks
4. **Instant authoritative backend validation** (face detection, bounds check, blur check, head pose angles, duplicate SHA-256 check, and same-person embedding cosine similarity)
5. **Session-safe completion & resume support**

---

## Tech Stack

### Backend
- **Python 3.10+**, **Flask 3.x** with Application Factory and Blueprints.
- **SQLite** via **SQLAlchemy 2.x** (`instance/app.db`) with automatic table creation on startup, WAL journal mode, and foreign keys enabled.
- **Flask-Limiter**: Rate limiting per IP and per roll number (OTP generation 1/60s, 5/hr; OTP verification 10/min; uploads 30/hr).
- **Face Analysis**: [InsightFace](https://github.com/deepinsight/insightface) (`buffalo_s` or `buffalo_l` on ONNX Runtime CPU). Single model load at startup with thread-safe inference lock.
- **Image Processing**: OpenCV Headless (`opencv-python-headless`), NumPy, Pillow.
- **Production Server**: [Waitress](https://docs.pylonsproject.org/projects/waitress/en/latest/) (multithreaded WSGI) or Gunicorn.
- **Testing**: `pytest` test suite with mocked external services.

### Frontend
- **React 18**, **Vite**, **TypeScript**, **react-router-dom v6**.
- **Plain CSS**: Modern, responsive UI with zero heavy CSS/UI frameworks.
- **Camera Capture**: `navigator.mediaDevices.getUserMedia` + HTML5 `<video>` + `<canvas>`.
- **Live In-Browser Guidance**: `@mediapipe/tasks-vision` FaceLandmarker (local assets, fully offline capable, UX helper only; backend is always the authority).
- **Vite Proxy**: Dev server proxies `/api` to `http://127.0.0.1:5000` to preserve same-origin cookies.

---

## Project Structure

```
face-registration/
├── .env.example              # Environment variables template
├── .gitignore                # Git exclusions
├── Makefile                  # Build, test, and run automation
├── package.json              # Monorepo root npm scripts
├── README.md                 # This documentation
├── backend/
│   ├── requirements.txt      # Pinned Python dependencies
│   ├── run.py                # Development entry point
│   ├── wsgi.py               # Production WSGI entry point (Waitress / Gunicorn)
│   ├── app/
│   │   ├── __init__.py       # create_app factory, proxy fix, security headers, SPA serve
│   │   ├── config.py         # Configuration loader & startup validation
│   │   ├── extensions.py     # SQLAlchemy & Limiter singletons
│   │   ├── models/           # User, Otp, Photo models
│   │   ├── api/
│   │   │   ├── auth.py       # /api/auth (send-otp, verify-otp, logout, me)
│   │   │   ├── photos.py     # /api/photos (upload, status)
│   │   │   └── errors.py     # HTTP error handlers
│   │   ├── services/
│   │   │   ├── otp_service.py    # HMAC-SHA256 OTP hashing, verification, cooldown
│   │   │   ├── mail_service.py   # Gmail SMTP_SSL HTML + text email dispatcher
│   │   │   ├── face_service.py   # InsightFace singleton & cosine similarity
│   │   │   ├── pose_service.py   # Pose angle definitions & classifications
│   │   │   └── photo_service.py  # Validation pipeline & atomic image persistence
│   │   └── utils/
│   │       ├── validators.py # Roll regex & image magic-byte validators
│   │       ├── security.py   # @login_required decorator & session helpers
│   │       └── responses.py  # Standardized json_ok / json_error responses
│   ├── scripts/
│   │   ├── download_models.py # Pre-downloads buffalo_s / buffalo_l models
│   │   └── calibrate_pose.py  # Diagnostic tool for yaw/pitch angles
│   ├── tests/                # Comprehensive pytest suite
│   ├── instance/             # SQLite app.db and app.log
│   └── photos/               # Saved photos: photos/<roll>/<roll>_<n>_<pose>.jpg
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    ├── public/               # Static assets & favicon
    └── src/
        ├── api/              # client.ts, auth.ts, photos.ts
        ├── components/       # CameraView, PoseGuide, PoseProgress, OtpInput, Alert, Button
        ├── config/           # poses.ts (matching backend angle thresholds)
        ├── hooks/            # useCamera, useFaceLandmarker, useCountdown, useAuthGuard
        ├── pages/            # LoginPage, OtpPage, CapturePage, DonePage
        ├── styles/           # global.css
        ├── types/            # TypeScript definitions
        ├── App.tsx
        ├── main.tsx
        └── routes.tsx
```

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** and **npm**
- A **Gmail account** with 2-Step Verification enabled (to generate a Google App Password)

---

## Quick Start (Development)

### 1. Configure Environment Variables
Copy `.env.example` to `.env` in the project root:
```bash
cp .env.example .env
```
Edit `.env` and fill in:
```env
APP_ENV=development
SECRET_KEY=generate_with_python_-c_"import secrets; print(secrets.token_hex(32))"
HOST=127.0.0.1
PORT=5000
PUBLIC_URL=http://localhost:5000

GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=abcd-efgh-ijkl-mnop
EMAIL_DOMAIN=iiitk.ac.in
```

> **Setting up Gmail App Password:**
> 1. Go to your [Google Account Security](https://myaccount.google.com/security).
> 2. Enable **2-Step Verification**.
> 3. Search for **App passwords** (or go to `https://myaccount.google.com/apppasswords`).
> 4. Create a new App Password named `FaceRegistration`.
> 5. Copy the 16-character code into `GMAIL_APP_PASSWORD` in your `.env`.
> 6. *Note for students:* Remind them to check their **SPAM / Junk** folder if OTP doesn't arrive in Inbox within 30 seconds.

### 2. Install Backend Dependencies & Download Models
```bash
pip install -r backend/requirements.txt
python backend/scripts/download_models.py --model buffalo_s
```

### 3. Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

### 4. Run Development Servers
Open two terminal windows:

**Terminal 1 (Backend - Flask on port 5000):**
```bash
python backend/run.py
```
*(Or use `make dev-backend`)*

**Terminal 2 (Frontend - Vite on port 5173):**
```bash
cd frontend
npm run dev
```
*(Or use `make dev-frontend`)*

Open your browser to: **`http://localhost:5173`**

---

## Production Deployment: Single Machine + Ngrok

In production, Flask serves both the compiled React frontend (`frontend/dist`) and all `/api/*` endpoints from a single port without CORS.

### 1. Build Frontend & Run with Waitress
```bash
# Build React SPA
cd frontend && npm run build && cd ..

# Update .env for production
# APP_ENV=production
# PUBLIC_URL=https://your-domain.ngrok-free.app

# Run Waitress production WSGI server
python backend/wsgi.py
```
*(Or run `make serve`)*

### 2. Expose with Ngrok (for mobile / HTTPS testing)
Modern browsers require a **Secure Context (HTTPS or localhost)** to access `navigator.mediaDevices.getUserMedia`. To test from your smartphone:

1. Install [ngrok](https://ngrok.com/) and authenticate your token.
2. Start the tunnel forwarding to port 5000:
   ```bash
   ngrok http 5000
   ```
3. Copy the public URL (e.g. `https://xxxx-xx-xx.ngrok-free.app`).
4. Update `.env`:
   ```env
   APP_ENV=production
   PUBLIC_URL=https://xxxx-xx-xx.ngrok-free.app
   ```
5. Restart `python backend/wsgi.py`.
6. Open the ngrok HTTPS link on your smartphone.
   *(Click "Visit Site" if ngrok displays a free-tier interstitial page).*
7. The browser will prompt for camera access over HTTPS and multi-pose face capture will work natively.

### 3. Health Check
Verify your backend is reachable behind the proxy:
```bash
curl https://xxxx-xx-xx.ngrok-free.app/api/health
# Returns: {"env":"production","message":"ok","ok":true}
```

---

## Pose Calibration & Tuning

Head pose angles are measured in degrees. The preview `<video>` is mirrored (CSS `transform: scaleX(-1)`) for natural selfie interaction, but the snapshot sent to the server is the **non-mirrored raw capture**.

Angle coordinate system:
- **Yaw**:
  - `> 0`: Person turns head to their **LEFT**
  - `< 0`: Person turns head to their **RIGHT**
- **Pitch**:
  - `> 0`: Person tilts head **UP** (chin raised)
  - `< 0`: Person tilts head **DOWN** (chin lowered)
- **Roll**:
  - In-plane tilt (kept within $\pm 20^\circ$)

### Pose Sequence Configuration

Both `backend/app/services/pose_service.py` and `frontend/src/config/poses.ts` share the exact configuration:

| Pose # | Name | Direction | Yaw Range | Pitch Range | Prompt Text |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | `FRONT` | Straight | $[-12^\circ, +12^\circ]$ | $[-12^\circ, +12^\circ]$ | *"Look straight at the camera"* |
| **2** | `LEFT` | Person's Left | $[+15^\circ, +55^\circ]$ | $[-18^\circ, +18^\circ]$ | *"Turn slightly toward your left shoulder and keep both eyes visible"* |
| **3** | `RIGHT` | Person's Right | $[-55^\circ, -15^\circ]$ | $[-18^\circ, +18^\circ]$ | *"Turn slightly toward your right shoulder and keep both eyes visible"* |
| **4** | `UP` | Chin Up | $[-15^\circ, +15^\circ]$ | $[+12^\circ, +30^\circ]$ | *"Lift your chin slightly up"* |

To test or calibrate camera angles for custom hardware:
```bash
# Test an image
python backend/scripts/calibrate_pose.py --image path/to/sample.jpg

# Interactive webcam test
python backend/scripts/calibrate_pose.py --webcam
```

---

## Backend Validation Rules

When a photo is POSTed to `/api/photos/upload`:
1. **Session Check**: Roll number is extracted strictly from the signed server session (cannot be spoofed in payload).
2. **Strict Sequence**: Pose must be the exact next pose in sequence. Re-submitting an accepted pose returns `409 POSE_ALREADY_ACCEPTED`.
3. **Magic Bytes**: Checks file header for valid JPEG (`FF D8 FF`) or PNG magic bytes; enforces max 2 MB file size.
4. **Single Face Detection**:
   - 0 faces detected $\rightarrow$ `422 NO_FACE`
   - $>1$ faces detected $\rightarrow$ `422 MULTIPLE_FACES`
   - Face confidence $< 0.70$ $\rightarrow$ rejected
5. **Framing & Boundary**: Face width must exceed 15% of frame width and must be entirely inside frame boundaries.
6. **Blurriness**: Variance of Laplacian on face crop must exceed 60.0.
7. **Pose Angle Check**: Measured yaw, pitch, and roll are verified against configured ranges with specific directional guidance hints.
8. **Anti-Duplicate Check**: SHA-256 hash must not match previously submitted photos for the student.
9. **Same-Person Identity Verification**:
   - Photo 1 generates the identity embedding.
   - Photos 2, 3, and 4 compute cosine similarity against Photo 1's embedding.
   - Must be $\ge 0.35$ cosine similarity; otherwise rejected with `422 DIFFERENT_PERSON`.
10. **Atomic Persistence**: Image written to a temporary file, then moved atomically via `os.replace` into `photos/<roll>/<roll>_<n>_<pose>.jpg`. If database insert fails, the file is immediately purged.

---

## Running Automated Tests

Run the complete test suite with `pytest`:
```bash
cd backend
python -m pytest tests/ -v
```

### Test Coverage Checklist:
- [x] **`test_roll_validation.py`**: Validates roll format (`524cs0019`), blocks path traversal (`../../etc`), spaces, and invalid lengths.
- [x] **`test_otp.py`**:
  - Roll `524cs0019` receives OTP to `524cs0019@iiitk.ac.in`.
  - Wrong OTP rejected.
  - Locked after 5 failed attempts.
  - Expired OTP rejected.
  - OTP is single-use only.
  - Completed students get `409 ALREADY_COMPLETED` without sending new OTP.
- [x] **`test_pose.py`**: Verifies angle classifications for Front, Left, Right, Up, in-plane roll, and InsightFace coordinate conventions.
- [x] **`test_upload_flow.py`**:
  - Unauthenticated requests return `401`.
  - Out-of-order pose upload returns `409 WRONG_POSE_ORDER`.
  - No-face and multi-face images rejected with `422`.
  - Blurry images rejected with `422 BLURRY_IMAGE`.
  - Non-matching pose angles rejected with `422 WRONG_POSE`.
  - Different person detected rejected with `422 DIFFERENT_PERSON`.
  - Full 4-step upload creates disk files and marks `user.completed = 1`.
  - Resume flow: Returning after 2 photos resumes directly at step 3.

---

## Manual Test Acceptance Script

| Step | Action | Expected Result |
| :--- | :--- | :--- |
| 1 | Enter roll `524cs0019` on Login page | OTP email is queued for `524cs0019@iiitk.ac.in`; the 60s cooldown timer displays immediately. |
| 2 | Enter invalid roll `../../etc` | Clear validation error: roll must be 6-15 alphanumeric lowercase chars. |
| 3 | Enter wrong OTP | Error shows remaining attempts counter. |
| 4 | Enter correct 6-digit OTP | Session established; automatically navigates to `/capture`. |
| 5 | Review Tips modal | Displays tips (lighting, no masks, 1 person) and "Start" button. |
| 6 | Camera stream | Video preview displays mirrored without a face-frame overlay. |
| 7 | Pose guidance | Real-time feedback updates: "Look straight", "Turn left", "Lift chin". |
| 8 | Auto-capture | Holding a suitable pose briefly triggers automatic upload and backend validation. |
| 9 | Upload status | Accepted photo thumbnail appears in the progress bar and advances to the next pose. |
| 10 | Refresh during capture | Refresh browser at Photo 3; status API resumes at Photo 3 without restarting. |
| 11 | Completion | After 4th photo, redirected to `/done` showing "Registration Complete!". |
| 12 | Re-login attempt | Entering `524cs0019` again returns "Photos already submitted for this roll number." |

---

## License
MIT License. Created for student registration portal.
