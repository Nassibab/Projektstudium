#!/usr/bin/env bash
set -euo pipefail

echo "Checking Docker availability..."
if ! docker info > /dev/null 2>&1; then
  echo "Docker is not running or not available. Please start Docker Desktop / Docker Engine and try again."
  exit 1
fi

echo "Building API, Frontend, and starting containers..."
docker compose build --no-cache

echo "Starting everything..."
docker compose up -d

echo "Waiting for services..."

# Function to wait for a service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    echo "Waiting for $service_name at $url..."
    while ! curl -s --max-time 5 "$url" > /dev/null; do
        echo "$service_name not ready, waiting..."
        sleep 2
    done
    echo "$service_name is ready!"
}

# Wait for API
wait_for_service "http://localhost:8000" "API"

# Wait for Frontend
wait_for_service "http://localhost:3000" "Frontend"

echo "Status:"
docker compose ps

echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 API:      http://localhost:8000"
echo "📊 Logs:     docker compose logs -f"

#!/usr/bin/env bash
set -euo pipefail

echo "Checking Docker availability..."
if ! docker info > /dev/null 2>&1; then
  echo "Docker is not running or not available. Please start Docker Desktop / Docker Engine and try again."
  exit 1
fi

echo "Building API, Frontend, and starting containers..."
docker compose build --no-cache

echo "Starting everything..."
docker compose up -d

echo "Waiting for services..."

# Function to wait for a service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    echo "Waiting for $service_name at $url..."
    while ! curl -s --max-time 5 "$url" > /dev/null; do
        echo "$service_name not ready, waiting..."
        sleep 2
    done
    echo "$service_name is ready!"
}

# Wait for API
wait_for_service "http://localhost:8000" "API"

# Wait for Frontend
wait_for_service "http://localhost:3000" "Frontend"

echo "Status:"
docker compose ps

echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 API:      http://localhost:8000"
echo "📊 Logs:     docker compose logs -f"
