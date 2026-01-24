# Deployment Guide - Python Version

## Deploy to Vercel

This guide will help you deploy the Python FastAPI backend + React frontend to Vercel.

### Prerequisites

1. A GitHub account
2. A Vercel account (sign up at https://vercel.com - it's free)
3. Your code pushed to a GitHub repository

### Steps

1. **Push your code to GitHub**
   ```bash
   cd src/talking-pnids-py
   git init
   git add .
   git commit -m "Initial commit - Python version"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Sign up/Login to Vercel**
   - Go to https://vercel.com
   - Sign up with your GitHub account

3. **Import your project**
   - Click "Add New..." → "Project"
   - Import your GitHub repository
   - **Important**: Set the root directory to `src/talking-pnids-py` (or the path where your `vercel.json` is located)

4. **Configure Environment Variables**
   - In the Vercel project settings, go to "Environment Variables"
   - **Required:** `OPENAI_API_KEY` = your OpenAI API key
   - **Optional:** You can also set these:
     - `OPENAI_MODEL` = model name (default: `gpt-5.2`)
     - `REASONING_EFFORT` = reasoning effort level (default: `medium`)
     - `PDFS_DIR` = PDF directory path (default: `./data/pdfs`)
     - `JSONS_DIR` = JSON directory path (default: `./data/jsons`)
     - `MDS_DIR` = Markdown directory path (default: `./data/mds`)
     - `MAX_TOKENS` = max tokens (default: `2000`)
     - `TEMPERATURE` = temperature (default: `0.7`)
     - `FRONTEND_URL` = your Vercel frontend URL (for CORS)
   - Make sure to add `OPENAI_API_KEY` for all environments (Production, Preview, Development)

5. **Configure Build Settings**
   - **Root Directory**: `src/talking-pnids-py` (or leave empty if deploying from the repo root)
   - **Framework Preset**: Other
   - **Build Command**: (leave empty, Vercel will auto-detect)
   - **Output Directory**: `frontend/dist` (for the frontend build)

6. **Deploy**
   - Click "Deploy"
   - Wait for the build to complete (usually 2-3 minutes)
   - Your app will be live at `https://your-project-name.vercel.app`

### Project Structure for Vercel

```
talking-pnids-py/
├── api/
│   └── index.py          # Vercel serverless function entry point
├── backend/              # FastAPI backend code
│   ├── api/
│   ├── utils/
│   └── main.py
├── frontend/            # React frontend
│   ├── src/
│   └── package.json
├── config/              # Configuration files
├── data/                # Data files (PDFs, JSONs, markdown)
├── vercel.json          # Vercel configuration
├── requirements.txt     # Python dependencies for Vercel
└── .vercelignore        # Files to ignore in deployment
```

### Important Notes

1. **API Routes**: All `/api/*` requests are routed to the Python serverless function
2. **Frontend**: The React app is built and served as static files
3. **CORS**: The backend is configured to allow requests from Vercel domains
4. **Environment Variables**: The app uses environment variables in production, but will fall back to `config/config.json` if available
5. **File Size Limits**: Vercel has limits on file sizes. Make sure your PDFs and data files are within limits (typically 50MB per file)

### Troubleshooting

- **Build fails**: Check that all dependencies are in `requirements.txt`
- **API not working**: Verify environment variables are set correctly
- **CORS errors**: Make sure `FRONTEND_URL` environment variable matches your Vercel domain
- **Module not found**: Ensure `PYTHONPATH` is set correctly (handled by vercel.json)

### Local Development

For local development, use the start scripts:
```bash
npm start
# or
./start.sh
```

This will start both the backend (port 8000) and frontend (port 3000) locally.
