# Fix: Data Files Not Found on Koyeb

## Problem

Your backend is deployed but returning empty arrays:
```json
{"mappings":[],"availablePdfs":[],"availableJsons":[],"availableMds":[]}
```

## Root Cause

Koyeb is running from the `backend/` directory, but the `data/` directory is one level up and not being found.

## Solution Options

### Option 1: Change Koyeb Root Directory (Recommended)

**Change the Root Directory in Koyeb from:**
```
src/talking-pnids-py/backend
```

**To:**
```
src/talking-pnids-py
```

**Then update the Procfile to:**
```
web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Pros:**
- Data files will be included in deployment
- Simpler path resolution
- Works with current code

**Cons:**
- Need to update Procfile

### Option 2: Set Environment Variables (Quick Fix)

In Koyeb, set these environment variables to use relative paths:

```
PDFS_DIR=../data/pdfs
JSONS_DIR=../data/jsons
MDS_DIR=../data/mds
```

**Pros:**
- No code changes needed
- Quick fix

**Cons:**
- Requires data directory to be one level up
- May not work if Koyeb only deploys backend/

### Option 3: Set PROJECT_ROOT Environment Variable

In Koyeb, set:
```
PROJECT_ROOT=/workspace/..
```

This tells the app to go up one level from the workspace to find data/.

**Pros:**
- Works with current path resolution logic
- No code changes

**Cons:**
- Depends on Koyeb's directory structure

## Recommended Action

**Use Option 1** - Change the root directory to `src/talking-pnids-py` and update the Procfile.

### Steps:

1. In Koyeb dashboard, go to your app settings
2. Change **Root Directory** from `src/talking-pnids-py/backend` to `src/talking-pnids-py`
3. Update the Procfile to:
   ```
   web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
4. Redeploy

This ensures the `data/` and `config/` directories are included in the deployment.
