# VPS Deployment Guide - WebCrawler Pro

> Deploy WebCrawler Pro on any Ubuntu/Debian VPS with automatic SSL via Traefik.

---

## 1. VPS Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| SSD | 20 GB | 50 GB |
| Open Ports | 80, 443 | 80, 443, 22 |

> **ARM64 note:** Images support both `linux/amd64` and `linux/arm64` (Hetzner CAX, AWS Graviton).

---

## 2. Domain DNS Setup

Add these DNS A records pointing to your VPS IP:

```
A    example.com           -> <YOUR_VPS_IP>
A    www.example.com       -> <YOUR_VPS_IP>
A    portainer.example.com -> <YOUR_VPS_IP>
A    minio.example.com     -> <YOUR_VPS_IP>
```

Verify propagation: `dig +short example.com`

---

## 3. Deployment in 5 Steps

### Step 1 - Clone the repository

```bash
ssh root@<YOUR_VPS_IP>
git clone https://github.com/crawlitron/webcrawler-pro.git
cd webcrawler-pro
```

### Step 2 - Configure environment

```bash
cp .env.example .env
nano .env
```

Edit these **required** values:

```env
DOMAIN=example.com
ACME_EMAIL=admin@example.com
POSTGRES_PASSWORD=<strong-random-password>
SECRET_KEY=<64-char-random-string>
MINIO_ROOT_PASSWORD=<strong-random-password>
PORTAINER_ADMIN_PASSWORD=<strong-random-password>
```

Generate a strong secret key: `openssl rand -hex 32`

### Step 3 - Set certificate file permissions

```bash
chmod 600 traefik/acme.json
```

### Step 4 - Run the deployment script

```bash
chmod +x deploy.sh
./deploy.sh
```

The script will:
- Install Docker + Docker Compose if not present
- Pull all images from `ghcr.io/crawlitron/webcrawler-pro/`
- Start all services via `docker-compose.vps.yml`
- Display service URLs and health status

### Step 5 - Verify deployment

```bash
docker compose -f docker-compose.vps.yml ps
```

All services should show `Up (healthy)`.

---

## 4. SSL Certificate Status

Traefik automatically requests Let's Encrypt certificates on first HTTPS request.

**Check certificate storage:**
```bash
cat traefik/acme.json | python3 -m json.tool | grep -A5 'Certificates'
```

**Force certificate renewal:**
```bash
rm traefik/acme.json && touch traefik/acme.json && chmod 600 traefik/acme.json
docker compose -f docker-compose.vps.yml restart traefik
```

---

## 5. Logs & Monitoring

```bash
# All services
docker compose -f docker-compose.vps.yml logs -f

# Specific service
docker compose -f docker-compose.vps.yml logs -f backend
docker compose -f docker-compose.vps.yml logs -f worker
docker compose -f docker-compose.vps.yml logs -f traefik

# Health check
curl -f https://example.com/health
curl -f https://example.com/api/health

# Resource usage
docker stats
```

**Portainer Web UI:** `https://portainer.example.com`

---

## 6. Backup & Restore

### Backup PostgreSQL
```bash
docker compose -f docker-compose.vps.yml exec postgres \
  pg_dump -U webcrawler webcrawler > backup-$(date +%Y%m%d-%H%M%S).sql
```

### Restore PostgreSQL
```bash
docker compose -f docker-compose.vps.yml exec -T postgres \
  psql -U webcrawler webcrawler < backup-20260101-120000.sql
```

### Backup MinIO
```bash
docker run --rm \
  -v webcrawler-pro_minio_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/minio-$(date +%Y%m%d).tar.gz /data
```

### Automated daily backups (cron)
```bash
# Run: crontab -e
0 3 * * * cd /root/webcrawler-pro && docker compose -f docker-compose.vps.yml exec -T postgres pg_dump -U webcrawler webcrawler > /root/backups/wcp-$(date +%%Y%%m%%d).sql 2>&1
```

---

## 7. Update to New Version

### Automatic updates (Watchtower)

Watchtower checks for new images daily (`WATCHTOWER_POLL_INTERVAL=86400`) and restarts containers automatically.

### Manual update
```bash
cd /root/webcrawler-pro
git pull origin main
docker compose -f docker-compose.vps.yml pull
docker compose -f docker-compose.vps.yml up -d --remove-orphans
docker compose -f docker-compose.vps.yml ps
```

### Rollback to a specific version
```bash
# Edit docker-compose.vps.yml image tags to e.g. :v0.1.0
docker compose -f docker-compose.vps.yml up -d backend frontend
```

---

## 8. Firewall Configuration

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
ufw status verbose
```

---

## 9. Troubleshooting

| Problem | Solution |
|---------|----------|
| SSL cert not issued | Check DNS propagation, ensure port 80 is open |
| Services not starting | `docker compose -f docker-compose.vps.yml logs` |
| DB connection error | Check `POSTGRES_PASSWORD` in `.env` |
| Out of disk space | `docker system prune -af --volumes` |
| 502 Bad Gateway | Check backend/frontend container health |
| acme.json permission error | `chmod 600 traefik/acme.json` |

---

## Service URLs Reference

| Service | URL |
|---------|-----|
| Frontend | `https://example.com` |
| API | `https://example.com/api` |
| API Docs | `https://example.com/api/docs` |
| Portainer | `https://portainer.example.com` |
| MinIO Console | `https://minio.example.com` |
