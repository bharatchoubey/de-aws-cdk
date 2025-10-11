# Config as a Service (CAS) REST API

A Flask-based REST API service for managing application and infrastructure configurations with PostgreSQL storage, JWT authentication, and CRUD operations.

## Features

- **JWT Authentication** with 12-hour token validity
- **User Management** (register, login, refresh tokens)
- **Configuration Management** for both application and infrastructure configs
- **Environment Support** (dev/staging/prod)
- **PostgreSQL Backend** with SQLAlchemy ORM
- **RESTful API** with proper HTTP status codes
- **Input Validation** and error handling

## Project Structure

```
cas/
├── src/
│   ├── __init__.py
│   ├── app.py                 # Flask application factory
│   ├── config.py              # App configuration
│   ├── database.py            # Database setup
│   ├── models/
│   │   ├── user.py           # User model
│   │   └── configuration.py   # Configuration model
│   ├── routes/
│   │   ├── auth.py           # Authentication endpoints
│   │   └── configs.py        # Configuration CRUD endpoints
│   └── middleware/
│       └── auth.py           # JWT middleware
├── requirements.txt
├── .env.example
└── README.md
```

## Setup Instructions

### 1. Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip (Python package manager)

### 2. Installation

1. **Clone and navigate to the project:**
   ```bash
   cd cas/
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and JWT secret
   ```

5. **Setup PostgreSQL database:**
   ```sql
   CREATE DATABASE cas_db;
   CREATE USER cas_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE cas_db TO cas_user;
   ```

6. **Initialize database:**
   ```bash
   export FLASK_APP=src.app:create_app
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

### 3. Running the Application

```bash
export FLASK_APP=src.app:create_app
export FLASK_ENV=development
flask run
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `POST /api/auth/refresh` - Refresh JWT token
- `GET /api/auth/me` - Get current user info

### Configuration Management

All configuration endpoints require JWT authentication via `Authorization: Bearer <token>` header.

- `POST /api/configs` - Create new configuration
- `GET /api/configs` - List configurations (with filters)
- `GET /api/configs/<id>` - Get specific configuration
- `PUT /api/configs/<id>` - Update configuration
- `DELETE /api/configs/<id>` - Delete configuration

### Health Check

- `GET /health` - Service health status

## API Usage Examples

### 1. Register a User

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepassword123"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "securepassword123"
  }'
```

### 3. Create Configuration

```bash
curl -X POST http://localhost:5000/api/configs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "app_name": "my-service",
    "config_type": "application",
    "environment": "dev",
    "key": "database_url",
    "value": "postgresql://localhost:5432/myapp_dev",
    "description": "Development database connection"
  }'
```

### 4. List Configurations

```bash
curl -X GET "http://localhost:5000/api/configs?app_name=my-service&environment=dev" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Configuration Types

- **application**: Application-specific configurations
- **infrastructure**: Infrastructure and deployment configurations

## Environments

- **dev/development**: Development environment
- **staging**: Staging environment  
- **prod/production**: Production environment

## Database Schema

### Users Table
- `id` (Primary Key)
- `username` (Unique)
- `email` (Unique)
- `password_hash`
- `created_at`, `updated_at`

### Configurations Table
- `id` (Primary Key)
- `app_name` (Application name)
- `config_type` (application/infrastructure)
- `environment` (dev/staging/prod)
- `key` (Configuration key)
- `value` (Configuration value)
- `description` (Optional description)
- `created_by_id` (Foreign Key to Users)
- `created_at`, `updated_at`

## Security Features

- JWT tokens with 12-hour expiration
- Password hashing with Werkzeug
- Input validation and sanitization
- SQL injection protection via SQLAlchemy ORM
- CORS support for cross-origin requests

## Development

### Running Tests

```bash
export FLASK_ENV=testing
python -m pytest tests/
```

### Database Migrations

```bash
# Create migration
flask db migrate -m "Description of changes"

# Apply migration
flask db upgrade

# Rollback migration
flask db downgrade
```

## Production Deployment

1. Set `FLASK_ENV=production` in your environment
2. Use a strong `JWT_SECRET_KEY` and `SECRET_KEY`
3. Configure proper database connection pooling
4. Use a production WSGI server like Gunicorn
5. Set up proper logging and monitoring
6. Use HTTPS in production

## License

This project is part of the de-cloud-sceptre infrastructure management system.
