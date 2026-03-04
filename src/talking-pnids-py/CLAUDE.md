# Talking P&IDs - Project Guide

## What the App Does
AI-powered Q&A assistant for analyzing industrial Piping & Instrumentation Diagrams (P&IDs). Users view PDF diagrams, ask questions about equipment and processes, and get AI-powered answers with interactive cross-referencing between diagrams.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python FastAPI (port 8000) |
| Frontend | React 18 + TypeScript + Vite (port 3000) |
| LLM | OpenAI (gpt-4, gpt-4o, o1, o3, etc.) via LangChain |
| Deployment | Koyeb (backend) + Vercel (frontend) |

## Project Structure

```
talking-pnids-py/
├── backend/          # Python FastAPI
├── frontend/         # React + TypeScript
├── config/           # file-mappings.json, config.json, prompts.json
├── data/
│   ├── pdfs/         # P&ID diagram PDFs
│   ├── mds/          # Markdown docs (injected as LLM context)
│   └── jsons/        # Equipment/system JSON schemas
├── start.sh          # Starts both services (also start.bat for Windows)
├── requirements.txt  # Python dependencies
└── package.json      # Root npm scripts for orchestration
```

## Backend

### Key Files
- `backend/main.py` — FastAPI app entry point, CORS middleware, route registration
- `backend/api/session.py` — `POST /api/session`: loads all markdown docs, runs init LLM prompt, returns welcome message + session ID
- `backend/api/query.py` — `POST /api/query`: injects relevant markdown as LLM context, returns AI answer
- `backend/api/files.py` — `GET /api/files`: returns file mappings with file existence checks
- `backend/api/pdf.py` — `GET /api/pdf/{filename}`: serves PDF files
- `backend/utils/langchain_setup.py` — Model routing (LangChain for standard models, direct API for reasoning models), in-memory session history
- `backend/utils/config.py` — Config loading: env vars > config.json > defaults
- `backend/utils/paths.py` — Path resolution supporting both local dev and cloud deployment
- `backend/utils/markdown_cache.py` — Markdown file caching for performance

### API Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/files` | File mappings with existence checks |
| POST | `/api/session` | Initialize session, load docs, get welcome message |
| POST | `/api/query` | Send query, get LLM response |
| GET | `/api/pdf/{filename}` | Serve PDF file |
| GET | `/health` | Health check |
| GET | `/debug/paths` | Debug path resolution |

### LLM Integration
- **Standard models** (gpt-4, gpt-4o): routed through LangChain `ChatOpenAI`
- **Reasoning models** (o1, o3, gpt-5.x): routed through direct OpenAI reasoning API
- Session history stored in-memory (global dict keyed by `sessionId`)
- Markdown docs injected into system prompt as context per query

## Frontend

### Key Files
- `frontend/src/pages/AppPage.tsx` — Main app UI (~600 lines), all chat and session logic
- `frontend/src/utils/api.ts` — Typed API client functions (`fetchFiles`, `startSession`, `sendQuery`, `getPdfUrl`)
- `frontend/src/App.tsx` — Router setup
- `frontend/vite.config.ts` — Dev proxy: `/api` → `localhost:8000`
- `frontend/vercel.json` — Vercel deployment config

### UI Layout (AppPage.tsx)
- **Left sidebar (20%):** P&ID file list with selection
- **Center panel (50%):** PDF viewer (iframe) + details panel
- **Right sidebar (30%):** Chat interface with markdown rendering

### P&ID Link Processing
The frontend parses LLM responses for P&ID references in formats like `[doc_id:...]` or `[PID-####]` and converts them to clickable links that switch the active diagram in the sidebar.

## Configuration

### Files
- `config/file-mappings.json` — Maps doc IDs to their PDF, MD, and JSON files
- `config/config.json` — OpenAI model, temperature, max tokens, directory paths
- `config/prompts.json` — System prompt, session init prompt, response format instructions

### Priority
Environment variables override `config.json`, which overrides built-in defaults. This allows secure cloud deployment without modifying files.

### Key Env Vars
- `OPENAI_API_KEY` — Required
- `MODEL` — OpenAI model name (e.g. `gpt-4o`)
- `PDFS_DIR`, `MDS_DIR`, `JSONS_DIR` — Absolute paths for cloud deployment

## Data Flow

1. Page loads → `GET /api/files` → sidebar populated with P&ID list
2. "Start Session" → `POST /api/session` → all markdowns loaded into LLM context, welcome message returned
3. User query → `POST /api/query` (includes selected P&ID + session ID) → LLM responds with context-aware answer
4. Response parsed → P&ID references converted to clickable links → user navigates between diagrams

## Deployment

- **Backend:** Koyeb — `https://decent-lilli-cogit-0d306da3.koyeb.app`
  - Entry: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Frontend:** Vercel — `https://talking-pnid.vercel.app/app`
  - Env var: `VITE_API_BASE_URL=https://decent-lilli-cogit-0d306da3.koyeb.app`
