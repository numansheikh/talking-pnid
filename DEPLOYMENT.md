# Deployment Guide

## Deploy to Vercel (Recommended - Free)

Vercel is the best option for Next.js apps as it's made by the creators of Next.js.

### Prerequisites
1. A GitHub account
2. A Vercel account (sign up at https://vercel.com - it's free)

### Steps

1. **Push your code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Sign up/Login to Vercel**
   - Go to https://vercel.com
   - Sign up with your GitHub account

3. **Import your project**
   - Click "Add New..." → "Project"
   - Import your GitHub repository
   - Vercel will auto-detect Next.js settings

4. **Configure Environment Variables**
   - In the Vercel project settings, go to "Environment Variables"
   - **Required:** `OPENAI_API_KEY` = your OpenAI API key
   - **Optional:** You can also set these (defaults will be used if not set):
     - `OPENAI_MODEL` = model name (default: `gpt-4`)
     - `PDFS_DIR` = PDF directory path (default: `./data/pdfs`)
     - `JSONS_DIR` = JSON directory path (default: `./data/jsons`)
     - `MAX_TOKENS` = max tokens (default: `2000`)
     - `TEMPERATURE` = temperature (default: `0.7`)
   - Make sure to add `OPENAI_API_KEY` for all environments (Production, Preview, Development)

5. **Deploy**
   - Click "Deploy"
   - Wait for the build to complete (usually 1-2 minutes)
   - Your app will be live at `https://your-project-name.vercel.app`

6. **Share with your team**
   - Share the Vercel URL with your team
   - They can access it from any browser
   - No installation needed!

### Local Development Setup

For local development, create a `config/config.json` file (copy from `config/config.json.example`):
```bash
cp config/config.json.example config/config.json
```

Then add your OpenAI API key to `config/config.json`.

**Note:** `config/config.json` is in `.gitignore` so it won't be committed to GitHub.

## Alternative Free Options

### Netlify
- Similar to Vercel
- Go to https://netlify.com
- Connect GitHub repo
- Add `OPENAI_API_KEY` environment variable
- Deploy

### Railway
- Go to https://railway.app
- Connect GitHub repo
- Add environment variables
- Deploy

## Important Notes

- **API Keys**: Never commit API keys to GitHub. Always use environment variables.
- **Config File**: The `config/config.json` file is optional in production. The app will use environment variables if the config file doesn't exist (which is the case on Vercel).
- **File Size**: Vercel has limits on file sizes. Your PDFs and JSON files should be fine.
- **Free Tier Limits**: 
  - Vercel: 100GB bandwidth/month, unlimited projects
  - Netlify: 100GB bandwidth/month, 300 build minutes/month
- **Custom Domain**: You can add a custom domain later if needed.
