# Talking P&IDs Backend

Python FastAPI backend for the Talking P&IDs application.

**Live API:** https://decent-lilli-cogit-0d306da3.koyeb.app

## Setup

1. **Virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configuration:**

   Copy `env.example` to `.env` and add your OpenAI API key:
   ```bash
   cp env.example .env
   ```

   Or create `config/config.json` in the parent directory (see `../config/config.json.example`).

4. **Run:**
   ```bash
   python main.py
   ```

   Or with uvicorn:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

API: http://localhost:8000

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Required. OpenAI API key | — |
| `OPENAI_MODEL` | Model name | `gpt-4` |
| `REASONING_EFFORT` | For reasoning models: `low`, `medium`, `high` | `medium` |
| `PDFS_DIR` | PDF directory | `./data/pdfs` |
| `JSONS_DIR` | JSON directory | `./data/jsons` |
| `MDS_DIR` | Markdown directory | `./data/mds` |
| `MAX_TOKENS` | Max tokens | `2000` |
| `TEMPERATURE` | Temperature | `0.7` |
| `FRONTEND_URL` | CORS origin (production) | `http://localhost:3000` |

See `ENV_SETUP.md` for full details.

## Project Structure

```
backend/
├── api/
│   ├── files.py      # File mappings endpoint
│   ├── session.py    # Session initialization
│   ├── query.py      # Query processing
│   └── pdf.py        # PDF serving
├── utils/
│   ├── config.py     # Configuration loading
│   ├── paths.py      # Path resolution (project root, config, data)
│   ├── markdown_cache.py
│   └── langchain_setup.py
├── main.py           # FastAPI app
├── requirements.txt
├── Procfile          # For Koyeb (used when root is parent dir)
├── env.example       # Example .env
├── ENV_SETUP.md      # Detailed env var guide
└── KOYEB_DEPLOYMENT.md   # Koyeb deployment guide
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/files` | File mappings with existence verification |
| POST | `/api/session` | Initialize session |
| POST | `/api/query` | Process query |
| GET | `/api/pdf/{filename}` | Serve PDF files |
| GET | `/health` | Health check |
| GET | `/debug/paths` | Debug path resolution |

## Deployment

Deploy to Koyeb using the parent project root (`src/talking-pnids-py`). See the main [README](../README.md#deployment) and [KOYEB_DEPLOYMENT.md](KOYEB_DEPLOYMENT.md).
