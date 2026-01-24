# Installing LangChain Dependencies

The backend has been converted to use LangChain. You need to install the new dependencies.

## Quick Install

```bash
cd talking-pnids-py/backend
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

This will install:
- langchain
- langchain-openai
- langchain-core
- langchain-community

## Verify Installation

After installing, try starting the backend:

```bash
python main.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

If you see import errors, make sure all packages installed correctly.

## Troubleshooting

If you get import errors:
1. Make sure you're in the virtual environment
2. Try: `pip install --upgrade langchain langchain-openai langchain-core`
3. Check Python version (should be 3.8+)
