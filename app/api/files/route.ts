import { NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

async function loadFileMappings() {
  const mappingsPath = path.join(process.cwd(), 'config', 'file-mappings.json')
  try {
    const content = await fs.readFile(mappingsPath, 'utf-8')
    return JSON.parse(content)
  } catch (error) {
    return { mappings: [] }
  }
}

async function verifyFiles() {
  // Load config with fallback to env vars
  const configPath = path.join(process.cwd(), 'config', 'config.json')
  let config: any = {
    directories: {
      pdfs: process.env.PDFS_DIR || './data/pdfs',
      jsons: process.env.JSONS_DIR || './data/jsons',
    },
  }

  try {
    const configData = await fs.readFile(configPath, 'utf-8')
    const fileConfig = JSON.parse(configData)
    config = {
      directories: {
        pdfs: process.env.PDFS_DIR || fileConfig.directories?.pdfs || config.directories.pdfs,
        jsons: process.env.JSONS_DIR || fileConfig.directories?.jsons || config.directories.jsons,
      },
    }
  } catch (error: any) {
    // File doesn't exist or can't be read - use defaults from env vars
    if (error.code !== 'ENOENT') {
      console.warn('Error reading config file:', error.message)
    }
  }
  
  // Handle both './data/jsons' and 'data/jsons' formats
  let pdfsPath = config.directories.pdfs
  if (pdfsPath.startsWith('./')) {
    pdfsPath = pdfsPath.substring(2)
  }
  let jsonsPath = config.directories.jsons
  if (jsonsPath.startsWith('./')) {
    jsonsPath = jsonsPath.substring(2)
  }
  
  const fullPdfsPath = path.join(process.cwd(), pdfsPath)
  const fullJsonsPath = path.join(process.cwd(), jsonsPath)
  
  console.log('Checking PDFs in:', fullPdfsPath)
  console.log('Checking JSONs in:', fullJsonsPath)
  
  try {
    const pdfFiles = await fs.readdir(fullPdfsPath)
    const jsonFiles = await fs.readdir(fullJsonsPath)
    
    console.log('PDF files found:', pdfFiles)
    console.log('JSON files found:', jsonFiles)
    
    return {
      pdfs: pdfFiles.filter(f => f.endsWith('.pdf')),
      jsons: jsonFiles.filter(f => f.endsWith('.json'))
    }
  } catch (error: any) {
    console.error('Error verifying files:', error)
    console.error('PDFs path:', fullPdfsPath)
    console.error('JSONs path:', fullJsonsPath)
    return { pdfs: [], jsons: [] }
  }
}

export async function GET() {
  try {
    const mappings = await loadFileMappings()
    const files = await verifyFiles()
    
    // Enrich mappings with file existence info
    const enrichedMappings = mappings.mappings.map((mapping: any) => ({
      ...mapping,
      pdfExists: files.pdfs.includes(mapping.pdf),
      jsonExists: files.jsons.includes(mapping.json)
    }))
    
    return NextResponse.json({
      mappings: enrichedMappings,
      availablePdfs: files.pdfs,
      availableJsons: files.jsons
    })
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || 'Failed to load file mappings' },
      { status: 500 }
    )
  }
}
