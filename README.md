# Agent Skill Extension

A Chrome extension that serves as a universal Agent + Skill platform for internal company use. Employees interact with a backend agent through the extension, create custom skills, test and evaluate them, and bind them to conversations for specialized task execution.

## Architecture

```
Chrome Extension (React + TypeScript)
├── Side Panel: Chat + page context + skill binding
└── Options Page: Skill management + skill creation + memory management
         │
         │  HTTP / SSE
         ▼
FastAPI Backend (Single Service)
├── API Layer: /chat /skills /skill-creator /memory /workspace
├── Agent Core: LiteLLM + tool use + context assembly
├── Skill Manager: Load/parse/bind/install/uninstall
├── Memory System: Fact extraction + prompt injection
└── Storage: SQLite + memory.json + filesystem
```

## Quick Start

### Backend

```bash
cd backend
make install    # Install Python dependencies
make dev        # Start backend on port 8001
```

### Frontend (Chrome Extension)

```bash
cd frontend
npm install     # Install dependencies
npm run dev     # Start dev server with HMR
npm run build   # Build for production
```

Load the extension in Chrome:
1. Go to `chrome://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `frontend/dist` directory

### Docker Deployment

```bash
cp .env.example .env
# Edit .env with your API key
docker compose up -d
```

## Configuration

### Backend (`backend/config.yaml`)

```yaml
llm:
  model: gpt-4o
  api_key: $OPENAI_API_KEY

memory:
  enabled: true
  debounce_seconds: 30

skills:
  public_path: skills/public
  custom_path: skills/custom
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | SSE streaming chat |
| GET | `/api/chat/history` | List chat threads |
| GET | `/api/chat/{thread_id}` | Get thread messages |
| GET | `/api/skills` | List skills |
| GET | `/api/skills/{name}` | Skill details |
| PUT | `/api/skills/{name}` | Toggle enabled |
| DELETE | `/api/skills/{name}` | Uninstall custom skill |
| POST | `/api/skill-creator/start` | Start skill creation |
| POST | `/api/skill-creator/install` | Install from draft |
| GET | `/api/memory` | Get memory data |
| POST | `/api/memory/reload` | Force reload |
| PUT | `/api/memory` | Update memory |
| GET | `/api/workspace/{id}/files` | List files |
| POST | `/api/workspace/{id}/upload` | Upload file |
| GET | `/health` | Health check |

## Testing

```bash
cd backend
make test       # Run all 53 tests
make lint       # Lint with ruff
```

## Tech Stack

**Backend:** Python 3.12+, FastAPI, LiteLLM, SQLAlchemy (async), aiosqlite, SSE

**Frontend:** React 18, TypeScript, Vite + CRXJS, Tailwind CSS, Zustand, react-markdown
