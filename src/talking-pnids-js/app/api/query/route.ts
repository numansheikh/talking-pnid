import { NextRequest, NextResponse } from 'next/server'
import OpenAI from 'openai'
import fs from 'fs/promises'
import path from 'path'
import { getAllMarkdowns, getMarkdownSummaries, getMarkdownByFilename } from '../utils/markdownCache'

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
    const { query, selectedMapping, sessionStarted } = await req.json()
    const config = await loadConfig()
    
    // Get API key from config or environment
    const apiKey = config.openai?.apiKey || process.env.OPENAI_API_KEY
    if (!apiKey) {
      throw new Error('OpenAI API key not found. Please set OPENAI_API_KEY environment variable or add it to config.json')
    }
    
    const openai = getOpenAIClient(apiKey)
    const prompts = await loadPrompts()
    
    // Get system prompt from prompts file
    const systemPrompt = prompts?.systemPrompt?.content || 
      prompts?.defaultSystemPrompt?.content || 
      'You are an expert assistant for Piping & Instrumentation Diagrams (P&IDs). Answer questions based on the provided markdown documentation and your knowledge of P&IDs.'
    
    let context = ''
    
    // If a specific mapping is selected, send that full markdown (single file should be fine, cached)
    if (selectedMapping && selectedMapping.md) {
      const markdown = await getMarkdownByFilename(selectedMapping.md)
      if (markdown) {
        context = `P&ID Markdown Documentation for ${selectedMapping.id} (${selectedMapping.pdf}):\n\n${markdown}\n\n`
      } else {
        context = `No markdown found for ${selectedMapping.md}.\n\n`
      }
    } else if (sessionStarted) {
      // Session started but no specific mapping: send summaries to avoid token limits (cached)
      const summaries = await getMarkdownSummaries()
      if (summaries.length > 0) {
        context = `P&ID Documentation Summaries (${summaries.length} systems available):\n\n${summaries.map((summary, idx) => `File ${idx + 1}: ${summary.filename}\nPreview: ${summary.preview}...\nSize: ${summary.size} characters\n`).join('\n')}\n\nNote: Summaries are provided to reduce token usage. If you need details about a specific equipment, instrument, or process from a particular file, indicate which one and the full markdown documentation can be retrieved.\n\n`
      } else {
        context = 'No P&ID markdown documentation available yet.\n\n'
      }
    } else {
      // Fallback: send summaries (cached)
      const summaries = await getMarkdownSummaries()
      if (summaries.length > 0) {
        context = `P&ID Documentation Summaries:\n\n${summaries.map((summary, idx) => `File ${idx + 1}: ${summary.filename}\nPreview: ${summary.preview}...\n`).join('\n')}\n\nNote: Summaries are provided. Select a specific file to get full markdown documentation.\n\n`
      } else {
        context = 'No P&ID markdown documentation available yet.\n\n'
      }
    }
    
    const completion = await openai.chat.completions.create({
      model: config.openai.model || 'gpt-4',
      messages: [
        {
          role: 'system',
          content: systemPrompt,
        },
        {
          role: 'user',
          content: `${context}Question: ${query}`,
        },
      ],
      max_tokens: config.settings?.maxTokens || 2000,
      temperature: config.settings?.temperature || 0.7,
    })

    const answer = completion.choices[0]?.message?.content
    
    if (!answer) {
      console.error('OpenAI returned empty response:', {
        choices: completion.choices,
        model: config.openai.model,
      })
      return NextResponse.json(
        { error: 'OpenAI API returned an empty response. Please try again.' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      answer,
    })
  } catch (error: any) {
    console.error('Query API error:', {
      message: error.message,
      name: error.name,
      status: error.status,
      response: error.response?.data,
    })
    return NextResponse.json(
      { 
        error: error.message || 'Failed to process query',
        details: process.env.NODE_ENV === 'development' ? error.stack : undefined
      },
      { status: 500 }
    )
  }
}
