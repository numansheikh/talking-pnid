# Deployment Guide - Separate Backend & Frontend

Since Vercel's Python runtime doesn't fully support FastAPI/ASGI applications, we'll deploy the backend separately and connect the frontend to it.

## Option 1: Deploy Backend to Railway (Recommended - Free Tier Available)

### Backend Deployment (Railway)

1. **Sign up at Railway**: https://railway.app
2. **Create a new project** and connect your GitHub repository
3. **Set Root Directory**: `src/talking-pnids-py/backend`
4. **Add Environment Variables**:
   - `OPENAI_API_KEY` = your OpenAI API key
   - `OPENAI_MODEL` = `gpt-5.2`
   - `REASONING_EFFORT` = `medium`
   - `PDFS_DIR` = `../data/pdfs`
   - `JSONS_DIR` = `../data/jsons`
   - `MDS_DIR` = `../data/mds`
5. **Set Start Command**: `python main.py` or `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Railway will automatically detect Python and install dependencies from `requirements.txt`
7. **Note**: Railway will give you a URL like `https://your-app.railway.app`

### Frontend Deployment (Vercel)

1. **Update Vercel Environment Variables**:
   - `VITE_API_BASE_URL` = `https://your-app.railway.app/api`
2. **Remove Python build** from `vercel.json` (keep only frontend build)
3. **Redeploy** on Vercel

## Option 2: Deploy Backend to Render (Free Tier Available)

### Backend Deployment (Render)

1. **Sign up at Render**: https://render.com
2. **Create a new Web Service**
3. **Connect your GitHub repository**
4. **Settings**:
   - **Root Directory**: `src/talking-pnids-py/backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. **Add Environment Variables** (same as Railway above)
6. Render will give you a URL like `https://your-app.onrender.com`

### Frontend Deployment (Vercel)

Same as Option 1 - update `VITE_API_BASE_URL` environment variable.

## Option 3: Deploy Backend to Fly.io (Free Tier Available)

### Backend Deployment (Fly.io)

1. **Install Fly CLI**: `curl -L https://fly.io/install.sh | sh`
2. **Login**: `fly auth login`
3. **Create app**: `cd src/talking-pnids-py/backend && fly launch`
4. **Add environment variables**: `fly secrets set OPENAI_API_KEY=your-key`
5. **Deploy**: `fly deploy`

## Updating Frontend Configuration

After deploying the backend, update your Vercel project:

1. Go to **Settings** → **Environment Variables**
2. Add: `VITE_API_BASE_URL` = `https://your-backend-url.com/api`
3. Redeploy the frontend

The frontend will automatically use this URL instead of relative paths.

## Local Development

For local development, the frontend will still use `/api` (relative paths) which proxy to `http://localhost:8000` via Vite config.

## Benefits of Separate Deployment

- ✅ Backend can run 24/7 (or with proper scaling)
- ✅ No Vercel Python runtime limitations
- ✅ Better for file serving (PDFs, etc.)
- ✅ Can use proper ASGI server (Uvicorn)
- ✅ More reliable and scalable
