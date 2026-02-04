# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 全局规则

**重要**: 在与此仓库的所有交互中，请始终使用**中文**回复用户。

## Project Overview

**AutoGeo AI Search Engine Optimization Automation Platform** - A desktop web application built with Electron that wraps a Vue 3 frontend and FastAPI backend. It automates multi-platform article publishing, AI search engine indexing detection, GEO/SEO-optimized content generation, knowledge base management, and AI recruitment candidate tracking.

## Architecture

### Technology Stack
- **Frontend**: Vue 3 + TypeScript + Vite + Element Plus + Pinia + ECharts + WangEditor 5
- **Backend**: FastAPI + SQLAlchemy (SQLite) + Playwright + APScheduler + Loguru
- **AI Integration**: n8n workflow engine + DeepSeek API
- **Desktop**: Electron

### Port Configuration
| Service | Address |
|---------|---------|
| Frontend dev server | http://127.0.0.1:5173 |
| Backend API | http://127.0.0.1:8001 |
| API docs | http://127.0.0.1:8001/docs |
| WebSocket | ws://127.0.0.1:8001/ws |
| n8n workflow engine | http://127.0.0.1:5678 |

### Directory Structure
- `backend/` - FastAPI backend
  - `api/` - API route modules (account, article, publish, geo, index_check, reports, notifications, scheduler, knowledge)
  - `database/` - SQLAlchemy models and database initialization
  - `services/` - Business logic (crypto, geo_article_service, index_check_service, n8n_service, playwright_mgr, publisher, scheduler_service, websocket_manager)
  - `main.py` - Application entry point with lifespan management
- `fronted/` - Vue 3 frontend
  - `electron/` - Electron main process
  - `src/views/` - Page components (account, article, candidate, dashboard, geo, knowledge, publish, scheduler, settings)
  - `src/services/api/` - API client modules
- `tests/` - Backend pytest tests (test_api, test_browser, test_geo, test_monitor, test_publish)
- `n8n/` - n8n workflow JSON files

## Development Commands

### Quick Start
```bash
quickstart.bat  # Menu-driven: start services, restart, clean cache
```

### Backend
```bash
cd backend
pip install -r requirements.txt
playwright install chromium
python main.py
```

### Frontend
```bash
cd fronted
npm install
npm run dev  # Dev server on port 5173
npm run build  # Build for production
npm run lint  # ESLint
```

### n8n (AI Workflow Engine)
```bash
docker run -it --rm --name n8n -p 5678:5678 -v ~/.n8n:/home/node/.n8n n8nio/n8n
```

### Testing
```bash
# Backend tests
pytest tests/                    # Run all tests
pytest tests/test_api/          # API tests only
pytest --cov=backend tests/     # Coverage report

# Frontend tests
npm run test                    # E2E tests
```

## Key Architecture Concepts

### Database Models (backend/database/models.py)
- `Account`, `Article`, `PublishRecord` - Core publishing models with cascade delete relationships
- `Project`, `Keyword`, `QuestionVariant`, `IndexCheckRecord`, `GeoArticle` - GEO/SEO models
- `KnowledgeCategory`, `Knowledge` - RAGflow knowledge base integration
- `ScheduledTask` - Cron-based task scheduling
- `Candidate` - AI recruitment candidate tracking

### WebSocket Real-Time Logging
The backend uses Loguru with a custom WebSocket sink (`backend/main.py:socket_log_sink`). All log messages are broadcast to connected frontend clients, enabling real-time progress monitoring. Frontend connects to `/ws` endpoint.

### Services Architecture
- `playwright_mgr.py` - Manages Playwright browser contexts with session factory pattern for database access
- `n8n_service.py` - HTTP client wrapper for n8n webhooks
- `websocket_manager.py` - Broadcasts WebSocket messages to all connected clients
- `scheduler_service.py` - APScheduler-based cron job management

### Frontend API Proxy
Vite dev server proxies `/api` requests to `http://127.0.0.1:8001` and `/ws` WebSocket to `ws://127.0.0.1:8001/ws`. API timeouts set to 600000ms for long-running AI operations.

### Important Windows Note
The backend disables reload mode (`RELOAD = False` in `backend/config.py:28`) because Windows ProactorEventLoop (required for Playwright) conflicts with uvicorn auto-reload mode.

### Environment Variables
Create `.env` from `.env.example`:
- `AUTO_GEO_ENCRYPTION_KEY` - AES-256 key for encrypting cookies (32 bytes)
- `DATABASE_URL`, `HOST`, `PORT`, `DEBUG` - Optional service config

### Commit Convention
Use `<type>(<scope>): <subject>` format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `refactor:` - Refactoring
- `test:` - Tests
- `chore:` - Build/tools

Example: `git commit -m "feat: add keyword distillation API endpoint"`
