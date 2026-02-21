# Collaborator Onboarding – Talking P&IDs

Quick setup guide for new team members.

## 1. Clone and enter the project

```bash
git clone https://github.com/numansheikh/talking-pnid.git
cd talking-pnid/src/talking-pnids-py
```

## 2. Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **OpenAI API key** (ask the project owner if you need one)

## 3. Configure (pick one)

**Option A – `.env` (recommended, not committed):**

```bash
cd backend
cp env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-your-key-here
```

**Option B – `config.json`:**

```bash
cp config/config.json.example config/config.json
# Edit config/config.json and add your API key
```

## 4. Run locally

From `src/talking-pnids-py`:

```bash
npm install && npm start
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000

Stop with **Ctrl+C**.

## 5. Project layout

| Area           | Path                         |
|----------------|------------------------------|
| Python backend | `backend/`                   |
| React frontend | `frontend/`                  |
| Config         | `config/`                    |
| Data (PDFs)    | `data/`                      |
| Main docs      | `README.md` in this folder   |

## 6. Deployment

- **Backend:** Koyeb
- **Frontend:** Vercel

See `README.md` → "Deployment" and "Verify online deployment".

## 7. Important

- Don't commit `.env` or `config/config.json` (they hold secrets)
- Sample data is in the repo; no extra setup needed
- Request repo access, API keys, and deployment credentials from the project owner
