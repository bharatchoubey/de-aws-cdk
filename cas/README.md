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

#### Option A: Docker Setup (Recommended)
- Docker 20.10+
- Docker Compose 2.0+
- Git

#### Option B: Local Development Setup
- Python 3.8+
- PostgreSQL 12+
- pip (Python package manager)

### 2. Installation

#### Option A: Docker Setup (Recommended)

1. **Clone and navigate to the project:**
   ```bash
   cd cas/
   ```

2. **Copy environment configuration:**
   ```bash
   cp env.example .env
   # Edit .env with your preferred settings
   ```

3. **Start the application:**
   ```bash
   # Using the management script (recommended)
   ./docker-manage.sh start
   
   # Or using docker-compose directly
   docker-compose up -d
   ```

4. **Initialize the database:**
   ```bash
   # Run database migrations
   ./docker-manage.sh migrate
   
   # Or manually
   docker-compose exec cas_app flask db upgrade
   ```

5. **Verify the installation:**
   ```bash
   # Check service status
   ./docker-manage.sh status
   
   # Test the health endpoint
   curl http://localhost:5000/health
   ```

The API will be available at:
- **Application**: `http://localhost:5000`
- **API Documentation**: `http://localhost:5000/api/`
- **Health Check**: `http://localhost:5000/health`
- **Database**: `localhost:5432` (PostgreSQL)
- **Redis**: `localhost:6379` (if enabled)
- **Nginx**: `http://localhost:80` (if enabled)

#### Option B: Local Development Setup

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

#### Docker (Recommended)
```bash
# Start all services
./docker-manage.sh start

# View logs
./docker-manage.sh logs

# Stop services
./docker-manage.sh stop

# Restart services
./docker-manage.sh restart
```

#### Local Development
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

## Docker Management

The project includes a comprehensive Docker setup with helper scripts for easy management.

### Docker Management Script

Use the `docker-manage.sh` script for common operations:

```bash
# Start the application
./docker-manage.sh start

# Stop the application
./docker-manage.sh stop

# Restart the application
./docker-manage.sh restart

# View application logs
./docker-manage.sh logs

# View all service logs
./docker-manage.sh logs-all

# Build Docker images
./docker-manage.sh build

# Run database migrations
./docker-manage.sh migrate

# Create initial migration
./docker-manage.sh init-migration

# Reset database (WARNING: deletes all data)
./docker-manage.sh reset-db

# Check service status
./docker-manage.sh status

# Clean up Docker resources
./docker-manage.sh cleanup

# Show help
./docker-manage.sh help
```

### Docker Services

The Docker Compose setup includes:

- **cas_app**: Flask application (port 5000)
- **postgres**: PostgreSQL database (port 5432)
- **redis**: Redis cache (port 6379) - optional
- **nginx**: Reverse proxy (port 80) - optional

### Environment Configuration

Copy `env.example` to `.env` and configure:

```bash
cp env.example .env
# Edit .env with your settings
```

Key environment variables:
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `SECRET_KEY`: Flask secret key
- `JWT_SECRET_KEY`: JWT signing key

### Docker Volumes

- `postgres_data`: Persistent PostgreSQL data
- `redis_data`: Persistent Redis data
- `./logs`: Application logs directory

## Development

### Running Tests

#### Docker
```bash
docker-compose exec cas_app python -m pytest tests/
```

#### Local
```bash
export FLASK_ENV=testing
python -m pytest tests/
```

### Database Migrations

#### Docker
```bash
# Create migration
docker-compose exec cas_app flask db migrate -m "Description of changes"

# Apply migration
docker-compose exec cas_app flask db upgrade

# Rollback migration
docker-compose exec cas_app flask db downgrade
```

#### Local
```bash
# Create migration
flask db migrate -m "Description of changes"

# Apply migration
flask db upgrade

# Rollback migration
flask db downgrade
```

## Production Deployment

### Docker Production Deployment

1. **Configure production environment:**
   ```bash
   # Set production environment variables
   export FLASK_ENV=production
   export SECRET_KEY=your-strong-secret-key
   export JWT_SECRET_KEY=your-strong-jwt-secret
   export POSTGRES_PASSWORD=your-strong-db-password
   ```

2. **Build and deploy:**
   ```bash
   # Build production images
   ./docker-manage.sh build
   
   # Start production services
   ./docker-manage.sh start
   
   # Run migrations
   ./docker-manage.sh migrate
   ```

3. **Configure reverse proxy (Nginx):**
   - Update `nginx.conf` with your domain
   - Configure SSL certificates in `ssl/` directory
   - Enable HTTPS in docker-compose.yml

4. **Monitor and maintain:**
   ```bash
   # Check service health
   ./docker-manage.sh status
   
   # View logs
   ./docker-manage.sh logs
   
   # Update application
   ./docker-manage.sh build
   ./docker-manage.sh restart
   ```

### Traditional Production Deployment

1. Set `FLASK_ENV=production` in your environment
2. Use a strong `JWT_SECRET_KEY` and `SECRET_KEY`
3. Configure proper database connection pooling
4. Use a production WSGI server like Gunicorn
5. Set up proper logging and monitoring
6. Use HTTPS in production

## License

This project is part of the de-cloud-sceptre infrastructure management system.
