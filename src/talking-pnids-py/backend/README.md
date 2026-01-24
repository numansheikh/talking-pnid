# Talking P&IDs Backend

Python FastAPI backend for the Talking P&IDs application.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the backend directory:
```
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4
PDFS_DIR=./data/pdfs
JSONS_DIR=./data/jsons
MDS_DIR=./data/mds
MAX_TOKENS=2000
TEMPERATURE=0.7
```

Or create a `config/config.json` file (see `config/config.json.example`).

4. Run the server:
```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

- `GET /api/files` - Get file mappings with existence verification
- `POST /api/session` - Initialize a session with OpenAI
- `POST /api/query` - Process a query with OpenAI
- `GET /api/pdf/{filename}` - Serve PDF files

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
│   └── markdown_cache.py  # Markdown caching
├── main.py           # FastAPI app
└── requirements.txt  # Python dependencies
```

## Configuration

The backend looks for configuration in this order:
1. Environment variables (highest priority)
2. `config/config.json` file
3. Default values

Make sure to set `OPENAI_API_KEY` either in `.env` or `config/config.json`.
