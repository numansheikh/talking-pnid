# Fix OpenAI Compatibility Issue

The error `TypeError: Client.__init__() got an unexpected keyword argument 'proxies'` is due to an outdated OpenAI library version.

## Quick Fix

Run this in the backend directory:

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install --upgrade openai
```

Or reinstall all dependencies:

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

The requirements.txt has been updated to use `openai>=1.40.0` which is compatible with the current httpx/httpcore versions.
