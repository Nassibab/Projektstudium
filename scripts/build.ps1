# PowerShell script to build and start Docker services on Windows
# Equivalent to build.sh

# Check and generate package-lock.json if missing
if (!(Test-Path "services/frontend/package-lock.json")) {
    Write-Host "Generating package-lock.json for frontend (this may take a few minutes)..."
    try {
        Push-Location services/frontend
        npm install
        Pop-Location
        Write-Host "package-lock.json generated."
    } catch {
        Write-Host "Failed to generate package-lock.json. Please run 'npm install' manually in services/frontend if needed."
    }
}

Write-Host "Building API, Frontend, and starting containers..."
docker compose build

Write-Host "Starting everything..."
docker compose up -d

Write-Host "Waiting for services..."

# Function to wait for a service to be ready
function Wait-ForService {
    param($url, $serviceName)
    Write-Host "Waiting for $serviceName at $url..."
    while ($true) {
        try {
            $response = Invoke-WebRequest -Uri $url -TimeoutSec 5 -ErrorAction Stop
            break
        } catch {
            Write-Host "$serviceName not ready, waiting..."
            Start-Sleep -Seconds 2
        }
    }
    Write-Host "$serviceName is ready!"
}

# Wait for API
Wait-ForService "http://localhost:8000" "API"

# Wait for Frontend
Wait-ForService "http://localhost:3000" "Frontend"

Write-Host "Status:"
docker compose ps

Write-Host ""
Write-Host "🌐 Frontend: http://localhost:3000"
Write-Host "🔧 API:      http://localhost:8000"
Write-Host "📊 Logs:     docker compose logs -f"