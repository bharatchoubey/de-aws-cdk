#!/bin/bash

# Docker Management Scripts for CAS (Config as a Service)
# This script provides easy commands to manage the Docker environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to check if .env file exists
check_env() {
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from env.example..."
        cp env.example .env
        print_warning "Please edit .env file with your configuration before running the application."
        exit 1
    fi
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    mkdir -p logs
    mkdir -p ssl
    print_success "Directories created successfully"
}

# Function to start the application
start() {
    print_status "Starting CAS application with Docker Compose..."
    check_docker
    check_env
    create_directories
    
    docker-compose up -d
    print_success "CAS application started successfully!"
    print_status "Application is available at: http://localhost:5000"
    print_status "Health check: http://localhost:5000/health"
}

# Function to stop the application
stop() {
    print_status "Stopping CAS application..."
    docker-compose down
    print_success "CAS application stopped successfully!"
}

# Function to restart the application
restart() {
    print_status "Restarting CAS application..."
    stop
    start
}

# Function to show logs
logs() {
    print_status "Showing application logs..."
    docker-compose logs -f cas_app
}

# Function to show all logs
logs_all() {
    print_status "Showing all service logs..."
    docker-compose logs -f
}

# Function to build the application
build() {
    print_status "Building CAS application..."
    check_docker
    docker-compose build --no-cache
    print_success "CAS application built successfully!"
}

# Function to run database migrations
migrate() {
    print_status "Running database migrations..."
    docker-compose exec cas_app flask db upgrade
    print_success "Database migrations completed!"
}

# Function to create initial migration
init_migration() {
    print_status "Creating initial migration..."
    docker-compose exec cas_app flask db init
    docker-compose exec cas_app flask db migrate -m "Initial migration"
    print_success "Initial migration created!"
}

# Function to reset database
reset_db() {
    print_warning "This will delete all data in the database. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Resetting database..."
        docker-compose down -v
        docker-compose up -d postgres
        sleep 10
        docker-compose exec cas_app flask db upgrade
        print_success "Database reset completed!"
    else
        print_status "Database reset cancelled."
    fi
}

# Function to show status
status() {
    print_status "Checking service status..."
    docker-compose ps
}

# Function to clean up
cleanup() {
    print_status "Cleaning up Docker resources..."
    docker-compose down -v --remove-orphans
    docker system prune -f
    print_success "Cleanup completed!"
}

# Function to show help
show_help() {
    echo "CAS Docker Management Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start         Start the CAS application"
    echo "  stop          Stop the CAS application"
    echo "  restart       Restart the CAS application"
    echo "  build         Build the Docker images"
    echo "  logs          Show application logs"
    echo "  logs-all      Show all service logs"
    echo "  migrate       Run database migrations"
    echo "  init-migration Create initial migration"
    echo "  reset-db      Reset the database (WARNING: deletes all data)"
    echo "  status        Show service status"
    echo "  cleanup       Clean up Docker resources"
    echo "  help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start      # Start the application"
    echo "  $0 logs       # View application logs"
    echo "  $0 migrate    # Run database migrations"
}

# Main script logic
case "${1:-help}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    build)
        build
        ;;
    logs)
        logs
        ;;
    logs-all)
        logs_all
        ;;
    migrate)
        migrate
        ;;
    init-migration)
        init_migration
        ;;
    reset-db)
        reset_db
        ;;
    status)
        status
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
