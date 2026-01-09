import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

async function loadConfig() {
  const configPath = path.join(process.cwd(), 'config', 'config.json')
  const configData = await fs.readFile(configPath, 'utf-8')
  return JSON.parse(configData)
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ filename: string }> | { filename: string } }
) {
  try {
    const resolvedParams = await Promise.resolve(params)
    const filename = decodeURIComponent(resolvedParams.filename)
    
    // Security: Only allow PDF files
    if (!filename.endsWith('.pdf')) {
      return NextResponse.json(
        { error: 'Invalid file type' },
        { status: 400 }
      )
    }

    const config = await loadConfig()
    const pdfsPath = path.join(process.cwd(), config.directories.pdfs.replace('./', ''))
    const filePath = path.join(pdfsPath, filename)

    // Check if file exists
    try {
      await fs.access(filePath)
    } catch {
      return NextResponse.json(
        { error: 'File not found' },
        { status: 404 }
      )
    }

    const fileBuffer = await fs.readFile(filePath)
    
    return new NextResponse(fileBuffer, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `inline; filename="${filename}"`,
        'Cache-Control': 'public, max-age=3600',
      },
    })
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || 'Failed to load PDF' },
      { status: 500 }
    )
  }
}
