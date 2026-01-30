# Talking P&IDs

AI-powered Q&A application for Piping & Instrumentation Diagrams.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Copy `.env.example` to `.env.local` and add your OpenAI API key:
```
OPENAI_API_KEY=your_key_here
```

3. Add P&ID files:
   - PDFs: `data/pdfs/`
   - JSON schemas: `data/jsons/`

4. Run development server:
```bash
npm run dev
```

## Folder Structure

- `data/pdfs/` - P&ID PDF files
- `data/jsons/` - JSON schema files
- `config/config.json` - Application configuration
# talking-pnid
