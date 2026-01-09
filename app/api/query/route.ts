import { NextRequest, NextResponse } from 'next/server'
import OpenAI from 'openai'
import fs from 'fs/promises'
import path from 'path'
import { getAllSchemas, getSchemaSummaries, getSchemaByFilename } from '../utils/schemaCache'

async function loadConfig() {
  const configPath = path.join(process.cwd(), 'config', 'config.json')
  let config: any = {
    openai: {
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
      'You are an expert assistant for Piping & Instrumentation Diagrams (P&IDs). Answer questions based on the provided JSON schema data and your knowledge of P&IDs.'
    
    let context = ''
    
    // If a specific mapping is selected, send that full schema (single schema should be fine, cached)
    if (selectedMapping && selectedMapping.json) {
      const schema = await getSchemaByFilename(selectedMapping.json)
      if (schema) {
        context = `P&ID JSON Schema for ${selectedMapping.id} (${selectedMapping.pdf}):\n${JSON.stringify(schema, null, 2)}\n\n`
      } else {
        context = `No schema found for ${selectedMapping.json}.\n\n`
      }
    } else if (sessionStarted) {
      // Session started but no specific mapping: send summaries to avoid token limits (cached)
      const summaries = await getSchemaSummaries()
      if (summaries.length > 0) {
        context = `P&ID Schema Summaries (${summaries.length} systems available):\n${JSON.stringify(summaries, null, 2)}\n\nNote: Schema summaries are provided to reduce token usage. If you need details about a specific equipment, instrument, or process from a particular schema, indicate which one (by doc_id or tag) and the full schema details can be retrieved.\n\n`
      } else {
        context = 'No P&ID schemas available yet.\n\n'
      }
    } else {
      // Fallback: send summaries (cached)
      const summaries = await getSchemaSummaries()
      if (summaries.length > 0) {
        context = `P&ID Schema Summaries:\n${JSON.stringify(summaries, null, 2)}\n\nNote: Summaries are provided. Select a specific file to get full schema details.\n\n`
      } else {
        context = 'No P&ID schemas available yet.\n\n'
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

    return NextResponse.json({
      answer: completion.choices[0]?.message?.content || 'No answer generated',
    })
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || 'Failed to process query' },
      { status: 500 }
    )
  }
}
