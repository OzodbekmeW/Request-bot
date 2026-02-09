# Xavfsiz Backend Tizimi

Production-ready, xavfsiz va scalable backend tizim (Admin + User Management)

## 📋 Tech Stack

- **Backend Framework:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL + SQLAlchemy 2.0 (async)
- **Migration:** Alembic
- **Cache:** Redis (async)
- **Security:** python-jose (JWT), passlib (bcrypt)
- **Validation:** Pydantic V2
- **Documentation:** FastAPI auto Swagger/ReDoc
- **Bot:** python-telegram-bot
- **ASGI Server:** Uvicorn

## 🔐 Security Features

- ✅ **HttpOnly Cookies** - Admin session (XSS protection)
- ✅ **CSRF Protection** - Double Submit Cookie pattern
- ✅ **Rate Limiting** - Redis-based (OTP, Login attempts)
- ✅ **JWT with Token Rotation** - Access + Refresh tokens
- ✅ **bcrypt Password Hashing** - Secure password storage
- ✅ **SQL Injection Protection** - SQLAlchemy parameterized queries
- ✅ **Security Headers** - XSS, Content-Type, Frame options
- ✅ **RBAC** - Role-based Access Control with permissions

## 🚀 Quick Start

### 1. Clone & Setup Environment

```bash
# Clone repository
cd backend

# Create virtual environment
python -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 3. Setup Database

```bash
# Create PostgreSQL database
createdb secure_backend

# Run migrations
alembic upgrade head

# Seed initial data (super admin + permissions)
python -m app.seeds.initial_data
```

### 4. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:alpine

# Or install locally
redis-server
```

### 5. Run Application

```bash
# Development
python run.py

# Or with uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Run Telegram Bot (Separate terminal)

```bash
python -m bot.main
```

## 📚 API Documentation

- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc
- **OpenAPI JSON:** http://localhost:8000/api/openapi.json

## 🔑 Default Super Admin

After running seed:

- **Username:** `superadmin`
- **Email:** `admin@example.com`
- **Password:** `SuperAdmin123!`

⚠️ **Change password in production!**

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── admin_auth.py      # Admin login/logout
│   │       │   ├── admin_management.py # Admin CRUD
│   │       │   ├── user_auth.py       # User OTP auth
│   │       │   └── user_management.py # User CRUD
│   │       └── router.py
│   ├── core/
│   │   ├── config.py        # Settings
│   │   ├── database.py      # SQLAlchemy async
│   │   ├── redis.py         # Redis client
│   │   └── security.py      # Password, JWT, tokens
│   ├── dependencies/
│   │   └── auth.py          # Guards (auth, csrf, permissions)
│   ├── middleware/
│   │   └── security.py      # Security headers
│   ├── models/
│   │   ├── admin.py
│   │   ├── admin_session.py
│   │   ├── otp_code.py
│   │   ├── permission.py
│   │   ├── refresh_token.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── admin.py
│   │   ├── auth.py
│   │   └── user.py
│   ├── seeds/
│   │   └── initial_data.py  # Super admin + permissions
│   ├── services/
│   │   ├── admin_auth_service.py
│   │   ├── admin_service.py
│   │   ├── otp_service.py
│   │   ├── telegram_service.py
│   │   ├── user_auth_service.py
│   │   └── user_service.py
│   └── main.py              # FastAPI app
├── alembic/
│   ├── versions/            # Migration files
│   └── env.py
├── bot/
│   └── main.py              # Telegram bot
├── tests/
├── .env.example
├── alembic.ini
├── requirements.txt
├── run.py
└── README.md
```

## 🔒 API Endpoints

### User Authentication (JWT)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/send-otp` | POST | Send OTP via Telegram |
| `/api/auth/verify-otp` | POST | Verify OTP, get tokens |
| `/api/auth/refresh` | POST | Refresh access token |

### Admin Authentication (Cookie + CSRF)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/auth/login` | POST | Admin login |
| `/api/admin/auth/logout` | POST | Admin logout |
| `/api/admin/auth/me` | GET | Get current admin |

### Admin Management

| Endpoint | Method | Permission |
|----------|--------|------------|
| `/api/admin/admins` | GET | `can_view_admins` |
| `/api/admin/admins/{id}` | GET | `can_view_admins` |
| `/api/admin/admins` | POST | `can_create_admin` |
| `/api/admin/admins/{id}` | PATCH | `can_edit_admin` |
| `/api/admin/admins/{id}` | DELETE | `can_delete_admin` |
| `/api/admin/admins/{id}/permissions` | PUT | `can_manage_permissions` |

### User Management

| Endpoint | Method | Permission |
|----------|--------|------------|
| `/api/admin/users` | GET | `can_view_users` |
| `/api/admin/users/{id}` | GET | `can_view_users` |
| `/api/admin/users/{id}` | PATCH | `can_edit_user` |
| `/api/admin/users/{id}/deactivate` | POST | `can_deactivate_user` |
| `/api/admin/users/{id}/activate` | POST | `can_deactivate_user` |
| `/api/admin/users/{id}` | DELETE | `can_delete_user` |

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/ -v
```

## 🐳 Docker (Optional)

```bash
# Build
docker-compose build

# Run
docker-compose up -d
```

## 📝 Rate Limiting

### OTP Limits
- 1 request per minute (per phone)
- 3 requests per hour (per phone)
- 10 requests per day (per IP)

### Login Limits
- 5 failed attempts → 15 minutes block

## 🔧 Environment Variables

See `.env.example` for all configuration options:

- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `JWT_ACCESS_SECRET` - JWT signing key
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `FRONTEND_URL` - CORS allowed origin

## 📜 License

MIT License

## 👨‍💻 Author

Backend Developer

---

**⚠️ Production Checklist:**

- [ ] Change all secret keys
- [ ] Enable HTTPS
- [ ] Set `DEBUG=False`
- [ ] Configure proper CORS origins
- [ ] Setup monitoring (Prometheus, Grafana)
- [ ] Configure logging (to file/service)
- [ ] Setup database backups
- [ ] Rate limiting production values
