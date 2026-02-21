# Collaborator Onboarding – Talking P&IDs

Quick setup guide for new team members.

## Live app

- **Backend:** https://decent-lilli-cogit-0d306da3.koyeb.app
- **Frontend:** https://talking-pnid.vercel.app/app

## 1. Clone and enter the project

```bash
git clone https://github.com/numansheikh/talking-pnid.git
cd talking-pnid/src/talking-pnids-py
```

## 2. Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **OpenAI API key** (see below)

## 3. API key

Each collaborator uses their own OpenAI API key. Keys are per-account and shouldn't be shared.

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create an API key
3. Add it locally (see Configure below) — **never commit it to git**

## 4. Configure (pick one)

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

## 5. Run locally

From `src/talking-pnids-py`:

```bash
npm install && npm start
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000

Stop with **Ctrl+C**.

## 6. Project layout

| Area           | Path                         |
|----------------|------------------------------|
| Python backend | `backend/`                   |
| React frontend | `frontend/`                  |
| Config         | `config/`                    |
| Data (PDFs)    | `data/`                      |
| Main docs      | `README.md` in this folder   |

## 7. Deployment

- **Backend:** Koyeb — https://decent-lilli-cogit-0d306da3.koyeb.app
- **Frontend:** Vercel — https://talking-pnid.vercel.app/app

See `README.md` → "Deployment" and "Verify online deployment".

## 8. Important

- Don't commit `.env` or `config/config.json` (they hold secrets)
- Sample data is in the repo; no extra setup needed
- Request repo access and deployment credentials from the project owner
