import { NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

async function loadPrompts() {
  const promptsPath = path.join(process.cwd(), 'config', 'prompts.json')
  try {
    const content = await fs.readFile(promptsPath, 'utf-8')
    return JSON.parse(content)
  } catch (error) {
    return null
  }
}

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url)
    const promptId = searchParams.get('id')

    const prompts = await loadPrompts()
    if (!prompts) {
      return NextResponse.json(
        { error: 'Prompts file not found' },
        { status: 404 }
      )
    }

    if (promptId) {
      // Return specific prompt by ID
      const promptKey = Object.keys(prompts).find(
        (key) => prompts[key]?.id === promptId
      )
      if (promptKey && prompts[promptKey]) {
        return NextResponse.json({ prompt: prompts[promptKey] })
      }
      return NextResponse.json(
        { error: 'Prompt not found' },
        { status: 404 }
      )
    }

    // Return all prompts
    return NextResponse.json({ prompts })
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || 'Failed to load prompts' },
      { status: 500 }
    )
  }
}
