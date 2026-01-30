import { NextRequest, NextResponse } from 'next/server'
import OpenAI from 'openai'
import fs from 'fs/promises'
import path from 'path'
import { getAllMarkdowns, getMarkdownSummaries } from '../utils/markdownCache'

async function loadConfig() {
  const configPath = path.join(process.cwd(), 'config', 'config.json')
  let config: any = {
    openai: {
      apiKey: process.env.OPENAI_API_KEY || '',
      model: process.env.OPENAI_MODEL || 'gpt-4',
    },
    directories: {
      pdfs: process.env.PDFS_DIR || './data/pdfs',
      jsons: process.env.JSONS_DIR || './data/jsons',
    },
    settings: {
      maxTokens: parseInt(process.env.MAX_TOKENS || '2000', 10),
      temperature: parseFloat(process.env.TEMPERATURE || '0.7'),
    },
  }

  try {
    const configData = await fs.readFile(configPath, 'utf-8')
    const fileConfig = JSON.parse(configData)
    // Merge file config with defaults (file config takes precedence, but env vars override)
    config = {
      openai: {
        apiKey: process.env.OPENAI_API_KEY || fileConfig.openai?.apiKey || config.openai.apiKey,
        model: process.env.OPENAI_MODEL || fileConfig.openai?.model || config.openai.model,
      },
      directories: {
        pdfs: process.env.PDFS_DIR || fileConfig.directories?.pdfs || config.directories.pdfs,
        jsons: process.env.JSONS_DIR || fileConfig.directories?.jsons || config.directories.jsons,
      },
      settings: {
        maxTokens: parseInt(process.env.MAX_TOKENS || fileConfig.settings?.maxTokens?.toString() || '2000', 10),
        temperature: parseFloat(process.env.TEMPERATURE || fileConfig.settings?.temperature?.toString() || '0.7'),
      },
    }
  } catch (error: any) {
    // File doesn't exist or can't be read - use defaults from env vars
    if (error.code !== 'ENOENT') {
      console.warn('Error reading config file:', error.message)
    }
  }

  return config
}

function getOpenAIClient(apiKey?: string) {
  // Prefer environment variable, then config, then throw error
  const key = apiKey || process.env.OPENAI_API_KEY
  
  if (!key) {
    throw new Error('OpenAI API key not found. Please set OPENAI_API_KEY environment variable or add it to config.json')
  }
  
  return new OpenAI({
    apiKey: key,
  })
}

async function loadPrompts() {
  const promptsPath = path.join(process.cwd(), 'config', 'prompts.json')
  try {
    const content = await fs.readFile(promptsPath, 'utf-8')
    return JSON.parse(content)
  } catch (error) {
    return null
  }
}

export async function POST(req: NextRequest) {
  try {
    console.log('Session initialization started...')
    const config = await loadConfig()
    console.log('Config loaded, model:', config.openai.model)
    
    // Get API key from config or environment
    const apiKey = config.openai?.apiKey || process.env.OPENAI_API_KEY
    if (!apiKey) {
      throw new Error('OpenAI API key not found. Please set OPENAI_API_KEY environment variable or add it to config.json')
    }
    
    const openai = getOpenAIClient(apiKey)
    
    const prompts = await loadPrompts()
    console.log('Prompts loaded:', prompts ? 'yes' : 'no')
    
    // Load markdown summaries (cached)
    const markdownSummaries = await getMarkdownSummaries()
    console.log('Markdown summaries loaded (cached):', markdownSummaries.length)
    
    if (markdownSummaries.length === 0) {
      console.error('No markdown files found')
      return NextResponse.json(
        { error: 'No markdown files found. Please add markdown files to the data/mds folder.' },
        { status: 404 }
      )
    }

    // Get system prompt
    const systemPrompt = prompts?.systemPrompt?.content || prompts?.defaultSystemPrompt?.content || 
      'You are an expert assistant for Piping & Instrumentation Diagrams (P&IDs).'
    
    // Get session init prompt and replace placeholder
    const sessionInitPrompt = (prompts?.sessionInitPrompt?.content || 
      'I\'m starting a new session to discuss plant operations. Please acknowledge that you\'ve received the plant data.')
      .replace('{count}', markdownSummaries.length.toString())
    
    // Prepare context with markdown summaries
    const markdownsContext = `P&ID Documentation Summaries (${markdownSummaries.length} systems available):\n\n${markdownSummaries.map((summary, idx) => `File ${idx + 1}: ${summary.filename}\nPreview: ${summary.preview}...\nSize: ${summary.size} characters\n`).join('\n')}\n\nNote: Full markdown documentation will be provided when answering specific questions about the plant.`
    
    console.log('Initializing OpenAI session with markdown summaries...')
    // Initialize session with OpenAI
    const completion = await openai.chat.completions.create({
      model: config.openai.model || 'gpt-4',
      messages: [
        {
          role: 'system',
          content: systemPrompt,
        },
        {
          role: 'user',
          content: `${markdownsContext}${sessionInitPrompt}`,
        },
      ],
      max_tokens: config.settings?.maxTokens || 2000,
      temperature: config.settings?.temperature || 0.7,
    })

    const assistantResponse = completion.choices[0]?.message?.content || 'Session initialized. Ready to assist.'
    console.log('Session initialized successfully')

    return NextResponse.json({
      success: true,
      message: assistantResponse,
      markdownsLoaded: markdownSummaries.length,
      sessionId: Date.now().toString(), // Simple session ID, can be enhanced later
    })
  } catch (error: any) {
    console.error('Session initialization error:', error)
    return NextResponse.json(
      { 
        error: error.message || 'Failed to initialize session',
        details: process.env.NODE_ENV === 'development' ? error.stack : undefined
      },
      { status: 500 }
    )
  }
}
