<div align="center">

# 🕷️ WebCrawler Pro

**Professional SEO Crawler & Website Auditing Platform**

*A powerful, self-hosted alternative to Screaming Frog — built for teams*

[![CI/CD Pipeline](https://github.com/crawlitron/webcrawler-pro/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/crawlitron/webcrawler-pro/actions/workflows/docker-publish.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-ghcr.io-blue?logo=docker)](https://github.com/crawlitron/webcrawler-pro/pkgs/container/webcrawler-pro)
[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)](https://fastapi.tiangolo.com/)

</div>

---

## 📸 Screenshots

> *Screenshots coming soon*

| Dashboard | Crawl View | SEO Issues |
|-----------|------------|------------|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Crawl](docs/screenshots/crawl.png) | ![Issues](docs/screenshots/issues.png) |

---

## ✨ Features

### 🔍 Crawling Engine
- **Multi-threaded Scrapy crawler** with configurable depth and concurrency
- **JavaScript rendering** via Playwright for SPA/dynamic content
- **Real-time progress** tracking with WebSocket updates
- **Scheduled crawls** with Celery Beat automation

### 📊 SEO Analysis
- **Meta tags**: Title, Description length validation and duplicate detection
- **Heading structure**: H1–H6 analysis, missing/duplicate H1 detection
- **Status codes**: 2xx, 3xx redirect chains, 4xx/5xx error tracking
- **Broken links**: Internal and external link validation
- **Image audit**: Missing alt-tags, oversized images
- **Issue severity**: Critical 🔴, Warning 🟡, Info 🔵

### 🏢 Team Collaboration
- **Project management**: Multiple projects with team access
- **Shareable reports**: Export as CSV, Excel, JSON, PDF
- **Crawl history**: Track SEO improvements over time
- **REST API**: Full programmatic access

### 🚀 Deployment
- **Self-hosted**: Full Docker Compose setup in minutes
- **SaaS-ready**: Scalable architecture for multi-tenant deployment
- **GitHub Actions CI/CD**: Automated build and push to ghcr.io

---

## ⚡ Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/crawlitron/webcrawler-pro.git && cd webcrawler-pro

# 2. Configure environment
cp .env.example .env   # Then edit .env with your values

# 3. Build and launch
make build
```

🎉 **Done!** Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📋 Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Docker | 24.0+ | [Install](https://docs.docker.com/get-docker/) |
| Docker Compose | 2.20+ | Included with Docker Desktop |
| Git | 2.x | For cloning |
| RAM | 2GB+ | 4GB recommended |

---

## 🛠️ Installation & Setup

### 1. Clone & Configure

```bash
git clone https://github.com/crawlitron/webcrawler-pro.git
cd webcrawler-pro
cp .env.example .env
```

Edit `.env` and update these critical values:

```env
POSTGRES_PASSWORD=your-secure-password-here
SECRET_KEY=your-random-secret-key-here
FRONTEND_URL=http://your-domain.com
NEXT_PUBLIC_API_URL=http://your-domain.com
```

### 2. Start Services

```bash
# Development (with hot-reload)
make build

# Production (pre-built images from ghcr.io)
docker compose -f docker-compose.prod.yml up -d
```

### 3. Run Database Migrations

```bash
make migrate
```

### 4. Verify Services

```bash
make ps
```

Expected output:
```
NAME                    STATUS
webcrawler_frontend     Up (healthy)
webcrawler_backend      Up (healthy)
webcrawler_worker       Up
webcrawler_postgres     Up (healthy)
webcrawler_redis        Up (healthy)
```

---

## 🐳 Docker Services

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| `frontend` | Next.js 14 | 3000 | React web interface |
| `backend` | FastAPI | 8000 | REST API server |
| `worker` | Celery | — | Background crawl tasks |
| `postgres` | postgres:16 | 5432 | Primary database |
| `redis` | redis:7 | 6379 | Cache & message broker |
| `nginx` | nginx:1.25 | 80 | Reverse proxy (prod) |

---

## 📖 API Documentation

Once running, access the interactive API docs:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

### Key Endpoints

```http
# Projects
GET    /api/projects          List all projects
POST   /api/projects          Create new project
GET    /api/projects/{id}     Get project details
DELETE /api/projects/{id}     Delete project

# Crawls
POST   /api/crawls/{project_id}/start    Start a crawl
GET    /api/crawls/{crawl_id}/status     Get crawl status
GET    /api/crawls/{crawl_id}/results    Get crawl results (paginated)
GET    /api/crawls/{crawl_id}/issues     Get SEO issues
GET    /api/crawls/{crawl_id}/export     Export as CSV

# Pages
GET    /api/pages/{crawl_id}             List all crawled pages
GET    /api/pages/{page_id}/details      Page SEO details
```

---

## 🔧 Available Commands

```bash
make help          # Show all available commands
make up            # Start services
make down          # Stop services
make build         # Build and start
make logs          # Follow all logs
make clean         # Remove all data (⚠️ destructive)
make restart       # Restart services
make ps            # Show service status
make migrate       # Run DB migrations
make shell-backend # Shell into backend container
make test          # Run tests
make lint          # Run linter
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Nginx (Port 80)                  │
│              Reverse Proxy + Rate Limiting          │
└──────────┬──────────────────────────┬──────────────┘
           │  /api/*  /docs  /ws/*    │  /*
           ▼                          ▼
┌──────────────────┐        ┌──────────────────┐
│  FastAPI Backend │        │  Next.js Frontend │
│     Port 8000    │        │     Port 3000     │
└────────┬─────────┘        └──────────────────┘
         │
    ┌────┴────────────┐
    │                 │
    ▼                 ▼
┌───────────┐  ┌────────────┐
│ PostgreSQL │  │   Redis    │
│  Port 5432│  │  Port 6379 │
└───────────┘  └─────┬──────┘
                     │
               ┌─────▼──────┐
               │   Celery   │
               │   Worker   │
               └────────────┘
```

---

## 🚀 Production Deployment

### With GitHub Container Registry

```bash
# Pull latest images
docker compose -f docker-compose.prod.yml pull

# Start production stack
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

### Push to GitHub

```bash
git remote add origin https://github.com/crawlitron/webcrawler-pro.git
git branch -M main
git push -u origin main
```

The CI/CD pipeline will automatically build and push Docker images to `ghcr.io`.

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Fork and clone
git clone https://github.com/YOUR_crawlitron/webcrawler-pro.git

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes, test, commit
make test
git commit -m "feat: your feature description"

# Push and open PR
git push origin feature/your-feature-name
```

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ by the WebCrawler Pro Contributors**

[Report Bug](https://github.com/crawlitron/webcrawler-pro/issues) · [Request Feature](https://github.com/crawlitron/webcrawler-pro/issues) · [Documentation](https://github.com/crawlitron/webcrawler-pro/wiki)

</div>
