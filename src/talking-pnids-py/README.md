# Talking P&IDs - Python Backend + React Frontend

AI-powered Q&A application for Piping & Instrumentation Diagrams with Python FastAPI backend and React frontend.

## Quick Start

### Step 1: Setup Data Files

First, copy the data files (PDFs, JSONs, markdown) from the JS project:

**Using Node.js (recommended):**
```bash
npm run setup-data
```

**Or manually:**
```bash
# macOS/Linux
./setup-data.sh

# Windows
setup-data.bat
```

This will copy the data files from `../talking-pnids-js/data/` to `./data/`.

### Step 2: Start the Application

### Option 1: Using the Start Script (Recommended)

**On macOS/Linux:**
```bash
./start.sh
```

**On Windows:**
```bash
start.bat
```

**Cross-platform (Node.js):**
```bash
npm install
npm start
```

The script will:
- Create virtual environment if needed
- Install backend dependencies if needed
- Install frontend dependencies if needed
- Start both backend (port 8000) and frontend (port 3000)

### Option 2: Manual Start

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**Frontend (in another terminal):**
```bash
cd frontend
npm install
npm run dev
```

## Configuration

The OpenAI API key is already configured in `config/config.json` (copied from the JS project).

To change settings, edit `config/config.json`:
```json
{
  "openai": {
    "apiKey": "your-key-here",
    "model": "gpt-4"
  },
  "directories": {
    "pdfs": "./data/pdfs",
    "jsons": "./data/jsons",
    "mds": "./data/mds"
  },
  "settings": {
    "maxTokens": 2000,
    "temperature": 0.7
  }
}
```

Or use environment variables (they override config.json):
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `PDFS_DIR`
- `JSONS_DIR`
- `MDS_DIR`
- `MAX_TOKENS`
- `TEMPERATURE`

## Project Structure

```
talking-pnids-py/
├── backend/          # Python FastAPI backend
│   ├── api/         # API endpoints
│   ├── utils/       # Utilities (config, cache)
│   └── main.py      # FastAPI app
├── frontend/         # React + Vite frontend
│   ├── src/
│   │   ├── pages/   # Page components
│   │   ├── contexts/# React contexts
│   │   └── utils/   # API client
│   └── package.json
├── config/          # Configuration files
│   ├── config.json  # Main config (with API key)
│   ├── prompts.json # AI prompts
│   └── file-mappings.json # File mappings
├── data/            # Data files (PDFs, JSONs, markdown)
│   ├── pdfs/        # PDF files
│   ├── jsons/       # JSON schema files
│   └── mds/         # Markdown files
└── start.sh         # Start script (Unix/Mac)
```

## API Endpoints

- `GET /api/files` - Get file mappings
- `POST /api/session` - Initialize session
- `POST /api/query` - Process query
- `GET /api/pdf/{filename}` - Serve PDF files

## Development

Backend runs on: http://localhost:8000
Frontend runs on: http://localhost:3000

The frontend automatically proxies API requests to the backend.

## Notes

- Login is currently disabled - all routes are public
- The backend uses markdown caching for performance
- Configuration is loaded from `config/config.json` with environment variable overrides
