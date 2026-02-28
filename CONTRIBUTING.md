# 🤝 Contributing to WebCrawler Pro

Thank you for your interest in contributing to WebCrawler Pro! We welcome all contributions — bug reports, feature requests, documentation improvements, and code changes.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

---

## 📜 Code of Conduct

This project adheres to a Code of Conduct based on respect and inclusivity. By participating, you agree to:
- Be respectful and constructive in all communications
- Welcome newcomers and help them get started
- Focus on what is best for the community and project
- Accept constructive criticism gracefully

---

## 🚀 Getting Started

### Prerequisites

- Docker 24.0+ and Docker Compose 2.20+
- Git 2.x
- Python 3.11+ (for local backend development)
- Node.js 18+ (for local frontend development)

### Fork and Clone

```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork
git clone https://github.com/YOUR_crawlitron/webcrawler-pro.git
cd webcrawler-pro

# 3. Add the upstream remote
git remote add upstream https://github.com/crawlitron/webcrawler-pro.git

# 4. Verify remotes
git remote -v
```

---

## 🛠️ Development Setup

```bash
# 1. Copy environment file
cp .env.example .env
# Edit .env with your local values

# 2. Start development stack
make build

# 3. Run migrations
make migrate

# 4. Verify everything is running
make ps
```

### Backend Development (Python / FastAPI)

```bash
# Enter backend container
make shell-backend

# Or run locally with virtual environment
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
make test

# Run linter
make lint
```

### Frontend Development (Next.js)

```bash
# Enter frontend container
make shell-frontend

# Or run locally
cd frontend
npm install
npm run dev
```

---

## 📁 Project Structure

```
webcrawler-pro/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── routers/            # API route handlers
│   │   ├── crawler/            # Scrapy spider & SEO analyzer
│   │   ├── models.py           # SQLAlchemy ORM models
│   │   ├── schemas.py          # Pydantic request/response schemas
│   │   ├── database.py         # DB connection & session
│   │   └── main.py             # FastAPI app entry point
│   ├── celery_worker.py        # Celery configuration
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # Next.js 14 application
│   ├── src/
│   │   ├── app/                # App Router pages
│   │   ├── components/         # Reusable UI components
│   │   └── lib/                # API client & utilities
│   └── Dockerfile
├── nginx/
│   └── nginx.conf              # Reverse proxy config
├── .github/
│   └── workflows/              # CI/CD pipelines
├── docker-compose.yml          # Development stack
├── docker-compose.prod.yml     # Production stack
├── Makefile                    # Developer shortcuts
└── .env.example                # Environment template
```

---

## 💡 How to Contribute

### 🐛 Reporting Bugs

1. **Search existing issues** first to avoid duplicates
2. Create a **new issue** using the Bug Report template
3. Include:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Docker version, browser)
   - Relevant logs (`make logs`)

### ✨ Suggesting Features

1. Open a **Feature Request** issue
2. Describe the problem it solves
3. Outline your proposed solution
4. Discuss alternatives you considered

### 📝 Improving Documentation

Documentation improvements are always welcome! Edit markdown files directly and submit a PR.

### 🔧 Submitting Code Changes

1. **Check existing issues** and PR to avoid duplication
2. **Open an issue first** for significant changes to discuss the approach
3. Follow the [development workflow](#development-workflow) below

---

## 💻 Development Workflow

```bash
# 1. Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# 2. Create a feature branch
git checkout -b feature/your-feature-name
# Or for bugfixes:
git checkout -b fix/issue-description

# 3. Make your changes
# ... write code ...

# 4. Run tests and linting
make test
make lint

# 5. Commit your changes
git add .
git commit -m "feat: add your feature description"

# 6. Push to your fork
git push origin feature/your-feature-name

# 7. Open a Pull Request on GitHub
```

---

## 📐 Coding Standards

### Python (Backend)

- **Style**: Follow [PEP 8](https://pep8.org/) with max line length **100**
- **Linting**: `flake8` (enforced in CI)
- **Formatting**: `black` for consistent formatting
- **Type hints**: Required for all function signatures
- **Docstrings**: Google-style docstrings for all public functions

```python
# Good example
async def get_project(project_id: int, db: Session = Depends(get_db)) -> ProjectResponse:
    """Retrieve a project by ID.

    Args:
        project_id: The unique identifier of the project.
        db: Database session dependency.

    Returns:
        ProjectResponse with project details.

    Raises:
        HTTPException: 404 if project not found.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
```

### TypeScript (Frontend)

- **Style**: Follow ESLint configuration
- **Components**: Functional components with TypeScript interfaces
- **Naming**: PascalCase for components, camelCase for functions/variables
- **Imports**: Absolute imports using `@/` alias

```typescript
// Good example
interface CrawlStatusProps {
  crawlId: string;
  onComplete?: () => void;
}

export function CrawlStatus({ crawlId, onComplete }: CrawlStatusProps) {
  // ...
}
```

---

## 📝 Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Code style (no logic change) |
| `refactor` | Code refactoring |
| `test` | Adding/updating tests |
| `chore` | Build process, dependencies |
| `perf` | Performance improvement |

### Examples

```bash
git commit -m "feat(crawler): add JavaScript rendering via Playwright"
git commit -m "fix(api): handle 429 rate limit in crawl requests"
git commit -m "docs: update installation guide for ARM64"
git commit -m "chore: upgrade FastAPI to 0.110.0"
```

---

## 🔍 Pull Request Process

1. **Fill out** the PR template completely
2. **Link** the related issue (`Closes #123`)
3. **Ensure CI passes** — all tests and lint checks must be green
4. **Request review** from at least one maintainer
5. **Respond to feedback** promptly and constructively
6. **Squash commits** if requested before merge

### PR Checklist

- [ ] Tests added/updated for new functionality
- [ ] Documentation updated if needed
- [ ] `make lint` passes locally
- [ ] `make test` passes locally
- [ ] No `.env` or secrets committed
- [ ] PR description clearly explains changes

---

## ❓ Questions?

Open a [Discussion](https://github.com/crawlitron/webcrawler-pro/discussions) on GitHub.

Thank you for contributing to WebCrawler Pro! 🕷️
