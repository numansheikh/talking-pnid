# Koyeb Backend Deployment Guide

This guide will help you deploy the FastAPI backend to Koyeb from scratch.

## Prerequisites

1. A Koyeb account (sign up at https://www.koyeb.com - free tier available)
2. A GitHub account
3. Your code pushed to a GitHub repository

## Step 1: Prepare Your Repository

### 1.1 Ensure Required Files Exist

Make sure these files are in your `backend/` directory:
- ✅ `main.py` - FastAPI application
- ✅ `requirements.txt` - Python dependencies
- ✅ `Procfile` - Koyeb startup command

### 1.2 Push to GitHub

```bash
cd /path/to/your/project
git add .
git commit -m "Prepare for Koyeb deployment"
git push origin main
```

## Step 2: Deploy on Koyeb

### 2.1 Create New App

1. Go to https://app.koyeb.com
2. Click **"Create App"** or **"New App"**
3. Select **"GitHub"** as your source
4. Authorize Koyeb to access your GitHub if needed

### 2.2 Configure Repository

1. Select your repository
2. **Important**: Set the **Root Directory** to:
   ```
   src/talking-pnids-py
   ```
   - This ensures `data/` and `config/` are included (needed for file mappings)
   - The Procfile at this level runs: `cd backend && uvicorn main:app ...`
3. Select the branch (usually `main` or `master`)

### 2.3 Configure Build Settings

- **Build Command**: Leave empty (Koyeb will auto-detect Python)
- **Run Command**: Leave empty (Procfile will be used)
- **Python Version**: Koyeb will auto-detect, but you can specify `3.11` or `3.12`

### 2.4 Set Environment Variables

Click on **"Environment Variables"** and add:

**Required:**
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**Optional (but recommended):**
```
OPENAI_MODEL=o1-preview
REASONING_EFFORT=medium
PDFS_DIR=/app/data/pdfs
JSONS_DIR=/app/data/jsons
MDS_DIR=/app/data/mds
FRONTEND_URL=https://your-frontend.vercel.app
MAX_TOKENS=2000
TEMPERATURE=0.7
```

**Important Notes:**
- Use **absolute paths** for directories in cloud (e.g., `/app/data/pdfs`)
- Set `FRONTEND_URL` to your Vercel frontend URL after deploying the frontend
- For initial testing, you can set `FRONTEND_URL=*` to allow all origins

### 2.5 Deploy

1. Click **"Deploy"**
2. Wait for the build to complete (usually 2-3 minutes)
3. Koyeb will provide you with a URL like: `https://your-app-name.koyeb.app`

## Step 3: Verify Deployment

### 3.1 Test Health Endpoint

```bash
curl https://your-app-name.koyeb.app/health
```

Should return: `{"status":"ok"}`

### 3.2 Test API Endpoint

```bash
curl https://your-app-name.koyeb.app/api/files
```

Should return JSON with file mappings.

### 3.3 Check Logs

In Koyeb dashboard:
1. Go to your app
2. Click on **"Logs"** tab
3. Check for any errors

## Step 4: Handle Data Files

### Option A: Include Data in Repository (Simple)

If your data files are small (< 50MB total):
1. Keep `data/` directory in your repository
2. Koyeb will deploy it with your code
3. Paths will work automatically

### Option B: External Storage (Recommended for Production)

For larger files or better performance:
1. Use cloud storage (S3, Google Cloud Storage, etc.)
2. Update paths to point to external storage
3. Or use Koyeb's volume mounts (if available on your plan)

## Step 5: Update CORS (After Frontend Deployment)

Once you deploy the frontend to Vercel:

1. Go to Koyeb app settings
2. Update environment variable:
   ```
   FRONTEND_URL=https://your-frontend.vercel.app
   ```
3. Restart the app (or it will auto-restart)

## Troubleshooting

### Issue: App fails to start

**Check:**
- Logs in Koyeb dashboard
- Ensure `Procfile` exists and is correct
- Verify `requirements.txt` is in the backend directory
- Check that `main.py` is in the backend directory

### Issue: "Module not found" errors

**Solution:**
- Ensure all dependencies are in `requirements.txt`
- Check that Root Directory is set to `src/talking-pnids-py`
- Verify the Procfile runs `cd backend && uvicorn main:app ...`

### Issue: "OpenAI API key not found"

**Solution:**
- Verify `OPENAI_API_KEY` is set in Koyeb environment variables
- Check that there are no extra spaces in the environment variable value

### Issue: Path errors (files not found)

**Solution:**
- Use absolute paths in environment variables: `/app/data/pdfs`
- Or ensure data files are included in your repository
- Check logs to see what paths are being used

### Issue: Port binding errors

**Solution:**
- Koyeb automatically sets `PORT` environment variable
- The code should use `os.getenv("PORT", 8000)` (already implemented)

## Next Steps

After backend is deployed and working:

1. ✅ Note your backend URL: `https://your-app-name.koyeb.app`
2. ✅ Test all endpoints
3. ✅ Deploy frontend to Vercel (next step)
4. ✅ Update `FRONTEND_URL` in Koyeb
5. ✅ Update frontend to use backend URL

## Useful Commands

```bash
# Test health
curl https://your-app-name.koyeb.app/health

# Test files endpoint
curl https://your-app-name.koyeb.app/api/files

# Test session (requires API key)
curl -X POST https://your-app-name.koyeb.app/api/session

# Debug paths
curl https://your-app-name.koyeb.app/debug/paths
```

## Support

- Koyeb Docs: https://www.koyeb.com/docs
- Koyeb Status: https://status.koyeb.com
- Check logs in Koyeb dashboard for detailed error messages
