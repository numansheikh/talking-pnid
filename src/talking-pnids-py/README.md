# Talking P&IDs - Python Backend + React Frontend

AI-powered Q&A application for Piping & Instrumentation Diagrams with Python FastAPI backend and React frontend.

**Note:** All commands below are run from the `talking-pnids-py` directory (e.g. `src/talking-pnids-py` if this repo includes a `src/` layout).

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **OpenAI API key** (for AI features)

### Step 1: Setup Data Files

Data files (PDFs, JSONs, markdown) can come from the JS project or your own sources.

**Option A: Copy from JS project** (if `talking-pnids-js` exists as a sibling directory)

```bash
# From the talking-pnids-py directory
npm run setup-data
# or: ./setup-data.sh (macOS/Linux) / setup-data.bat (Windows)
```

This copies from `../talking-pnids-js/data/` to `./data/`.

**Option B: Use existing data**

Place your files in `data/pdfs`, `data/jsons`, and `data/mds`. Ensure `config/file-mappings.json` matches your files.

### Step 2: Configure

Create `config/config.json` (or copy from `config/config.json.example`):

```json
{
  "openai": {
    "apiKey": "your-openai-api-key-here",
    "model": "gpt-4"
  },
  "directories": {
    "pdfs": "./data/pdfs",
    "jsons": "./data/jsons",
    "mds": "./data/mds"
  },
  "settings": {
    "maxTokens": 2000,
    "temperature": 0.7,
    "reasoningEffort": "medium"
  }
}
```

Or use a `.env` file in `backend/` (copy from `backend/env.example`):

```
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4
REASONING_EFFORT=medium
PDFS_DIR=./data/pdfs
JSONS_DIR=./data/jsons
MDS_DIR=./data/mds
```

### Step 3: Start the Application

**Using the start script (recommended):**

```bash
# macOS/Linux
./start.sh

# Windows
start.bat

# Cross-platform (Node.js)
npm install && npm start
```

The script will create a virtual environment, install dependencies, and start backend (port 8000) and frontend (port 3000).

**Manual start:**

```bash
# Terminal 1 - Backend
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py

# Terminal 2 - Frontend
cd frontend
npm install
npm run dev
```

## Configuration

Configuration is loaded in this order (highest priority first):

1. **Environment variables** (including `.env` in `backend/`)
2. **`config/config.json`**
3. **Defaults**

### Config file

Edit `config/config.json`:

| Key | Description |
|-----|-------------|
| `openai.apiKey` | OpenAI API key |
| `openai.model` | Model (e.g. `gpt-4`, `gpt-4o`, `o1-preview`) |
| `directories.pdfs` | Path to PDF files |
| `directories.jsons` | Path to JSON schema files |
| `directories.mds` | Path to markdown files |
| `settings.maxTokens` | Max response tokens |
| `settings.temperature` | Model temperature |
| `settings.reasoningEffort` | For reasoning models: `low`, `medium`, `high` |

### Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | — |
| `OPENAI_MODEL` | Model name | `gpt-4` |
| `REASONING_EFFORT` | Reasoning effort | `medium` |
| `PDFS_DIR` | PDF directory path | `./data/pdfs` |
| `JSONS_DIR` | JSON directory path | `./data/jsons` |
| `MDS_DIR` | Markdown directory path | `./data/mds` |
| `MAX_TOKENS` | Max tokens | `2000` |
| `TEMPERATURE` | Temperature | `0.7` |
| `FRONTEND_URL` | CORS origin (e.g. frontend URL in production) | `http://localhost:3000` |

## Project Structure

```
talking-pnids-py/
├── backend/              # Python FastAPI backend
│   ├── api/
│   │   ├── files.py      # File mappings
│   │   ├── session.py    # Session init
│   │   ├── query.py      # Query processing
│   │   └── pdf.py        # PDF serving
│   ├── utils/
│   │   ├── config.py     # Config loading
│   │   ├── paths.py      # Path resolution
│   │   ├── markdown_cache.py
│   │   └── langchain_setup.py
│   ├── main.py           # FastAPI app
│   ├── requirements.txt
│   ├── Procfile          # For cloud deployment
│   └── env.example       # Example .env
├── frontend/             # React + Vite + TypeScript
│   ├── src/
│   │   ├── pages/        # Page components
│   │   ├── contexts/     # React contexts
│   │   ├── utils/        # API client
│   │   └── services/     # Additional services
│   ├── package.json
│   ├── vite.config.ts
│   └── vercel.json       # For Vercel deployment
├── config/
│   ├── config.json       # Main config
│   ├── config.json.example
│   ├── prompts.json
│   └── file-mappings.json
├── data/
│   ├── pdfs/
│   ├── jsons/
│   └── mds/
├── start.sh              # Start script (Unix/Mac)
├── start.bat             # Start script (Windows)
├── start.js              # Cross-platform start
├── package.json          # Root scripts
└── Procfile              # For Koyeb (root dir deployment)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/files` | Get file mappings with existence verification |
| POST | `/api/session` | Initialize a session |
| POST | `/api/query` | Process a query |
| GET | `/api/pdf/{filename}` | Serve PDF files |
| GET | `/health` | Health check |
| GET | `/debug/paths` | Debug path resolution |

## Deployment

### Backend: Koyeb

1. **Prerequisites:** Koyeb account, GitHub repo
2. **Create App** → GitHub → select repository
3. **Root directory:** `src/talking-pnids-py`
4. **Procfile** (use the one at project root):
   ```
   web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
5. **Environment variables:**

   | Variable | Value |
   |----------|-------|
   | `OPENAI_API_KEY` | Your API key |
   | `FRONTEND_URL` | Your Vercel URL (e.g. `https://your-app.vercel.app`) |
   | `OPENAI_MODEL` | Optional, e.g. `gpt-4` |
   | `REASONING_EFFORT` | Optional, e.g. `medium` |
   | `PDFS_DIR` | `/app/data/pdfs` (absolute paths for cloud) |
   | `JSONS_DIR` | `/app/data/jsons` |
   | `MDS_DIR` | `/app/data/mds` |

6. Deploy. Note your backend URL (e.g. `https://your-app.koyeb.app`).

**Data files:** Keep the `data/` directory in the repo so it is deployed with the app. Use absolute paths in env vars as above.

### Frontend: Vercel

1. **Prerequisites:** Vercel account, GitHub repo
2. **Add Project** → Import Git Repository
3. **Root directory:** `src/talking-pnids-py/frontend`
4. **Environment variable:**

   | Variable | Value |
   |----------|-------|
   | `VITE_API_BASE_URL` | Backend URL without `/api` (e.g. `https://your-app.koyeb.app`) |

5. Deploy.

### Post-deployment

1. Set `FRONTEND_URL` in Koyeb to your Vercel URL.
2. Verify CORS: open the Vercel app and ensure API calls succeed.

See `backend/KOYEB_DEPLOYMENT.md` and `frontend/VERCEL_DEPLOYMENT.md` for more detail.

## Development

- **Backend:** http://localhost:8000  
- **Frontend:** http://localhost:3000  

The frontend proxies `/api` to the backend during development.

## Notes

- Login is currently disabled; all routes are public.
- The backend uses markdown caching for performance.
- For cloud deployment, use absolute paths for data directories.
