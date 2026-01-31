# Environment Variables Setup Guide

This guide explains how to configure the application using environment variables for universal deployment across local and cloud environments.

## Quick Start

### Option 1: Using .env file (Recommended for Local Development)

1. Copy the example file:
   ```bash
   cd backend
   cp env.example .env
   ```

2. Edit `.env` and add your OpenAI API key:
   ```bash
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

3. The application will automatically load variables from `.env` (via python-dotenv)

### Option 2: Export Environment Variables (Recommended for Cloud Deployment)

```bash
export OPENAI_API_KEY=sk-your-actual-api-key-here
export OPENAI_MODEL=gpt-5.2
export REASONING_EFFORT=medium
```

## Available Environment Variables

### Required

- **`OPENAI_API_KEY`**: Your OpenAI API key (required for AI features)
  - Example: `OPENAI_API_KEY=sk-proj-...`

### Optional - OpenAI Settings

- **`OPENAI_MODEL`**: Model to use (default: `gpt-4`)
  - Example: `OPENAI_MODEL=gpt-5.2`
- **`REASONING_EFFORT`**: Reasoning effort level for gpt-5.2 (default: `medium`)
  - Options: `low`, `medium`, `high`
  - Example: `REASONING_EFFORT=high`

### Optional - Directory Paths

These can be **relative** (for local dev) or **absolute** (for cloud deployment):

- **`PDFS_DIR`**: Path to PDF files directory (default: `./data/pdfs`)
  - Local: `PDFS_DIR=./data/pdfs`
  - Cloud: `PDFS_DIR=/app/data/pdfs` or `PDFS_DIR=/var/www/data/pdfs`
  
- **`JSONS_DIR`**: Path to JSON files directory (default: `./data/jsons`)
  - Local: `JSONS_DIR=./data/jsons`
  - Cloud: `JSONS_DIR=/app/data/jsons`
  
- **`MDS_DIR`**: Path to Markdown files directory (default: `./data/mds`)
  - Local: `MDS_DIR=./data/mds`
  - Cloud: `MDS_DIR=/app/data/mds`

**Note**: If you set absolute paths, they will be used directly. If relative paths are set, they will be resolved relative to the project root.

### Optional - API Settings

- **`MAX_TOKENS`**: Maximum tokens for responses (default: `2000`)
  - Example: `MAX_TOKENS=4000`
  
- **`TEMPERATURE`**: Temperature for AI responses (default: `0.7`)
  - Example: `TEMPERATURE=0.5`

### Optional - CORS

- **`FRONTEND_URL`**: Frontend URL for CORS (default: `http://localhost:3000`)
  - Example: `FRONTEND_URL=https://your-app.vercel.app`

### Optional - Project Root

- **`PROJECT_ROOT`**: Override project root detection (usually not needed)
  - Example: `PROJECT_ROOT=/app`

## Priority Order

Configuration is loaded in this priority order (highest to lowest):

1. **Environment Variables** (highest priority)
2. `config/config.json` file
3. Default values

## Examples

### Local Development

```bash
# .env file
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-5.2
PDFS_DIR=./data/pdfs
JSONS_DIR=./data/jsons
MDS_DIR=./data/mds
```

### Cloud Deployment (Koyeb/Railway/Render)

```bash
# Set in platform's environment variables
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-5.2
PDFS_DIR=/app/data/pdfs
JSONS_DIR=/app/data/jsons
MDS_DIR=/app/data/mds
FRONTEND_URL=https://your-frontend.vercel.app
```

### Docker Deployment

```dockerfile
ENV OPENAI_API_KEY=sk-your-key-here
ENV PDFS_DIR=/app/data/pdfs
ENV JSONS_DIR=/app/data/jsons
ENV MDS_DIR=/app/data/mds
```

## Verification

To verify your environment variables are loaded correctly:

```bash
# Check backend
curl http://localhost:8000/debug/paths

# Or check in Python
cd backend
python -c "from utils.config import load_config; import json; print(json.dumps(load_config(), indent=2))"
```

## Security Notes

- **Never commit `.env` files** to version control
- `.env` is already in `.gitignore`
- For cloud deployment, use the platform's secure environment variable settings
- API keys should never appear in code or logs
