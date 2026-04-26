# 💬 Messenger Backend

Production-ready FastAPI backend for a messenger application with WebSocket support, JWT authentication, OTP verification, and an admin panel.

## 🚀 Quick Start

### Docker (Recommended)

```bash
# Copy environment config
cp .env.example .env

# Start all services (PostgreSQL + Redis + App)
docker-compose up -d

# View logs
docker-compose logs -f app
```

App will be available at:
- **API:** http://localhost:8000
- **Swagger Docs:** http://localhost:8000/docs
- **Admin Panel:** http://localhost:8000/admin/login (admin / admin123)

---

### Local Development

**Requirements:** Python 3.11+, PostgreSQL, Redis

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your database credentials

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

---

## 🏗️ Project Structure

```
messenger-backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings & environment variables
│   ├── database.py          # Async SQLAlchemy setup
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── routers/             # API endpoint handlers
│   ├── services/            # Business logic layer
│   ├── admin/               # Admin panel (Jinja2)
│   ├── core/                # Auth, WebSocket manager, dependencies
│   └── utils/               # Helper functions
├── alembic/                 # Database migrations
├── uploads/                 # Local media storage
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 📡 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/send-otp` | Send OTP to phone |
| POST | `/api/auth/verify-otp` | Verify OTP, get JWT tokens |
| POST | `/api/auth/refresh-token` | Refresh access token |
| POST | `/api/auth/logout` | Revoke refresh token |

### Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/profile/setup` | Initial profile setup |
| GET | `/api/profile/me` | Get own profile |
| PUT | `/api/profile/me` | Update profile |
| POST | `/api/profile/avatar` | Upload avatar |
| GET | `/api/profile/{user_id}` | Get public profile |

### Contacts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/contacts` | List contacts |
| POST | `/api/contacts/sync` | Sync phone contacts |
| GET | `/api/contacts/search?q=` | Search users |

### Chats & Messages
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chats` | List all chats |
| POST | `/api/chats` | Create chat |
| GET | `/api/chats/{id}` | Chat details |
| DELETE | `/api/chats/{id}` | Delete chat |
| GET | `/api/chats/{id}/messages` | Get messages (cursor pagination) |
| POST | `/api/chats/{id}/messages` | Send message |
| DELETE | `/api/chats/{id}/messages/{msg_id}` | Delete message |
| POST | `/api/chats/{id}/messages/read` | Mark as read |

### Media
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/media/upload` | Upload file |
| GET | `/api/media/{filename}` | Download file |

### Calls
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/calls/initiate` | Start a call |
| POST | `/api/calls/{id}/accept` | Accept call |
| POST | `/api/calls/{id}/reject` | Reject call |
| POST | `/api/calls/{id}/end` | End call |
| GET | `/api/calls/history` | Call history |

### Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/PUT | `/api/settings/notifications` | Notification settings |
| GET/PUT | `/api/settings/privacy` | Privacy settings |
| POST | `/api/settings/devices/register` | Register FCM device |

---

## 🔌 WebSocket

Connect to real-time events:

```javascript
const ws = new WebSocket(`ws://localhost:8000/api/ws?token=YOUR_ACCESS_TOKEN`);

ws.onmessage = (event) => {
    const { event: type, data } = JSON.parse(event.data);
    // Events: message.new, message.read, user.typing, user.online, call.incoming
};

// Send typing indicator
ws.send(JSON.stringify({
    event: "user.typing",
    data: { chat_id: "chat-uuid", is_typing: true }
}));
```

---

## 🔧 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | PostgreSQL async URL |
| `SECRET_KEY` | - | JWT signing key (min 32 chars) |
| `OTP_DEV_MODE` | `true` | Show OTP in response (dev only) |
| `TWILIO_*` | - | Twilio SMS credentials (production) |
| `MEDIA_STORAGE` | `local` | `local` or `s3` |
| `ADMIN_USERNAME` | `admin` | Admin panel username |
| `ADMIN_PASSWORD` | `admin123` | Admin panel password |

---

## 🗃️ Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

---

## 🛡️ Security Notes

1. Change `SECRET_KEY` to a strong random value in production
2. Set `OTP_DEV_MODE=false` in production
3. Configure real Twilio credentials for SMS
4. Change `ADMIN_USERNAME` and `ADMIN_PASSWORD`
5. Set `DEBUG=false` in production
6. Configure proper CORS origins

---

## 📊 Admin Panel

Navigate to `/admin/login` and sign in with admin credentials.

Features:
- **Dashboard:** User count, message stats, active chats
- **Users:** List, search, block/unblock users
- **Chats:** View all chats with member and message counts
