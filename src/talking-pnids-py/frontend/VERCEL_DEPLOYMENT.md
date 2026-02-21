# Vercel Frontend Deployment Guide

This guide will help you deploy the React frontend to Vercel and connect it to your Koyeb backend.

**Live app:** https://talking-pnid.vercel.app/app  
**Backend:** https://decent-lilli-cogit-0d306da3.koyeb.app

## Prerequisites

1. A Vercel account (sign up at https://vercel.com - free tier available)
2. A GitHub account
3. Your backend deployed on Koyeb (should be done already)

## Step 1: Prepare Your Repository

### 1.1 Ensure Required Files Exist

Make sure these files are in your `frontend/` directory:
- ✅ `package.json` - Dependencies and build scripts
- ✅ `vite.config.ts` - Vite configuration
- ✅ `vercel.json` - Vercel configuration (already created)
- ✅ `src/` - Source code

### 1.2 Push to GitHub

```bash
cd /path/to/your/project
git add .
git commit -m "Add Vercel deployment configuration"
git push origin main
```

## Step 2: Deploy on Vercel

### 2.1 Create New Project

1. Go to https://vercel.com
2. Click **"Add New..."** → **"Project"**
3. Select **"Import Git Repository"**
4. Authorize Vercel to access your GitHub if needed

### 2.2 Configure Repository

1. Select your repository
2. **Important**: Set the **Root Directory** to `src/talking-pnids-py/frontend`
   - This tells Vercel where your frontend code is located
3. Vercel should auto-detect:
   - **Framework Preset**: Vite (or Other)
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

### 2.3 Set Environment Variables

Click on **"Environment Variables"** and add:

**Required:**
```
VITE_API_BASE_URL=https://decent-lilli-cogit-0d306da3.koyeb.app
```

**Important Notes:**
- Use the backend URL without trailing slash and without `/api`
- The frontend automatically appends `/api` when making requests

### 2.4 Deploy

1. Click **"Deploy"**
2. Wait for the build to complete (usually 1-2 minutes)
3. Vercel will provide you with a URL (live app: https://talking-pnid.vercel.app/app)

## Step 3: Update Backend CORS

### 3.1 Update Koyeb Environment Variables

Go back to your Koyeb dashboard and update the environment variable:

```
FRONTEND_URL=https://talking-pnid.vercel.app
```

### 3.2 Restart Backend (if needed)

Koyeb should auto-restart, or you can manually trigger a restart.

## Step 4: Verify Deployment

### 4.1 Test Frontend

1. Open https://talking-pnid.vercel.app/app
2. Check browser console (F12) for any errors
3. Verify that files are loading from the backend

### 4.2 Test API Connection

In browser console, you should see the API base URL pointing to your backend (with `/api` appended).

### 4.3 Test Functionality

1. Files should load from backend
2. You should be able to start a session (if API key is set)
3. You should be able to ask questions

## Troubleshooting

### Issue: "Failed to load files" or CORS errors

**Solution:**
- Verify `FRONTEND_URL` is set correctly in Koyeb
- Check that the URL matches your Vercel domain exactly (including `https://`)
- Restart the Koyeb backend after updating `FRONTEND_URL`

### Issue: API calls going to wrong URL

**Solution:**
- Check `VITE_API_BASE_URL` in Vercel environment variables
- Should be `https://decent-lilli-cogit-0d306da3.koyeb.app` (no trailing slash, no `/api`)
- The code automatically adds `/api` to the base URL

### Issue: Build fails on Vercel

**Solution:**
- Check that Root Directory is set to `src/talking-pnids-py/frontend`
- Verify `package.json` has a `build` script
- Check build logs in Vercel dashboard

### Issue: 404 errors on page refresh

**Solution:**
- The `vercel.json` rewrite rule should handle this
- If not, check that `vercel.json` is in the frontend directory

## Environment Variables Summary

### Vercel (Frontend)
```
VITE_API_BASE_URL=https://decent-lilli-cogit-0d306da3.koyeb.app
```

### Koyeb (Backend)
```
OPENAI_API_KEY=sk-your-key-here
FRONTEND_URL=https://talking-pnid.vercel.app
```

## Next Steps

After deployment:
1. ✅ Test all functionality
2. ✅ Share the Vercel URL with your team
3. ✅ Monitor both Vercel and Koyeb dashboards for any issues
4. ✅ Set up custom domain (optional)

## Useful Commands

```bash
# Test backend
curl https://decent-lilli-cogit-0d306da3.koyeb.app/api/files

# Test frontend
curl https://talking-pnid.vercel.app/app

# Check environment variables in Vercel
# Go to Project Settings → Environment Variables
```

## Support

- Vercel Docs: https://vercel.com/docs
- Vercel Status: https://www.vercel-status.com
- Check build logs in Vercel dashboard for detailed error messages
