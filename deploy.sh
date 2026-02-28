#!/bin/bash
# =============================================================================
# WebCrawler Pro — VPS Deployment Script
# Usage: bash deploy.sh
# Tested on: Ubuntu 22.04 LTS, Debian 12
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1" >&2; }
info() { echo -e "${BLUE}[i]${NC} $1"; }

echo -e "${CYAN}"
cat << 'BANNER'
 ___       __     __    ________  ________  ________  ___       _______   ________     
|\  \     |\  \  |\  \ |\   ____\|\   __  \|\   __  \|\  \     |\  ___ \ |\   __  \    
\ \  \    \ \  \ \ \  \\ \  \___|\ \  \|\  \ \  \|\  \ \  \    \ \   __/|\ \  \|\  \   
 \ \  \  __\ \  \ \ \  \\ \  \    \ \   _  _\ \   __  \ \  \    \ \  \_|/_\ \   _  _\  
  \ \  \|\__\_\  \ \ \__\\ \  \____\ \  \\  \\ \  \ \  \ \  \____\ \  \_|\ \ \  \\  \| 
   \ \____________\ \|__| \ \_______\ \__\\ _\\ \__\ \__\ \_______\ \_______\ \__\\ _\ 
    \|____________|        \|_______|\|__|\|__|\|__|\|__|\|_______|\|_______|\|__|\|__|
BANNER
echo -e "${NC}"
echo -e "${CYAN}WebCrawler Pro — VPS Deployment Script v0.2.0${NC}"
echo -e "${CYAN}=============================================${NC}\n"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# =============================================================================
# Step 1: Check / Install Docker
# =============================================================================
info "Step 1: Checking Docker installation..."

if ! command -v docker &> /dev/null; then
    warn "Docker not found. Installing Docker..."
    if [[ -f /etc/debian_version ]] || [[ -f /etc/ubuntu-release ]]; then
        apt-get update -qq
        apt-get install -y -qq ca-certificates curl gnupg lsb-release
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg \
            -o /etc/apt/keyrings/docker.asc
        chmod a+r /etc/apt/keyrings/docker.asc
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") \
$(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
            tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt-get update -qq
        apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        systemctl enable docker
        systemctl start docker
        log "Docker installed successfully"
    else
        err "Unsupported OS. Please install Docker manually: https://docs.docker.com/engine/install/"
        exit 1
    fi
else
    DOCKER_VER=$(docker --version | awk '{print $3}' | tr -d ',')
    log "Docker already installed: v${DOCKER_VER}"
fi

# Check docker compose plugin
if ! docker compose version &> /dev/null 2>&1; then
    err "Docker Compose plugin not found. Please install docker-compose-plugin."
    exit 1
fi
log "Docker Compose: $(docker compose version --short)"

# =============================================================================
# Step 2: Setup .env file
# =============================================================================
info "Step 2: Checking environment configuration..."

if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
        cp .env.example .env
        warn ".env created from .env.example"
        warn "IMPORTANT: Edit .env with your actual values before proceeding!"
        echo ""
        echo -e "${RED}Please edit the following variables in .env:${NC}"
        echo -e "  ${YELLOW}DOMAIN${NC}              = your domain (e.g. mycrawler.com)"
        echo -e "  ${YELLOW}ACME_EMAIL${NC}          = your email for Let's Encrypt"
        echo -e "  ${YELLOW}POSTGRES_PASSWORD${NC}   = strong database password"
        echo -e "  ${YELLOW}SECRET_KEY${NC}          = random secret (run: openssl rand -hex 32)"
        echo -e "  ${YELLOW}MINIO_ROOT_PASSWORD${NC} = strong MinIO password"
        echo ""
        read -rp "Have you edited .env with your values? [y/N] " confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            warn "Deployment aborted. Edit .env and re-run ./deploy.sh"
            exit 0
        fi
    else
        err ".env.example not found. Cannot create .env"
        exit 1
    fi
else
    log ".env already exists"
fi

# Validate critical env vars
source .env 2>/dev/null || true
CRITICAL_VARS=("DOMAIN" "ACME_EMAIL" "POSTGRES_PASSWORD" "SECRET_KEY")
MISSING=0
for var in "${CRITICAL_VARS[@]}"; do
    val="${!var:-}"
    if [[ -z "$val" || "$val" == *"example"* || "$val" == *"changeme"* || "$val" == *"your-"* ]]; then
        err "${var} is not set or still has default value"
        MISSING=1
    fi
done
if [[ $MISSING -eq 1 ]]; then
    err "Please update the critical variables in .env and re-run deploy.sh"
    exit 1
fi
log "Environment configuration validated"

# =============================================================================
# Step 3: Fix acme.json permissions
# =============================================================================
info "Step 3: Setting up Traefik SSL certificate storage..."

mkdir -p traefik
if [[ ! -f traefik/acme.json ]]; then
    touch traefik/acme.json
fi
chmod 600 traefik/acme.json
log "traefik/acme.json permissions set to 600"

# =============================================================================
# Step 4: Pull latest Docker images
# =============================================================================
info "Step 4: Pulling Docker images from ghcr.io..."

GHCR_IMAGES=(
    "ghcr.io/crawlitron/webcrawler-pro/backend:latest"
    "ghcr.io/crawlitron/webcrawler-pro/frontend:latest"
)

for img in "${GHCR_IMAGES[@]}"; do
    info "Pulling $img ..."
    docker pull "$img" || warn "Could not pull $img (will try to use local cache)"
done

docker pull traefik:v3.0
docker pull postgres:16-alpine
docker pull redis:7-alpine
docker pull minio/minio:latest
docker pull portainer/portainer-ce:latest
docker pull containrrr/watchtower:latest
log "All images pulled"

# =============================================================================
# Step 5: Start services
# =============================================================================
info "Step 5: Starting WebCrawler Pro services..."

docker compose -f docker-compose.vps.yml up -d --remove-orphans

# Wait for backend health
info "Waiting for backend to become healthy (up to 90s)..."
for i in $(seq 1 30); do
    if docker exec webcrawler-backend curl -sf http://localhost:8000/health &>/dev/null; then
        log "Backend is healthy"
        break
    fi
    sleep 3
    if [[ $i -eq 30 ]]; then
        warn "Backend health check timed out. Check logs: docker logs webcrawler-backend"
    fi
done

# =============================================================================
# Step 6: Summary
# =============================================================================
echo ""
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}  WebCrawler Pro deployed successfully! 🚀  ${NC}"
echo -e "${GREEN}=============================================${NC}"
echo ""
echo -e "${CYAN}URLs:${NC}"
echo -e "  🌐 App:       ${YELLOW}https://${DOMAIN:-your-domain.com}${NC}"
echo -e "  📡 API:       ${YELLOW}https://${DOMAIN:-your-domain.com}/api${NC}"
echo -e "  📚 API Docs:  ${YELLOW}https://${DOMAIN:-your-domain.com}/docs${NC}"
echo -e "  🐳 Portainer: ${YELLOW}https://portainer.${DOMAIN:-your-domain.com}${NC}"
echo -e "  🪣 MinIO:     ${YELLOW}https://minio.${DOMAIN:-your-domain.com}${NC}"
echo -e "  🔒 Traefik:   ${YELLOW}https://traefik.${DOMAIN:-your-domain.com}${NC}"
echo ""
echo -e "${CYAN}Useful commands:${NC}"
echo -e "  docker compose -f docker-compose.vps.yml ps"
echo -e "  docker compose -f docker-compose.vps.yml logs -f backend"
echo -e "  docker compose -f docker-compose.vps.yml down"
echo ""
echo -e "${CYAN}Service status:${NC}"
docker compose -f docker-compose.vps.yml ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}'
