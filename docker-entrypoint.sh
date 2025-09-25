#!/bin/bash

set -euo pipefail

# Colors for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Wait for services to be ready
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=30
    local attempt=1

    log_info "Waiting for $service_name at $host:$port..."
    
    while ! nc -z "$host" "$port" 2>/dev/null; do
        if [ $attempt -eq $max_attempts ]; then
            log_error "$service_name is not available after $max_attempts attempts"
            exit 1
        fi
        log_debug "Attempt $attempt/$max_attempts: $service_name not ready, waiting 2s..."
        sleep 2
        ((attempt++))
    done
    
    log_info "$service_name is ready!"
}

# Initialize database if needed
init_database() {
    log_info "Initializing database..."
    if [ -f "/app/TradeBot/database/init_db.py" ]; then
        python3 /app/TradeBot/database/init_db.py || {
            log_warn "Database initialization returned non-zero exit code (might be already initialized)"
        }
    else
        log_warn "Database initialization script not found"
    fi
}

# Setup environment
setup_environment() {
    log_info "Setting up environment..."
    
    # Ensure log directories exist
    mkdir -p /app/logs /app/TradeBot/logs
    
    # Set Python path
    export PYTHONPATH="/app:${PYTHONPATH:-}"
    
    # Default environment variables
    export FLASK_ENV="${FLASK_ENV:-production}"
    export FLASK_DEBUG="${FLASK_DEBUG:-false}"
    export FLASK_HOST="${FLASK_HOST:-0.0.0.0}"
    export FLASK_PORT="${FLASK_PORT:-5000}"
    
    log_info "Environment setup complete"
}

# Health check function
health_check() {
    local url="${1:-http://localhost:5000/health}"
    log_info "Performing health check: $url"
    
    for i in {1..5}; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            log_info "Health check passed"
            return 0
        fi
        log_debug "Health check attempt $i failed, retrying in 2s..."
        sleep 2
    done
    
    log_warn "Health check failed after 5 attempts"
    return 1
}

# Service management functions
run_trading_api() {
    log_info "Starting Trading API Service..."
    
    # Wait for dependencies
    if [ "${POSTGRES_HOST:-}" ] && [ "${POSTGRES_PORT:-}" ]; then
        wait_for_service "${POSTGRES_HOST}" "${POSTGRES_PORT}" "PostgreSQL"
    fi
    
    if [ "${REDIS_HOST:-}" ] && [ "${REDIS_PORT:-}" ]; then
        wait_for_service "${REDIS_HOST}" "${REDIS_PORT}" "Redis"
    fi
    
    # Initialize database
    init_database
    
    # Start Flask API
    log_info "Starting Flask application..."
    cd /app
    exec python3 -m TradeBot.main
}

run_trading_orchestrator() {
    log_info "Starting Trading Orchestrator Service..."
    
    # Wait for trading API to be ready
    if [ "${BACKEND_BASE_URL:-}" ]; then
        local api_url="${BACKEND_BASE_URL}/health"
        log_info "Waiting for Trading API to be ready at $api_url..."
        
        for i in {1..30}; do
            if curl -f -s "$api_url" > /dev/null 2>&1; then
                log_info "Trading API is ready"
                break
            fi
            if [ $i -eq 30 ]; then
                log_error "Trading API not ready after 30 attempts"
                exit 1
            fi
            log_debug "Trading API not ready, attempt $i/30, waiting 5s..."
            sleep 5
        done
    fi
    
    # Wait for other dependencies
    if [ "${POSTGRES_HOST:-}" ] && [ "${POSTGRES_PORT:-}" ]; then
        wait_for_service "${POSTGRES_HOST}" "${POSTGRES_PORT}" "PostgreSQL"
    fi
    
    if [ "${REDIS_HOST:-}" ] && [ "${REDIS_PORT:-}" ]; then
        wait_for_service "${REDIS_HOST}" "${REDIS_PORT}" "Redis"
    fi
    
    # Start orchestrator
    log_info "Starting Trading Orchestrator..."
    cd /app
    exec python3 trading_orchestrator.py
}

run_llm_service() {
    log_info "Starting LLM Service..."
    cd /app
    exec python3 -m LLM.fast_main "$@"
}

run_mt5_service() {
    log_info "Starting MT5 Service..."
    cd /app
    exec python3 -m mt.main "$@"
}

run_telegram_bot() {
    log_info "Starting Telegram Bot Service..."
    cd /app
    exec python3 -m orchestrator.main "$@"
}

# Signal handlers for graceful shutdown
cleanup() {
    log_info "Received shutdown signal, cleaning up..."
    # Kill any background processes
    jobs -p | xargs -r kill
    log_info "Cleanup completed"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Main execution logic
main() {
    log_info "Docker Entrypoint Script Started"
    log_info "Command: $*"
    
    # Setup environment
    setup_environment
    
    # Parse command
    local command="${1:-trading-api}"
    shift 2>/dev/null || true
    
    case "$command" in
        "trading-api")
            run_trading_api "$@"
            ;;
        "trading-orchestrator")
            run_trading_orchestrator "$@"
            ;;
        "llm")
            run_llm_service "$@"
            ;;
        "mt5")
            run_mt5_service "$@"
            ;;
        "telegram")
            run_telegram_bot "$@"
            ;;
        "bash"|"sh")
            log_info "Starting shell session..."
            exec bash
            ;;
        "health")
            health_check "$@"
            ;;
        *)
            log_error "Unknown command: $command"
            log_info "Available commands:"
            log_info "  trading-api        - Start Flask API service (default)"
            log_info "  trading-orchestrator - Start main trading orchestrator"
            log_info "  llm               - Start LLM service"
            log_info "  mt5               - Start MT5 service" 
            log_info "  telegram          - Start Telegram bot"
            log_info "  health            - Run health check"
            log_info "  bash              - Start interactive shell"
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"
