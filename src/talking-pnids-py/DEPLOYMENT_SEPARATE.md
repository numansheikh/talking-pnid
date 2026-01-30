# Deployment Guide - Separate Backend & Frontend

Since Vercel's Python runtime doesn't fully support FastAPI/ASGI applications, we'll deploy the backend separately and connect the frontend to it.

## Platform Comparison

### Render vs Koyeb (Both Require Credit Card)

| Feature | Render | Koyeb |
|---------|--------|-------|
| **Free Tier** | ✅ Yes (spins down after 15min) | ✅ Yes (pay-as-you-go) |
| **Credit Card Required** | ❌ Yes | ❌ Yes |
| **FastAPI Support** | ✅ Excellent | ✅ Excellent |
| **Auto-deploy from GitHub** | ✅ Yes | ✅ Yes |
| **Cold Start** | ~30-60s (after spin-down) | ~250ms (very fast) |
| **Ease of Use** | ⭐⭐⭐⭐ Very Easy | ⭐⭐⭐⭐⭐ Excellent |
| **Best For** | Simple deployments | High performance, fast cold starts |

**Verdict**: If you must choose between these two, **Koyeb is better** for:
- Faster cold starts (250ms vs 30-60s)
- Better performance
- More modern platform

But both require credit cards.

### Best Options WITHOUT Credit Card

1. **Replit** ⭐⭐⭐⭐⭐ (BEST - No credit card, easy setup, free hosting)
2. **PythonAnywhere** ⭐⭐⭐⭐ (Free tier, no credit card, but more manual setup)
3. **Glitch** ⭐⭐⭐ (Free tier, no credit card, but limited)

---

## Option 1: Deploy Backend to Replit (BEST - FREE, No Credit Card) ⭐

### Backend Deployment (Replit) - FREE, NO CREDIT CARD

1. **Sign up at Replit**: https://replit.com (free, no credit card required)
2. **Create a new Repl**:
   - Click "Create Repl"
   - Choose "Import from GitHub"
   - Enter: `numansheikh/talking-pnid`
   - Select "Python" as the language
3. **Configure**:
   - In the Repl, go to "Secrets" (lock icon in sidebar)
   - Add environment variables:
     - `OPENAI_API_KEY` = your OpenAI API key
     - `OPENAI_MODEL` = `gpt-5.2`
     - `REASONING_EFFORT` = `medium`
     - `PDFS_DIR` = `../data/pdfs`
     - `JSONS_DIR` = `../data/jsons`
     - `MDS_DIR` = `../data/mds`
4. **Set up the Repl**:
   - The `.replit` file is already in the backend directory
   - Or manually run: `cd src/talking-pnids-py/backend && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000`
5. **Deploy as Web Service**:
   - Click "Deploy" button (top right)
   - Choose "Deploy as Web Service"
   - Replit will give you a URL like `https://your-repl-name.your-username.repl.co`

### Frontend Deployment (Vercel)

1. **Update Vercel Environment Variables**:
   - `VITE_API_BASE_URL` = `https://your-repl-name.your-username.repl.co/api`
2. **Redeploy** on Vercel (or it will auto-redeploy)

---

## Option 2: Deploy Backend to Koyeb (Requires Credit Card)

### Backend Deployment (Koyeb)

1. **Sign up at Koyeb**: https://www.koyeb.com (requires credit card)
2. **Create a new App**:
   - Click "Deploy" → "Create App"
   - Connect your GitHub repository: `numansheikh/talking-pnid`
3. **Configure**:
   - **Root Directory**: `src/talking-pnids-py/backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Run Command**: `uvicorn main:app --host 0.0.0.0 --port 8000`
   - **Type**: Web Service
4. **Add Environment Variables**:
   - `OPENAI_API_KEY` = your OpenAI API key
   - `OPENAI_MODEL` = `gpt-5.2`
   - `REASONING_EFFORT` = `medium`
   - `PDFS_DIR` = `../data/pdfs`
   - `JSONS_DIR` = `../data/jsons`
   - `MDS_DIR` = `../data/mds`
5. **Deploy** - Koyeb will give you a URL like `https://your-app.koyeb.app`

**Note**: Koyeb offers pay-as-you-go pricing starting at $0.0022/hour. Requires credit card.

### Frontend Deployment (Vercel)

1. **Update Vercel Environment Variables**:
   - `VITE_API_BASE_URL` = `https://your-app.koyeb.app/api`
2. **Redeploy** on Vercel

---

## Option 3: Deploy Backend to Render (Requires Credit Card)

### Backend Deployment (Render)

1. **Sign up at Render**: https://render.com (requires credit card)
2. **Create a new Web Service**
3. **Connect your GitHub repository**
4. **Settings**:
   - **Root Directory**: `src/talking-pnids-py/backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free (spins down after 15 min inactivity)
5. **Add Environment Variables** (same as above)
6. **Deploy** - Render will give you a URL like `https://your-app.onrender.com`

### Frontend Deployment (Vercel)

Same as above - update `VITE_API_BASE_URL` environment variable.

---

## Option 4: Deploy Backend to PythonAnywhere (Free Tier - No Credit Card)

### Backend Deployment (PythonAnywhere)

1. **Sign up at PythonAnywhere**: https://www.pythonanywhere.com (free tier, no credit card)
2. **Upload your code**:
   - Use the Files tab to upload or clone from GitHub
   - Navigate to your backend directory
3. **Set up Web App**:
   - Go to "Web" tab
   - Click "Add a new web app"
   - Choose "Manual configuration" → "Python 3.10" (or latest)
   - Set source code path to your backend directory
4. **Configure WSGI file**:
   - Edit the WSGI file to point to your FastAPI app
   - Use uvicorn or create a WSGI wrapper
5. **Add environment variables** in the Web app settings
6. **Reload** the web app

### Frontend Deployment (Vercel)

Same as above - update `VITE_API_BASE_URL` environment variable.

---

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

## Recommendation

**For no credit card**: Use **Replit** (Option 1) - easiest and truly free.

**If you have a credit card**: Use **Koyeb** (Option 2) - best performance and fastest cold starts.
