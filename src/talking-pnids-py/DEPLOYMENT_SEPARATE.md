# Deployment Guide - Separate Backend & Frontend

Since Vercel's Python runtime doesn't fully support FastAPI/ASGI applications, we'll deploy the backend separately and connect the frontend to it.

## Option 1: Deploy Backend to Render (Recommended - Free Tier Available)

### Backend Deployment (Render) - FREE TIER

1. **Sign up at Render**: https://render.com (free tier available)
2. **Create a new Web Service**
3. **Connect your GitHub repository**
4. **Settings**:
   - **Name**: `talking-pnids-backend` (or any name)
   - **Root Directory**: `src/talking-pnids-py/backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free (spins down after 15 min inactivity, wakes on request)
5. **Add Environment Variables**:
   - `OPENAI_API_KEY` = your OpenAI API key
   - `OPENAI_MODEL` = `gpt-5.2`
   - `REASONING_EFFORT` = `medium`
   - `PDFS_DIR` = `../data/pdfs`
   - `JSONS_DIR` = `../data/jsons`
   - `MDS_DIR` = `../data/mds`
6. **Deploy** - Render will give you a URL like `https://your-app.onrender.com`

### Frontend Deployment (Vercel)

1. **Update Vercel Environment Variables**:
   - `VITE_API_BASE_URL` = `https://your-app.onrender.com/api`
2. **Redeploy** on Vercel (or it will auto-redeploy)

## Option 2: Deploy Backend to Fly.io (Free Tier Available)

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
