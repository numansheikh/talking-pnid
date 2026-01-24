# Talking P&IDs Frontend

React + TypeScript frontend for the Talking P&IDs application, built with Vite.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

The frontend will run on `http://localhost:3000` and proxy API requests to `http://localhost:8000` (Python backend).

## Build

```bash
npm run build
```

The built files will be in the `dist` directory.

## Project Structure

```
src/
├── contexts/        # React contexts (AuthContext)
├── pages/          # Page components (Login, Signup, App)
├── utils/          # Utility functions (API client)
├── App.tsx         # Main app component with routing
├── main.tsx        # Entry point
└── index.css       # Global styles
```

## API Integration

The frontend expects a Python backend running on `http://localhost:8000` with the following endpoints:

- `GET /api/files` - Get file mappings
- `POST /api/session` - Start a session
- `POST /api/query` - Send a query
- `GET /api/pdf/:filename` - Get PDF file

All API calls are proxied through Vite's dev server during development.
