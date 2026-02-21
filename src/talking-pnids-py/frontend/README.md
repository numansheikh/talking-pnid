# Talking P&IDs Frontend

React + TypeScript frontend for the Talking P&IDs application, built with Vite.

**Live app:** https://talking-pnid.vercel.app/app

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   ```

Runs at http://localhost:3000 and proxies `/api` to http://localhost:8000 (Python backend).

## Build

```bash
npm run build
```

Output: `dist/`

## Project Structure

```
src/
├── contexts/        # React contexts (AuthContext)
├── pages/           # Page components (Login, Signup, App)
├── utils/           # API client (fetchFiles, startSession, sendQuery)
├── services/        # Additional services
├── App.tsx          # Main app with routing
├── main.tsx         # Entry point
└── index.css        # Global styles
```

## API Integration

The frontend expects a Python backend with:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/files` | File mappings |
| POST | `/api/session` | Start session |
| POST | `/api/query` | Send query |
| GET | `/api/pdf/:filename` | PDF file |

For production, set `VITE_API_BASE_URL` to `https://decent-lilli-cogit-0d306da3.koyeb.app`. The client appends `/api` automatically.

## Deployment

Deploy to Vercel. Root directory: `src/talking-pnids-py/frontend`. Set `VITE_API_BASE_URL` to your backend URL. See the main [README](../README.md#deployment) and [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md).
