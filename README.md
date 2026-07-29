# Temple AI Crowd Management System

## Project Structure

```
crowd_management_backend/
├── backend/          ← FastAPI (Python) — AI Engine
│   ├── app/
│   │   ├── ai/               Phase 3 — YOLO Model Manager + Detector
│   │   ├── person_counter/   Phase 4 — Entry/Exit Counting
│   │   ├── queue_management/ Phase 5 — Queue Monitoring
│   │   ├── zone_monitoring/  Phase 6 — Zone Monitoring
│   │   ├── face_recognition/ Phase 7 — Face Recognition
│   │   ├── camera/           Camera Manager + Frame Buffer
│   │   ├── events/           Redis Pub/Sub + WebSocket
│   │   └── api/v1/           REST API Endpoints
│   ├── models/
│   │   └── yolo11x.pt        YOLO Model (GPU)
│   └── .env                  Backend config
│
├── frontend/         ← Laravel (PHP) — Dashboard
│   ├── app/
│   ├── resources/views/
│   ├── routes/
│   └── .env                  Frontend config
│
├── start.bat         ← Double-click to start both servers (Windows)
├── stop.bat          ← Stop all servers
├── docker-compose.yml← AWS / Docker deployment
├── nginx.conf        ← Nginx reverse proxy config
└── README.md

```

---

## Local Development (Windows)

### Quick Start — Double click karo
```
C:\crowd_management_backend\start.bat
```

### Manual start
```bash
# Terminal 1 — Backend
cd C:\crowd_management_backend\backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd C:\crowd_management_backend\frontend
php artisan serve --port=8080
```

### URLs
| Service | URL |
|---|---|
| Laravel Dashboard | http://127.0.0.1:8080 |
| FastAPI Backend | http://127.0.0.1:8000 |
| Swagger API Docs | http://127.0.0.1:8000/docs |

---

## AWS Deployment (Docker)

```bash
# EC2 lo run cheyyi
git clone <repo> crowd_management_backend
cd crowd_management_backend

docker-compose up -d
```

### AWS URLs (after deploy)
| Service | URL |
|---|---|
| Dashboard | http://your-ec2-ip |
| API | http://your-ec2-ip/api/v1 |
| Docs | http://your-ec2-ip/docs |
| WebSocket | ws://your-ec2-ip/ws/dashboard |

---

## API Endpoints

### Phase 3 — AI
- `GET /api/v1/ai/status`
- `POST /api/v1/ai/test`

### Phase 4 — Person Counter
- `POST /api/v1/person-counter/start/{camera_id}`
- `GET  /api/v1/person-counter/status/{camera_id}`

### Phase 5 — Queue Management
- `POST /api/v1/queue/start/{camera_id}`
- `GET  /api/v1/queue/status/{camera_id}`

### Phase 6 — Zone Monitoring
- `POST /api/v1/zone/start/{camera_id}`
- `GET  /api/v1/zone/status/{camera_id}`

### Phase 7 — Face Recognition
- `POST /api/v1/face/register`
- `GET  /api/v1/face/persons`
- `POST /api/v1/face/start/{camera_id}`
- `GET  /api/v1/face/status/{camera_id}`

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Engine | Python, FastAPI, YOLO11x, InsightFace |
| Database | PostgreSQL 15 |
| Cache/Events | Redis 7 |
| Frontend | Laravel 11 (PHP 8.2) |
| Proxy | Nginx |
| GPU | NVIDIA RTX 3050 / AWS T4 |
| Deployment | Docker, AWS EC2 |
